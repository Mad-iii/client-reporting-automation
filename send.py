import html
import os
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

SERIF = "Georgia,'Times New Roman',serif"
SANS = "Arial,Helvetica,sans-serif"


def _label(text, c):
    return (f'<div style="font:700 11px {SANS};letter-spacing:1.5px;text-transform:uppercase;'
            f'color:{c["primary"]};border-bottom:1px solid {c["primary"]};padding-bottom:7px;'
            f'margin:34px 0 14px">{html.escape(text)}</div>')


def _kpi(k, c, tone, first, last):
    primary, rule, muted = c["primary"], c["rule"], c["muted"]
    pad = "14px 14px 14px 0" if first else "14px"
    right = "" if last else f"border-right:1px solid {rule};"
    return (
        f'<td valign="top" width="33%" style="padding:{pad};{right}border-top:2px solid {primary};'
        f'border-bottom:1px solid {rule}">'
        f'<div style="font:600 10px {SANS};letter-spacing:1.2px;text-transform:uppercase;color:{muted}">'
        f'{html.escape(k["label"])}</div>'
        f'<div style="font:700 26px {SERIF};color:{primary};padding:5px 0 3px">{html.escape(k["value_text"])}</div>'
        f'<div style="font:700 12px {SANS};color:{tone[k["tone"]]}">{html.escape(k["change_text"])}</div></td>')


def build_email(f, narrative, pdf_path, dash_url, agency, client, logo_path):
    c = agency["colors"]
    e = html.escape
    k = {x["key"]: x for x in f["kpis"]}
    tone = {"good": c["good"], "bad": c["bad"], "flat": c["muted"]}
    primary, accent, ink, muted, rule, paper = (c["primary"], c["accent"], c["ink"], c["muted"],
                                                c["rule"], c["paper"])

    msg = EmailMessage()
    msg["Subject"] = f"{client['name']} | weekly performance report, {f['period']['label']}"
    msg["From"] = agency["from_email"]
    msg["To"] = client["contact_email"]

    steps_txt = "\n".join(f"{i}. {s}" for i, s in enumerate(narrative["next_steps"], start=1))
    msg.set_content(
        f"Hi {client['contact_name']},\n\n"
        f"Here is your weekly performance report for {f['period']['label']}.\n\n"
        f"{narrative['what_happened']}\n\nWhat we recommend:\n{steps_txt}\n\n"
        f"Live dashboard: {dash_url}\nThe full PDF report is attached.\n\n{agency['name']}")

    cid = make_msgid(domain="report.local")
    keys = ("revenue", "roas", "conversions")
    kpi_cells = "".join(_kpi(k[key], c, tone, i == 0, i == len(keys) - 1) for i, key in enumerate(keys))
    steps_html = "".join(
        f'<tr><td valign="top" width="30" style="padding:11px 0;border-bottom:1px solid {rule};'
        f'font:700 20px {SERIF};color:{accent}">{i}</td>'
        f'<td valign="top" style="padding:11px 0;border-bottom:1px solid {rule};font:15px/1.55 {SANS};color:{ink}">'
        f'{e(s)}</td></tr>' for i, s in enumerate(narrative["next_steps"], start=1))
    pre = f"{client['name']}: revenue {k['revenue']['value_text']} ({k['revenue']['change_text']}), ROAS {k['roas']['value_text']}."

    body = f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
<body style="margin:0;padding:0;background:{paper}">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:{paper}">{e(pre)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{paper}"><tr>
<td align="center" style="padding:24px 12px">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:100%;background:#ffffff">
  <tr><td style="height:4px;line-height:4px;font-size:0;background:{primary}">&nbsp;</td></tr>
  <tr><td style="padding:26px 36px 0 36px">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
      <td valign="middle"><img src="cid:{cid[1:-1]}" width="150" alt="{e(agency['name'])}" style="display:block;border:0"></td>
      <td valign="middle" align="right" style="font:700 10px {SANS};letter-spacing:1.4px;text-transform:uppercase;color:{primary}">
        Weekly performance report<br><span style="font:400 12px {SANS};letter-spacing:0;text-transform:none;color:{muted}">{e(f['period']['label'])}</span></td>
    </tr></table>
  </td></tr>
  <tr><td style="padding:16px 36px 0 36px"><div style="border-bottom:1px solid {rule};height:1px;line-height:1px;font-size:0">&nbsp;</div></td></tr>
  <tr><td style="padding:30px 36px 36px 36px">
    <div style="font:14px {SANS};color:{muted};padding-bottom:6px">Hi {e(client['contact_name'])},</div>
    <div style="font:700 30px/1.15 {SERIF};color:{primary};padding-bottom:14px">{e(client['name'])}</div>
    <div style="font:18px/1.55 {SERIF};color:{ink};padding-bottom:26px">{e(narrative['what_happened'])}</div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{kpi_cells}</tr></table>
    {_label('Why it happened', c)}
    <div style="font:15px/1.6 {SANS};color:{ink}">{e(narrative['why'])}</div>
    {_label('What we recommend', c)}
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{steps_html}</table>
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:32px"><tr>
      <td style="background:{primary}"><a href="{e(dash_url)}" style="display:inline-block;padding:13px 26px;font:700 13px {SANS};letter-spacing:.5px;color:#ffffff;text-decoration:none">Open live dashboard</a></td>
    </tr></table>
    <div style="font:12.5px/1.5 {SANS};color:{muted};padding-top:12px">The full PDF report is attached to this email.</div>
  </td></tr>
  <tr><td style="padding:16px 36px 22px 36px;border-top:1px solid {rule};font:11.5px/1.5 {SANS};color:{muted}">
    {e(agency['name'])} &nbsp;|&nbsp; Confidential, prepared for {e(client['name'])}
  </td></tr>
</table>
</td></tr></table>
</body></html>"""
    msg.add_alternative(body, subtype="html")
    html_part = msg.get_body(preferencelist=("html",))
    html_part.add_related(Path(logo_path).read_bytes(), "image", "png", cid=cid)
    msg.add_attachment(Path(pdf_path).read_bytes(), maintype="application", subtype="pdf",
                       filename=Path(pdf_path).name)
    return msg


def deliver(msg, email_cfg, slug, out_dir):
    mode = email_cfg.get("mode", "eml")
    if mode == "gmail":
        user, pw = os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"]
        del msg["From"]
        msg["From"] = user
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(user, pw)
            s.send_message(msg)
        return f"sent to {msg['To']}"
    path = Path(out_dir) / "emails" / f"{slug}.eml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(msg))
    return str(path)