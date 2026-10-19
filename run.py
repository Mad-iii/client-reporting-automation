import argparse
import datetime as dt
import shutil
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()   # reads keys from the .env file in this folder

from assets import make_logo
from charts import make_charts
from connectors import fetch_all
from metrics import build_facts
from narrative import get_narrative
from render_dashboard import build_dashboard, build_index
from render_pdf import build_pdf
from send import build_email, deliver


def last_full_week_end(today=None):
    """Most recent Sunday (weeks run Monday-Sunday)."""
    today = today or dt.date.today()
    return today - dt.timedelta(days=today.weekday() + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--client", help="run a single client slug")
    ap.add_argument("--no-llm", action="store_true", help="skip OpenRouter/Ollama, use templates")
    ap.add_argument("--config", default="config.yaml", help="config file (use another for a white-label sample)")
    ap.add_argument("--out", default="output", help="output folder")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    agency = cfg["agency"]
    out = Path(args.out)
    for sub in ("reports", "dashboards", "charts", "emails"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    logo = out / "logo.png"
    if agency.get("logo_file"):
        shutil.copy(agency["logo_file"], logo)     # the agency's own PNG logo
    else:
        make_logo(logo, agency["name"], agency["colors"])

    end = last_full_week_end()
    start = end - dt.timedelta(days=55)           # 8 weeks of history
    base = agency.get("dashboard_base_url", "").rstrip("/")
    index_items = []

    for client in cfg["clients"]:
        if args.client and client["slug"] != args.client:
            continue
        slug = client["slug"]
        print(f"\n== {client['name']}")
        ads, ga4 = fetch_all(client, start, end)
        facts = build_facts(client, ads, ga4, end)
        narrative = get_narrative(facts, cfg["llm"], use_llm=not args.no_llm)
        print(f"  commentary source: {narrative['source']}")

        charts = make_charts(facts, out / "charts" / slug, agency["colors"])
        pdf_path = out / "reports" / f"{slug}-{end}.pdf"
        build_pdf(facts, narrative, charts, agency, str(logo), str(pdf_path))
        dash_path = build_dashboard(facts, narrative, agency, pdf_path.name, out / "dashboards")

        dash_url = f"{base}/dashboards/{slug}.html" if base else dash_path.resolve().as_uri()
        msg = build_email(facts, narrative, pdf_path, dash_url, agency, client, str(logo))
        print("  email:", deliver(msg, cfg["email"], slug, out))
        index_items.append(dict(slug=slug, name=client["name"], period=facts["period"]["label"]))

    if index_items:
        build_index(index_items, agency, out / "dashboards")
        print("\nDone. Open output/dashboards/index.html")


if __name__ == "__main__":
    main()