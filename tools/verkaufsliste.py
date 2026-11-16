#!/usr/bin/env python3
"""Monatliche Verkaufsliste (Einzelaufzeichnung) für den Snackautomaten – immer gleiches Layout.

Aufruf:
  python3 tools/verkaufsliste.py <vends.json> <ust.json> <JJJJ-MM> <ziel.pdf> <vk.json> [--test] [--von TT.MM.JJJJ] [--bis TT.MM.JJJJ]
  --von: erster Tag, falls der Monatsanfang schon über eine frühere Leerungs-Buchung in Lexware erfasst ist.

vends.json : Liste aus Vendon /rest/head/stats/vends (Felder transaction_id, datetime, selection,
             name, quantity, price, vat, payment_method) – alle Verkäufe des Monats.
ust.json   : {"Produktname in Vendon": 7|19} aus dem Blatt „Produkt-EK“, Spalte „USt Verkauf %“.
             Fehlt ein Produkt, gilt die Regel aus ust_produkte.py und es erscheint ein Hinweis.
Ausgabe    : PDF (Beleg für Lexware) und vk.json (Bereich „verkaufsliste“ fürs Dashboard, #freigabe).
Netto/USt der Zusammenfassung = aus der Bruttosumme je Steuersatz (so wird in Lexware gebucht).
"""
import sys, os, json, datetime, zoneinfo, hashlib
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ust_produkte import ust_verkauf

pdfmetrics.registerFont(TTFont("DV", os.path.join(HERE, "fonts", "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DVB", os.path.join(HERE, "fonts", "DejaVuSans-Bold.ttf")))
F, FB = "DV", "DVB"
TZ = zoneinfo.ZoneInfo("Europe/Berlin")
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]


