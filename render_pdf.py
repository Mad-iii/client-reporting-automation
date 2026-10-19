from xml.sax.saxutils import escape

from reportlab.lib import colors as rl
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

from utils import campaign_display_rows

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN          # 174 mm
LOGO_W = 38 * mm


def _styles(C):
    base = ParagraphStyle("base", fontName="Helvetica", fontSize=9.5, leading=14.5, textColor=C["ink"])
    return dict(
        base=base,
        title=ParagraphStyle("title", parent=base, fontName="Times-Bold", fontSize=27, leading=31,
                             textColor=C["primary"]),
        meta=ParagraphStyle("meta", parent=base, fontSize=8.5, leading=12, textColor=C["muted"]),
        lede=ParagraphStyle("lede", parent=base, fontName="Times-Roman", fontSize=13.5, leading=19.5),
        label=ParagraphStyle("label", parent=base, fontName="Helvetica-Bold", fontSize=7.5, leading=10,
                             textColor=C["primary"]),
        kpi_label=ParagraphStyle("kl", parent=base, fontName="Helvetica-Bold", fontSize=6.6, leading=9,
                                 textColor=C["muted"]),
        kpi_value=ParagraphStyle("kv", parent=base, fontName="Times-Bold", fontSize=21, leading=25,
                                 textColor=C["primary"]),
        kpi_delta=ParagraphStyle("kd", parent=base, fontSize=8.5, leading=11),
        action_no=ParagraphStyle("ano", parent=base, fontName="Times-Bold", fontSize=16, leading=18,
                                 textColor=C["accent"]),
        th_l=ParagraphStyle("thl", parent=base, fontName="Helvetica-Bold", fontSize=6.6, leading=9,
                            textColor=C["muted"]),
        th=ParagraphStyle("th", parent=base, fontName="Helvetica-Bold", fontSize=6.6, leading=9,
                          textColor=C["muted"], alignment=TA_RIGHT),
        cell=ParagraphStyle("cell", parent=base, fontSize=8.8, leading=11.5),
        num=ParagraphStyle("num", parent=base, fontSize=8.8, leading=11.5, alignment=TA_RIGHT),
        tiny=ParagraphStyle("tiny", parent=base, fontSize=7.2, leading=10, textColor=C["muted"]),
    )


