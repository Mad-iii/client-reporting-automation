import zlib
import numpy as np
import pandas as pd

WEEKDAY_FACTOR = [1.00, 1.00, 1.02, 1.05, 1.08, 1.12, 0.95]   # Mon..Sun

# base bounce rate per GA4 channel
CHANNELS = {
    "Organic Search": 0.45,
    "Direct": 0.38,
    "Email": 0.30,
    "Paid Social": 0.55,
    "Paid Search": 0.40,
}


def _rng(client):
    return np.random.default_rng(client.get("seed", zlib.crc32(client["slug"].encode())))


def fetch_ads(client, start, end):
    """Daily rows for Meta Ads + Google Ads. 'shock' only affects the report week."""
    rng = _rng(client)
    rows = []
    for camp in client["campaigns"]:
        shock = camp.get("shock", {})
        for d in pd.date_range(start, end):
            s = shock if d > end - pd.Timedelta(days=7) else {}
            spend = camp["spend"] * rng.normal(1, 0.04) * s.get("spend", 1.0)
            impressions = int(spend / camp["cpm"] * 1000)
            ctr = camp["ctr"] * rng.normal(1, 0.06) * s.get("ctr", 1.0)
            clicks = int(rng.binomial(impressions, min(max(ctr, 0), 1)))
            cvr = camp["cvr"] * WEEKDAY_FACTOR[d.weekday()] * s.get("cvr", 1.0)
            conversions = int(rng.binomial(clicks, min(max(cvr, 0), 1)))
            revenue = conversions * camp["value"] * rng.normal(1, 0.08)
            rows.append((d, camp["platform"], camp["name"], round(spend, 2),
                         impressions, clicks, conversions, round(revenue, 2)))
    return pd.DataFrame(rows, columns=["date", "platform", "campaign", "spend",
                                       "impressions", "clicks", "conversions", "revenue"])


def fetch_ga4(client, start, end, ads):
    """Daily rows per channel and device. Paid sessions are derived from ad clicks
    so the numbers across platforms stay consistent."""
    rng = _rng(client)
    g = client["ga4"]
    shock_all = g.get("shock", {})
    clicks = ads.groupby(["date", "platform"])["clicks"].sum()
    rows = []
    for d in pd.date_range(start, end):
        shock = shock_all if d > end - pd.Timedelta(days=7) else {}
        for channel, base_bounce in CHANNELS.items():
            if channel == "Paid Social":
                base = clicks.get((d, "Meta Ads"), 0) * 0.9
            elif channel == "Paid Search":
                base = clicks.get((d, "Google Ads"), 0) * 0.9
            elif channel == "Organic Search":
                base = g["organic"] * shock.get("organic_mult", 1.0)
            elif channel == "Direct":
                base = g["direct"]
            else:
                base = g["email"]
            base *= rng.normal(1, 0.06) * WEEKDAY_FACTOR[d.weekday()]
            devices = (
                ("Mobile", g["mobile_share"], 0.05 + shock.get("mobile_bounce_add", 0.0)),
                ("Desktop", 1 - g["mobile_share"], -0.05),
            )
            for device, share, offset in devices:
                sessions = int(max(base * share, 0))
                p = min(max(base_bounce + g.get("bounce_adj", 0.0) + offset, 0.02), 0.95)
                bounces = int(rng.binomial(sessions, p))
                rows.append((d, channel, device, sessions, bounces))
    return pd.DataFrame(rows, columns=["date", "channel", "device", "sessions", "bounces"])