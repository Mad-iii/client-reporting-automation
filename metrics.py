import json
import pandas as pd
from utils import safe_div, pct_change, fmt_value, fmt_delta, delta_tone

KPI_DEFS = [
    dict(key="spend", label="Ad spend", fmt="money", good="neutral"),
    dict(key="revenue", label="Revenue", fmt="money", good="up"),
    dict(key="roas", label="ROAS", fmt="x", good="up"),
    dict(key="conversions", label="Conversions", fmt="int", good="up"),
    dict(key="cpa", label="Cost / conversion", fmt="money2", good="down"),
    dict(key="ctr", label="CTR", fmt="pct", good="up"),
    dict(key="sessions", label="Website sessions", fmt="int", good="up"),
    dict(key="bounce_rate", label="Bounce rate", fmt="pct", good="down"),
]
AD_COLS = ["spend", "impressions", "clicks", "conversions", "revenue"]


def _window(df, start, end):
    return df[(df["date"] >= start) & (df["date"] <= end)]


def _derive(spend, impressions, clicks, conversions, revenue):
    return dict(
        spend=float(spend), impressions=float(impressions), clicks=float(clicks),
        conversions=float(conversions), revenue=float(revenue),
        roas=safe_div(revenue, spend), cpa=safe_div(spend, conversions),
        ctr=safe_div(clicks, impressions), cpc=safe_div(spend, clicks),
        cvr=safe_div(conversions, clicks),
    )


def _totals(ads, ga4):
    t = _derive(*[ads[c].sum() for c in AD_COLS])
    sessions, bounces = float(ga4["sessions"].sum()), float(ga4["bounces"].sum())
    t["sessions"] = sessions
    t["bounce_rate"] = safe_div(bounces, sessions)
    return t


def _campaigns(ads, cur_w, prev_w, total_spend):
    def grp(w):
        return _window(ads, *w).groupby(["platform", "campaign"])[AD_COLS].sum()
    cur, prev = grp(cur_w), grp(prev_w)
    rows = []
    for (platform, name), r in cur.iterrows():
        m = _derive(*[r[c] for c in AD_COLS])
        p = None
        if (platform, name) in prev.index:
            pr = prev.loc[(platform, name)]
            p = _derive(*[pr[c] for c in AD_COLS])
        rows.append(dict(
            platform=platform, campaign=name, **m, prev=p,
            spend_share=safe_div(m["spend"], total_spend) or 0.0,
            cpa_change=pct_change(m["cpa"], p["cpa"]) if p else None,
            roas_change=pct_change(m["roas"], p["roas"]) if p else None,
        ))
    rows.sort(key=lambda x: -x["spend"])
    return rows


def _channels(ga4, cur_w, prev_w):
    cur = _window(ga4, *cur_w).groupby("channel")["sessions"].sum()
    prev = _window(ga4, *prev_w).groupby("channel")["sessions"].sum()
    out = []
    for ch, v in cur.sort_values(ascending=False).items():
        p = float(prev.get(ch, 0))
        out.append(dict(channel=ch, sessions=float(v), prev=p, change=pct_change(float(v), p)))
    return out


def _devices(ga4, cur_w, prev_w):
    def rates(w):
        g = _window(ga4, *w).groupby("device")[["sessions", "bounces"]].sum()
        return {d: (float(r.sessions), safe_div(r.bounces, r.sessions)) for d, r in g.iterrows()}
    cur, prev = rates(cur_w), rates(prev_w)
    out = []
    for d, (s, b) in cur.items():
        pb = prev.get(d, (0, None))[1]
        pts = (b - pb) if (b is not None and pb is not None) else None
        out.append(dict(device=d, sessions=s, bounce_rate=b, prev_bounce_rate=pb, bounce_change_pts=pts))
    return out


def _trend(ads, ga4, end, n_weeks):
    t = dict(labels=[], spend=[], revenue=[], roas=[], sessions=[])
    for i in range(n_weeks):
        e = end - pd.Timedelta(days=7 * (n_weeks - 1 - i))
        s = e - pd.Timedelta(days=6)
        a, g = _window(ads, s, e), _window(ga4, s, e)
        sp, rv = float(a["spend"].sum()), float(a["revenue"].sum())
        t["labels"].append(s.strftime("%b %d"))
        t["spend"].append(round(sp, 2))
        t["revenue"].append(round(rv, 2))
        t["roas"].append(round(rv / sp, 2) if sp else None)
        t["sessions"].append(int(g["sessions"].sum()))
    return t


