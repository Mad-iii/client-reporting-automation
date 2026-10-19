import hashlib
import json
import os
import re
from pathlib import Path

import requests

SYSTEM_PROMPT = (
    "You are a senior paid-media analyst writing a weekly report for a non-technical business owner. "
    "Use ONLY numbers that appear in the fact sheet. Never invent numbers, percentages or causes "
    "beyond those given. Plain language, no jargon, no markdown, no numbered lists."
)

USER_TEMPLATE = """{facts}

Write exactly three sections. Put each header on its own line:
WHAT HAPPENED
WHY
WHAT TO DO NEXT

WHAT HAPPENED: 2-3 sentences summarising the week.
WHY: 2-3 sentences explaining the main drivers, using the likely causes given.
WHAT TO DO NEXT: 3 short lines, each starting with "- ", based on the suggested actions."""


def facts_to_text(f):
    lines = [f"Client: {f['client']['name']}", f"Week: {f['period']['label']}", "",
             "KPIs (this week vs last week):"]
    for k in f["kpis"]:
        lines.append(f"- {k['label']}: {k['value_text']} ({k['change_text']} vs last week, was {k['prev_text']})")
    lines += ["", "Campaigns:"]
    for c in f["campaigns"]:
        lines.append(f"- {c['campaign']} ({c['platform']}): spend ${c['spend']:,.0f}, "
                     f"ROAS {c['roas'] or 0:.2f}x, cost per conversion ${c['cpa'] or 0:,.2f}")
    lines += ["", "Detected issues and wins:"]
    for a in f["anomalies"] or []:
        lines.append(f"- [{a['tone']}] {a['message']}. Likely cause: {a['cause']}. "
                     f"Suggested action: {a['action']}.")
    if not f["anomalies"]:
        lines.append("- Nothing unusual this week.")
    return "\n".join(lines)


# ---------- safety net: every number the model writes must exist in the fact sheet ----------
NUM = re.compile(r"\d[\d,]*\.?\d*")


def _norm(tok):
    return tok.replace(",", "").rstrip(".")


def numbers_ok(output, fact_text):
    allowed = {_norm(t) for t in NUM.findall(fact_text)}
    for tok in NUM.findall(output):
        n = _norm(tok)
        if n in allowed:
            continue
        try:
            if float(n) <= 10 and float(n) == int(float(n)):   # small counts like "3 campaigns"
                continue
        except ValueError:
            pass
        return False
    return True


def parse_sections(text):
    text = text.replace("**", "")
    m = re.search(r"WHAT HAPPENED\s*:?\s*(.*?)\s*WHY\s*:?\s*(.*?)\s*WHAT TO DO NEXT\s*:?\s*(.*)",
                  text, re.S | re.I)
    if not m:
        return None
    what, why, nxt = (x.strip() for x in m.groups())
    steps = [re.sub(r"^[-*\u2022]\s*", "", l).strip() for l in nxt.splitlines() if l.strip()]
    steps = [s for s in steps if s][:4]
    if not (what and why and steps):
        return None
    return dict(what_happened=what, why=why, next_steps=steps)


# ---------- providers ----------
def _chat_openrouter(messages, cfg):
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    for model in cfg["openrouter_models"]:
        if not (model.endswith(":free") or model == "openrouter/free"):
            print(f"  [openrouter] skipping {model}: not a free model")
            continue
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model, "messages": messages, "temperature": 0.3},
            timeout=cfg.get("timeout", 60),
        )
        if r.ok:
            try:
                text = r.json()["choices"][0]["message"]["content"]
                if text and text.strip():
                    print(f"  [openrouter] model used: {model}")
                    return text
            except (KeyError, IndexError, TypeError):
                pass
            print(f"  [openrouter] {model}: empty or unexpected response, trying next")
            continue
        body = r.text[:300]
        if r.status_code == 402:
            raise RuntimeError(f"OpenRouter credit problem (402): {body}")
        if r.status_code == 429 and "upstream" not in body.lower() and "provider returned" not in body.lower():
            # account-level cap (per-minute or per-day): more requests would only waste quota
            raise RuntimeError(f"OpenRouter account limit hit (429): {body}")
        print(f"  [openrouter] {model}: HTTP {r.status_code}, trying next")
    raise RuntimeError("no free model answered")

def _chat_ollama(messages, cfg):
    r = requests.post(
        "http://localhost:11434/api/chat",
        json={"model": cfg["ollama_model"], "messages": messages, "stream": False,
              "options": {"temperature": 0.3}},
        timeout=cfg.get("timeout", 60) * 3,
    )
    r.raise_for_status()
    return r.json()["message"]["content"]


PROVIDERS = {"openrouter": _chat_openrouter, "ollama": _chat_ollama}


# ---------- no-LLM fallback (always works) ----------
def _chg(k):
    c = k["change"]
    if c is None or abs(c) < 0.005:
        return "flat"
    return f"{'up' if c > 0 else 'down'} {abs(c) * 100:.1f}%"


def template_narrative(f):
    k = {x["key"]: x for x in f["kpis"]}
    what = (f"{f['client']['name']} spent {k['spend']['value_text']} on ads this week and generated "
            f"{k['revenue']['value_text']} in revenue ({_chg(k['revenue'])} compared with last week). "
            f"Return on ad spend was {k['roas']['value_text']} and the website had "
            f"{k['sessions']['value_text']} sessions ({_chg(k['sessions'])}).")
    camps = [c for c in f["campaigns"] if c["roas"] is not None and c["spend_share"] >= 0.08]
    if camps:
        best = max(camps, key=lambda c: c["roas"])
        what += f" The strongest campaign was {best['campaign']} at {best['roas']:.2f}x return."

    anomalies = f["anomalies"]
    if anomalies:
        why = " ".join(f"{a['message']}: {a['cause']}." for a in anomalies[:2])
    else:
        why = "Results moved in line with normal week-to-week variation; no campaign changed enough to raise a flag."
    steps = [a["action"] for a in anomalies[:3]] or ["Keep current budgets and review again next week"]
    return dict(what_happened=what, why=why, next_steps=steps)


def get_narrative(f, cfg, cache_dir="output/cache", use_llm=True):
    text = facts_to_text(f)
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(text.encode()).hexdigest()[:16]
    cache_file = Path(cache_dir) / f"{f['client']['slug']}-{key}.json"

    if use_llm and cache_file.exists():            # same facts = no new request (saves free quota)
        return json.loads(cache_file.read_text())

    if use_llm:
        messages = [{"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": USER_TEMPLATE.format(facts=text)}]
        for name in cfg["providers"]:
            if name == "template":
                break
            try:
                raw = PROVIDERS[name](messages, cfg)
                parsed = parse_sections(raw)
                if parsed and numbers_ok(raw, text):
                    parsed["source"] = name
                    cache_file.write_text(json.dumps(parsed))
                    return parsed
                print(f"  [{name}] output rejected (bad format or unknown numbers), trying next")
            except Exception as e:
                print(f"  [{name}] unavailable: {e}")

    out = template_narrative(f)
    out["source"] = "template"
    return out