def e(x):
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main():
    a = [x for i, x in enumerate(sys.argv[1:], 1) if not x.startswith("--") and sys.argv[i - 1] not in ("--von", "--bis")]
    vends_p, ust_p, monat, out_pdf, out_vk = a[:5]
    test = "--test" in sys.argv
    bis_arg = sys.argv[sys.argv.index("--bis") + 1] if "--bis" in sys.argv else None
    von_arg = sys.argv[sys.argv.index("--von") + 1] if "--von" in sys.argv else None
    J, M = map(int, monat.split("-"))
    von_d = datetime.datetime.strptime(von_arg, "%d.%m.%Y").date() if von_arg else datetime.date(J, M, 1)
    bis_d = (datetime.date(J + (M == 12), M % 12 + 1, 1) - datetime.timedelta(days=1)) if not bis_arg else datetime.datetime.strptime(bis_arg, "%d.%m.%Y").date()
    von, bis = von_d.strftime("%d.%m.%Y"), bis_d.strftime("%d.%m.%Y")
    beleg = f"{M:02d}-{J}"
    vends = json.load(open(vends_p, encoding="utf-8"))
    if isinstance(vends, dict):
        vends = vends.get("result", [])
    ust_map = json.load(open(ust_p, encoding="utf-8")) if os.path.exists(ust_p) else {}
    data, fehlt = [], set()
    for x in sorted(vends, key=lambda x: (x["datetime"], x["transaction_id"])):
        dt = datetime.datetime.fromtimestamp(x["datetime"], TZ)
        if not (von_d <= dt.date() <= bis_d):
            continue
        n = x["name"]; q = int(x.get("quantity") or 1); b = round(float(x["price"]) * q, 2)
        if n in ust_map and str(ust_map[n]).strip() in ("7", "19"):
            v = int(ust_map[n])
        else:
            v = ust_verkauf(n); fehlt.add(n)
        net = round(b / (1 + v / 100), 2)
        pay = "Bar" if x.get("payment_method") == "CASH" else str(x.get("payment_method") or "")
        data.append(dict(dt=dt, tx=x["transaction_id"], sel=x.get("selection", ""), n=n, q=q, b=b, v=v, net=net, st=round(b - net, 2), vv=x.get("vat", ""), pay=pay))
    for i, d in enumerate(data):
        d["nr"] = i + 1
    S = {7: [0, 0.0], 19: [0, 0.0]}
    for d in data:
        S[d["v"]][0] += d["q"]; S[d["v"]][1] += d["b"]
    summen = {}
    for v in (7, 19):
        br = round(S[v][1], 2); nt = round(br / (1 + v / 100), 2)
        summen[str(v)] = dict(s=S[v][0], b=br, n=nt, u=round(br - nt, 2))
    summen["ges"] = dict(s=S[7][0] + S[19][0], b=round(S[7][1] + S[19][1], 2))
    zahlarten = sorted({d["pay"] for d in data})
    erstellt = datetime.datetime.now(TZ)

    # ---------- PDF ----------
    H = ParagraphStyle("h", fontName=FB, fontSize=13, leading=16, spaceAfter=4)
    N = ParagraphStyle("n", fontName=F, fontSize=8, leading=10.5)
    PR = ParagraphStyle("p", fontName=F, fontSize=7, leading=8)
    story = [Paragraph("SnackDirWas GmbH – Einzelaufzeichnung der Verkäufe (Warenautomat)", H),
             Paragraph(f"Automat: „Snack dir was GmbH“, Löwentorstr. 10, 99752 Bleicherode · Vendon-Gerät 522103<br/>"
                       f"Zeitraum: {von} – {bis} · Zahlart: {', '.join(zahlarten) or '–'} · Quelle: Vendon Cloud, Transaktionsprotokoll (Echtzeit-Telemetrie)<br/>"
                       f"Erstellt: {erstellt.strftime('%d.%m.%Y %H:%M')} Uhr · Lexware-Beleg: Einnahmen {beleg} (Sammlekunde, Allgemeiner)", N),
             Spacer(1, 3 * mm)]
    if test:
        story += [Paragraph("<b>TESTAUSDRUCK – nicht gebucht</b>", ParagraphStyle("t", fontName=FB, fontSize=9, textColor=colors.red)), Spacer(1, 2 * mm)]
    st = [["USt-Satz", "Stück", "Brutto €", "Netto €", "USt €"]] + \
         [[f"{v} %", summen[str(v)]["s"], e(summen[str(v)]["b"]), e(summen[str(v)]["n"]), e(summen[str(v)]["u"])] for v in (7, 19)] + \
         [["Summe", summen["ges"]["s"], e(summen["ges"]["b"]), e(summen["7"]["n"] + summen["19"]["n"]), e(summen["7"]["u"] + summen["19"]["u"])]]
    t = Table(st, colWidths=[30 * mm, 20 * mm, 30 * mm, 30 * mm, 30 * mm])
    t.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), F, 8.5), ("FONT", (0, 0), (-1, 0), FB, 8.5), ("FONT", (0, -1), (-1, -1), FB, 8.5),
                           ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("GRID", (0, 0), (-1, -1), .3, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee"))]))
    story += [Paragraph("<b>Zusammenfassung</b>", N), t, Spacer(1, 3 * mm),
              Paragraph("Hinweis zur Umsatzsteuer: Der Steuersatz je Verkauf wird nach der Art der Ware zugeordnet (§ 12 Abs. 2 Nr. 1 UStG i. V. m. Anlage 2): "
                        "Lebensmittel 7 %, Getränke 19 %, Milch und Milchmischgetränke mit mind. 75 % Milchanteil 7 %, sonstige Waren 19 %. "
                        "Der in den Vendon-Stammdaten hinterlegte Satz ist teils unvollständig und steht nur zur Information in der Spalte „Vendon“. "
                        "Maßgeblich ist die Spalte „USt“. Die Zusammenfassung rechnet Netto/USt aus der Bruttosumme je Steuersatz (wie in Lexware gebucht); "
                        "die Summe der Einzelzeilen kann deshalb um wenige Cent abweichen.", N),
              Spacer(1, 4 * mm), Paragraph("<b>Einzelne Verkäufe (chronologisch)</b>", N)]
    tb = [["Nr.", "Datum / Uhrzeit", "Transakt.-ID", "Fach", "Produkt", "Menge", "Brutto €", "USt", "Netto €", "USt €", "Vendon"]]
    dayrows = []; day = None; acc = None

    def flush():
        tb.append(["", f"Summe {day}", "", "", "", str(acc[0]), e(acc[1]), "", e(acc[2]), e(acc[3]), ""]); dayrows.append(len(tb) - 1)
    for d in data:
        dd = d["dt"].strftime("%d.%m.%Y")
        if dd != day:
            if day: flush()
            day = dd; acc = [0, 0, 0, 0]
        acc[0] += d["q"]; acc[1] += d["b"]; acc[2] += d["net"]; acc[3] += d["st"]
        tb.append([d["nr"], d["dt"].strftime("%d.%m.%Y %H:%M:%S"), str(d["tx"]), d["sel"], Paragraph(d["n"], PR), d["q"], e(d["b"]), f"{d['v']} %", e(d["net"]), e(d["st"]), f"{d['vv']} %"])
    if day: flush()
    T = Table(tb, colWidths=[8 * mm, 27 * mm, 22 * mm, 9 * mm, 44 * mm, 10 * mm, 14 * mm, 10 * mm, 14 * mm, 12 * mm, 13 * mm], repeatRows=1)
    sty = [("FONT", (0, 0), (-1, -1), F, 7), ("FONT", (0, 0), (-1, 0), FB, 7), ("ALIGN", (5, 0), (-1, -1), "RIGHT"), ("ALIGN", (0, 0), (0, -1), "RIGHT"),
           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, 0), .6, colors.black), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
           ("TEXTCOLOR", (10, 1), (10, -1), colors.grey), ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]
    for i in dayrows:
        sty += [("FONT", (0, i), (-1, i), FB, 7), ("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f4f4f4")), ("LINEBELOW", (0, i), (-1, i), .3, colors.grey)]
    T.setStyle(TableStyle(sty)); story.append(T)
    pr = {}
    for d in data:
        k = (d["n"], d["v"]); x = pr.setdefault(k, [0, 0, 0, 0]); x[0] += d["q"]; x[1] += d["b"]; x[2] += d["net"]; x[3] += d["st"]
    pt = [["Produkt", "USt", "Stück", "Brutto €", "Netto €", "USt €"]] + \
         [[Paragraph(k[0], ParagraphStyle("q", fontName=F, fontSize=7.5, leading=9)), f"{k[1]} %", x[0], e(x[1]), e(x[2]), e(x[3])]
          for k, x in sorted(pr.items(), key=lambda z: (z[0][1], -z[1][1], z[0][0]))]
    P = Table(pt, colWidths=[70 * mm, 14 * mm, 14 * mm, 22 * mm, 22 * mm, 20 * mm], repeatRows=1)
    P.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), F, 7.5), ("FONT", (0, 0), (-1, 0), FB, 7.5), ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                           ("GRID", (0, 0), (-1, -1), .25, colors.lightgrey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee"))]))
    story += [PageBreak(), Paragraph("<b>Übersicht nach Produkt</b>", N), Spacer(1, 2 * mm), P]

    def foot(c, doc):
        c.setFont(F, 7); c.setFillColor(colors.grey)
        c.drawString(15 * mm, 8 * mm, f"SnackDirWas GmbH · Einzelaufzeichnung Verkäufe {von} – {bis} · {len(data)} Verkäufe · Summe {e(summen['ges']['b'])} €")
        c.drawRightString(195 * mm, 8 * mm, f"Seite {doc.page}")
        if test:
            c.saveState(); c.setFont(FB, 60); c.setFillColor(colors.Color(1, 0, 0, alpha=.08)); c.translate(105 * mm, 150 * mm); c.rotate(45)
            c.drawCentredString(0, 0, "TEST"); c.restoreState()
    SimpleDocTemplate(out_pdf, pagesize=A4, leftMargin=10 * mm, rightMargin=10 * mm, topMargin=12 * mm, bottomMargin=14 * mm,
                      title=f"Einzelaufzeichnung Verkäufe {von}-{bis}", author="SnackDirWas GmbH").build(story, onFirstPage=foot, onLaterPages=foot)

    # ---------- Dashboard-Daten ----------
    produkte = sorted([[k[0], x[0], round(x[1], 2), k[1]] for k, x in pr.items()], key=lambda z: -z[2])
    hinweise = []
    if fehlt:
        hinweise.append("Steuersatz nach Regel gesetzt (nicht im Blatt Produkt-EK): " + ", ".join(sorted(fehlt)))
    if test:
        hinweise.insert(0, "TESTLAUF – bitte NICHT freigeben.")
    kennung = "VK-" + monat + "-" + hashlib.sha1(json.dumps([[d["tx"], d["b"], d["v"]] for d in data]).encode()).hexdigest()[:8]
    vk = dict(monat=monat, label=f"{MONATE[M - 1]} {J}" + (" (TEST)" if test else ""), von=von, bis=bis, beleg=beleg,
              erstellt=erstellt.strftime("%d.%m.%Y %H:%M"), kennung=kennung, status="offen", summen=summen, produkte=produkte, hinweise=hinweise)
    json.dump(vk, open(out_vk, "w", encoding="utf-8"), ensure_ascii=False)
    print("ok", len(data), "Verkäufe", summen, "Kennung", kennung, "ohne Blatt-USt:", len(fehlt))


if __name__ == "__main__":
    main()
