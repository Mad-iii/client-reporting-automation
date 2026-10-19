def safe_div(a, b):
    try:
        if b is None or float(b) == 0:
            return None
        return float(a) / float(b)
    except (TypeError, ValueError):
        return None


def pct_change(cur, prev):
    if cur is None or prev in (None, 0):
        return None
    return (cur - prev) / prev


def fmt_value(v, fmt):
    if v is None:
        return "-"
    if fmt == "money":
        return f"${v:,.0f}"
    if fmt == "money2":
        return f"${v:,.2f}"
    if fmt == "x":
        return f"{v:.2f}x"
    if fmt == "pct":
        return f"{v * 100:.1f}%"
    return f"{v:,.0f}"


def fmt_delta(change):
    return "n/a" if change is None else f"{change * 100:+.1f}%"


def delta_tone(change, good):
    """good = 'up' | 'down' | 'neutral'. Returns 'good' | 'bad' | 'flat'."""
    if change is None or abs(change) < 0.005 or good == "neutral":
        return "flat"
    went_up = change > 0
    return "good" if (went_up and good == "up") or (not went_up and good == "down") else "bad"


def campaign_display_rows(f):
    rows = []
    for c in f["campaigns"]:
        rows.append(dict(
            name=c["campaign"],
            platform=c["platform"],
            spend=fmt_value(c["spend"], "money"),
            revenue=fmt_value(c["revenue"], "money"),
            roas=fmt_value(c["roas"], "x"),
            cpa=fmt_value(c["cpa"], "money2"),
            cpa_change=fmt_delta(c["cpa_change"]),
            tone=delta_tone(c["cpa_change"], "down"),
        ))
    return rows