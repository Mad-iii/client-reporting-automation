from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

from utils import campaign_display_rows

INDEX = Template("""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ a.name }} | Client dashboards</title>
<style>
  html{background:{{ a.colors.paper }}}
  body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;color:{{ a.colors.ink }}}
  .bar{height:4px;background:{{ a.colors.primary }}}
  .wrap{max-width:760px;margin:0 auto;padding:0 28px 64px}
  .mast{padding:22px 0 18px;border-bottom:1px solid {{ a.colors.rule }}}
  .mast img{height:38px;display:block}
  h1{font-family:Georgia,"Times New Roman",serif;font-size:36px;color:{{ a.colors.primary }};margin:40px 0 6px}
  p.sub{color:{{ a.colors.muted }};margin:0 0 30px;font-size:14px}
  h2{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:{{ a.colors.primary }};
     border-bottom:1px solid {{ a.colors.primary }};padding-bottom:8px;margin:0}
  a.row{display:flex;justify-content:space-between;align-items:baseline;padding:16px 0;border-bottom:1px solid {{ a.colors.rule }};
     text-decoration:none;color:{{ a.colors.primary }}}
  a.row b{font-family:Georgia,"Times New Roman",serif;font-size:21px}
  a.row span{color:{{ a.colors.muted }};font-size:13px}
  a.row:hover b{text-decoration:underline}
</style></head><body>
<div class="bar"></div>
<div class="wrap">
  <div class="mast"><img src="../logo.png" alt="{{ a.name }}"></div>
  <h1>Client dashboards</h1>
  <p class="sub">Weekly performance, one page per client.</p>
  <h2>Clients</h2>
  {% for c in clients %}<a class="row" href="{{ c.slug }}.html"><b>{{ c.name }}</b><span>{{ c.period }}</span></a>{% endfor %}
</div></body></html>""")


def build_dashboard(f, narrative, brand, pdf_name, out_dir):
    env = Environment(loader=FileSystemLoader("templates"), autoescape=select_autoescape(["html"]))
    html = env.get_template("dashboard.html").render(
        f=f, n=narrative, c=brand["colors"], a=brand,
        rows=campaign_display_rows(f), pdf_name=pdf_name)
    path = Path(out_dir) / f"{f['client']['slug']}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


def build_index(items, brand, out_dir):
    path = Path(out_dir) / "index.html"
    path.write_text(INDEX.render(a=brand, clients=items), encoding="utf-8")
    return path