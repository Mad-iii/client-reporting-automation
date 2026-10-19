import pandas as pd
from . import dummy


def fetch_all(client, start, end):
    """The one place to change when going live: call real Meta / Google Ads / GA4 here
    and return two DataFrames with the same columns as the dummy ones."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    ads = dummy.fetch_ads(client, start, end)
    ga4 = dummy.fetch_ga4(client, start, end, ads)
    return ads, ga4