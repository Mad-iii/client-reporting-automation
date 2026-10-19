# Automated Client Reporting

Weekly marketing reports for agency clients, generated automatically: data pulled from
Meta Ads, Google Ads and GA4, an AI-written plain-English summary, a branded PDF, a live
dashboard, and a ready-to-send email.

**[Live demo](https://Mad-iii.github.io/client-reporting-automation/)** | [Sample PDF](samples/SAMPLE.pdf)

![Dashboard](docs/dashboard.png)

## What it does
- Pulls ad and analytics data per client (demo uses realistic synthetic data)
- Computes KPIs, week-over-week changes and flags anomalies in code
- Has an LLM explain what happened, why, and what to do next
- Produces a branded PDF, an interactive dashboard and an HTML email with the PDF attached
- Runs on a schedule with GitHub Actions and publishes to GitHub Pages

<img src="docs/report.png" width="48%">

## How it works
```
connectors -> metrics engine -> fact sheet -> LLM commentary (verified) -> PDF + dashboard + email
```
- **Connectors:** one module per source returning the same table format, so real APIs
  replace the demo data without touching anything else.
- **Metrics engine:** all numbers are calculated in code (pandas), never by the model.
- **AI commentary:** the model only receives a fact sheet. Every number it writes is
  checked against that sheet; if it invents one, the output is rejected and a
  template is used instead. Providers: OpenRouter free models, then templates.
- **Cost:** $0 to run (free-tier models, open-source libraries, GitHub free hosting).

## Run it locally
```bash
pip install -r requirements.txt
python run.py            # add --no-llm to skip the AI step
```
Optional: add `OPENROUTER_API_KEY` to a `.env` file for AI-written commentary.

## Stack
Python, pandas, matplotlib, ReportLab, Jinja2, Chart.js, GitHub Actions, OpenRouter.

## Notes
All clients and figures in this demo are fictional. Going to production would involve
real API connectors (Meta Marketing API, Google Ads API, GA4 Data API), per-client
authentication, private dashboards, and a review step before sending.