def _section(title, st, C):
    t = Table([[Paragraph(escape(title).upper(), st["label"])]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.7, C["primary"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _img(path):
    iw, ih = ImageReader(path).getSize()
    return Image(path, width=CONTENT_W, height=CONTENT_W * ih / iw)


def build_pdf(f, narrative, charts, brand, logo_path, out_path):
    hexes = brand["colors"]
    C = {k: rl.HexColor(v) for k, v in hexes.items()}
    st = _styles(C)
    tone_hex = {"good": hexes["good"], "bad": hexes["bad"], "flat": hexes["muted"]}
    lw, lh = ImageReader(logo_path).getSize()
    logo_h = LOGO_W * lh / lw

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(C["primary"])
        canvas.rect(0, PAGE_H - 3 * mm, PAGE_W, 3 * mm, stroke=0, fill=1)
        canvas.drawImage(logo_path, MARGIN, PAGE_H - 8 * mm - logo_h, width=LOGO_W, height=logo_h, mask="auto")
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(C["primary"])
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 12 * mm, "WEEKLY PERFORMANCE REPORT")
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(C["muted"])
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 16 * mm, f["period"]["label"])
        canvas.setStrokeColor(C["rule"])
        canvas.setLineWidth(0.5)
        y = PAGE_H - 8 * mm - logo_h - 3 * mm
        canvas.line(MARGIN, y, PAGE_W - MARGIN, y)
        canvas.line(MARGIN, 14 * mm, PAGE_W - MARGIN, 14 * mm)
        canvas.setFont("Helvetica", 7)
        foot = f"{brand['name']}  |  Confidential, prepared for {f['client']['name']}"
        if brand.get("demo_notice"):
            foot += f"  |  {brand['demo_notice']}"
        canvas.drawString(MARGIN, 10 * mm, foot)
        canvas.drawRightString(PAGE_W - MARGIN, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(out_path, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=29 * mm, bottomMargin=20 * mm,
                            title=f"{f['client']['name']} - weekly performance report", author=brand["name"])

    # KPI strip: 4 x 2, hairlines only
    cells = []
    for k in f["kpis"]:
        col = tone_hex[k["tone"]]
        cells.append([
            Paragraph(escape(k["label"]).upper(), st["kpi_label"]),
            Paragraph(escape(k["value_text"]), st["kpi_value"]),
            Paragraph(f'<font color="{col}"><b>{escape(k["change_text"])}</b></font>', st["kpi_delta"]),
        ])
    grid = Table([cells[:4], cells[4:]], colWidths=[CONTENT_W / 4] * 4)
    grid.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 1.3, C["primary"]),
        ("LINEBELOW", (0, 0), (-1, 1), 0.5, C["rule"]),
        ("LINEAFTER", (0, 0), (2, -1), 0.5, C["rule"]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
    ]))

    # Numbered actions
    arows = [[Paragraph(str(i), st["action_no"]), Paragraph(escape(s), st["base"])]
             for i, s in enumerate(narrative["next_steps"], start=1)]
    actions = Table(arows, colWidths=[11 * mm, CONTENT_W - 11 * mm])
    actions.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, C["rule"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))

    # Campaign table
    muted = hexes["muted"]
    rows = campaign_display_rows(f)

    def num(text, color=None, bold=False):
        t = escape(text)
        if bold:
            t = f"<b>{t}</b>"
        if color:
            t = f'<font color="{color}">{t}</font>'
        return Paragraph(t, st["num"])

    data = [[Paragraph("CAMPAIGN", st["th_l"])] +
            [Paragraph(x, st["th"]) for x in ("SPEND", "REVENUE", "ROAS", "COST / CONV.", "CHANGE")]]
    for r in rows:
        name = (f'{escape(r["name"])}<br/><font size="7" color="{muted}">{escape(r["platform"])}</font>')
        data.append([Paragraph(name, st["cell"]), num(r["spend"]), num(r["revenue"]),
                     num(r["roas"], bold=True), num(r["cpa"]),
                     num(r["cpa_change"], color=tone_hex[r["tone"]], bold=True)])
    table = Table(data, colWidths=[68 * mm, 24 * mm, 24 * mm, 18 * mm, 24 * mm, 16 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 1.0, C["primary"]),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, C["rule"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, -1), 0), ("RIGHTPADDING", (-1, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    note = ("Commentary is AI-assisted; every figure is verified against the underlying data."
            if narrative["source"] != "template" else
            "Commentary is generated automatically from the underlying data.")

    story = [
        Paragraph(escape(f["client"]["name"]), st["title"]),
        Spacer(1, 3),
        Paragraph(f"Week of {escape(f['period']['label'])}  |  changes compared with the previous week", st["meta"]),
        Spacer(1, 14),
        Paragraph(escape(narrative["what_happened"]), st["lede"]),
        Spacer(1, 16),
        grid,
        Spacer(1, 18),
        KeepTogether([_section("Why it happened", st, C), Spacer(1, 8),
                      Paragraph(escape(narrative["why"]), st["base"])]),
        Spacer(1, 18),
        KeepTogether([_section("Recommended actions", st, C), Spacer(1, 2), actions]),
        Spacer(1, 18),
        KeepTogether([_section("Revenue and ad spend, last eight weeks", st, C), Spacer(1, 8), _img(charts["trend"])]),
        Spacer(1, 18),
        KeepTogether([_section("Campaign performance", st, C), Spacer(1, 4), table]),
        Spacer(1, 18),
        KeepTogether([_section("Return on ad spend by campaign", st, C), Spacer(1, 8), _img(charts["campaigns"])]),
        Spacer(1, 18),
        KeepTogether([_section("Website sessions by channel", st, C), Spacer(1, 8), _img(charts["channels"])]),
        Spacer(1, 12),
        Paragraph(note, st["tiny"]),
    ]
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return out_path