def _cause(c, p):
    ctr = pct_change(c["ctr"], p["ctr"]) or 0
    cvr = pct_change(c["cvr"], p["cvr"]) or 0
    cpc = pct_change(c["cpc"], p["cpc"]) or 0
    if ctr < -0.15:
        return (f"click-through rate fell {abs(ctr) * 100:.0f}%, which usually means tired ad creative or audience",
                "Refresh the ad creative and test new hooks")
    if cvr < -0.15:
        return (f"fewer clicks turned into customers (conversion rate down {abs(cvr) * 100:.0f}%), "
                "which points to the landing page, offer or tracking",
                "Check the landing page and conversion tracking")
    if cpc > 0.15:
        return (f"cost per click rose {cpc * 100:.0f}%, which suggests more competition in the auction",
                "Review bids and audience overlap")
    return ("a mix of small shifts in click and conversion rates", "Review the audience and bid settings")


def _anomalies(f):
    out = []
    for c in f["campaigns"]:
        p, share = c["prev"], c["spend_share"]
        name = f"{c['campaign']} ({c['platform']})"
        if p and c["cpa_change"] is not None and p["conversions"] >= 10:
            if c["cpa_change"] > 0.25:
                cause, action = _cause(c, p)
                out.append(dict(
                    kind="cpa_up", tone="bad", severity=c["cpa_change"] * max(share, 0.1),
                    message=(f"{name} now costs {fmt_value(c['cpa'], 'money2')} per conversion, "
                             f"up {c['cpa_change'] * 100:.0f}% from {fmt_value(p['cpa'], 'money2')}"),
                    cause=cause, action=action))
            elif c["cpa_change"] < -0.2 and c["conversions"] >= p["conversions"]:
                out.append(dict(
                    kind="winner", tone="good", severity=abs(c["cpa_change"]) * max(share, 0.1),
                    message=(f"{name} improved to {fmt_value(c['cpa'], 'money2')} per conversion, "
                             f"down {abs(c['cpa_change']) * 100:.0f}% from {fmt_value(p['cpa'], 'money2')}"),
                    cause="the audience and creative are working well right now",
                    action="Raise its budget gradually, about 20% at a time, and watch cost per conversion"))
        if c["roas"] is not None and c["roas"] < 1 and share >= 0.08:
            out.append(dict(
                kind="low_roas", tone="bad", severity=(1 - c["roas"]) * max(share, 0.1) * 1.5,
                message=f"{name} returned only {c['roas']:.2f}x on {fmt_value(c['spend'], 'money')} of spend",
                cause="it is spending more than it earns back",
                action="Cut its budget or pause it until the targeting or offer is fixed"))
    for d in f["devices"]:
        pts = d["bounce_change_pts"]
        if pts is not None and pts > 0.05:
            out.append(dict(
                kind="bounce_up", tone="bad", severity=pts * 3,
                message=f"{d['device']} bounce rate rose {pts * 100:.1f} points to {d['bounce_rate'] * 100:.1f}%",
                cause="often a slow page, a broken mobile layout or ads sending people to the wrong page",
                action=f"Run a speed and layout check on the main {d['device'].lower()} landing pages"))
    for ch in f["channels"]:
        if ch["channel"] == "Organic Search" and ch["change"] is not None and ch["change"] > 0.2:
            out.append(dict(
                kind="organic_up", tone="good", severity=ch["change"] * 0.3,
                message=f"Organic search sessions grew {ch['change'] * 100:.0f}% to {ch['sessions']:,.0f}",
                cause="search visibility improved or interest in the brand is rising",
                action="Find which pages gained traffic and link to them from ads and emails"))
    out.sort(key=lambda a: -a["severity"])
    return out[:5]


def _json_default(o):
    return o.item() if hasattr(o, "item") else str(o)


def build_facts(client, ads, ga4, end_date, n_weeks=8):
    end = pd.Timestamp(end_date)
    start = end - pd.Timedelta(days=6)
    pend = start - pd.Timedelta(days=1)
    pstart = pend - pd.Timedelta(days=6)
    cw, pw = (start, end), (pstart, pend)

    cur = _totals(_window(ads, *cw), _window(ga4, *cw))
    prev = _totals(_window(ads, *pw), _window(ga4, *pw))

    kpis = []
    for d in KPI_DEFS:
        v, p = cur[d["key"]], prev[d["key"]]
        ch = pct_change(v, p)
        kpis.append(dict(d, value=v, prev=p, change=ch,
                         value_text=fmt_value(v, d["fmt"]), prev_text=fmt_value(p, d["fmt"]),
                         change_text=fmt_delta(ch), tone=delta_tone(ch, d["good"])))

    f = dict(
        client=dict(name=client["name"], slug=client["slug"]),
        period=dict(start=str(start.date()), end=str(end.date()),
                    label=f"{start:%b %d} - {end:%b %d, %Y}"),
        totals=dict(cur=cur, prev=prev),
        kpis=kpis,
        campaigns=_campaigns(ads, cw, pw, cur["spend"]),
        channels=_channels(ga4, cw, pw),
        devices=_devices(ga4, cw, pw),
        trend=_trend(ads, ga4, end, n_weeks),
    )
    f["anomalies"] = _anomalies(f)
    return json.loads(json.dumps(f, default=_json_default))