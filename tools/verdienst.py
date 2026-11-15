#!/usr/bin/env python3
"""Berechnet den Verdienst pro Produkt fuer das Dashboard (Bereich "verdienst").
Aufruf: python3 verdienst.py <ek.json> <namen.txt> <woche.txt> <vorwoche.txt> <q13.txt> <von_bis.json> <ausgabe.json>
- ek.json: {"Produktname in Vendon": [ek_netto, pfand, ust, "Quelle"] | {"ust": 7}}  (aus Google-Tabelle "Produkt-EK")
- namen.txt: je Zeile  id|Name|Anzahl Faecher  (Vendon shelfanalysis)
- woche/vorwoche/q13.txt: je Zeile oder mit ; getrennt  id|Stueck|Umsatz brutto
- von_bis.json: {"woche":["2026-11-09","2026-11-15"], "vorwoche":[...], "q13":[...], "stand":"..."}
Gewinn = Umsatz/(1+USt) - (EK netto + Pfand) * Stueck. Produkte ohne EK: Gewinn null."""
import sys, json

def lies(path):
    t = open(path, encoding="utf-8").read().replace(";", "\n")
    return [z.split("|") for z in t.split("\n") if z.strip()]

def main():
    ek, namen = json.load(open(sys.argv[1], encoding="utf-8")), lies(sys.argv[2])
    perioden = dict(zip(("woche", "vorwoche", "q13"), sys.argv[3:6]))
    vb = json.load(open(sys.argv[6], encoding="utf-8"))
    nm = {z[0]: z[1] for z in namen}; fa = {z[0]: int(z[2]) if len(z) > 2 else 0 for z in namen}
    out = {"stand": vb.get("stand", "")}
    for key, path in perioden.items():
        items = []
        for z in lies(path):
            i, s, u = z[0], int(z[1]), float(z[2]); n = nm.get(i, i)
            k = ek.get(n)
            ust = (k[2] if isinstance(k, list) else (k or {}).get("ust", 19)) if k else 19
            un = u / (1 + ust / 100)
            if isinstance(k, list) and k[0] is not None:
                e = k[0] + (k[1] or 0); g = un - e * s
                items.append(dict(n=n, s=s, u=round(u, 2), un=round(un, 2), ek=round(e, 3), g=round(g, 2), gs=round(g / s, 2) if s else None,
                                  m=round(100 * g / un) if un else None, f=fa.get(i, 0)))
            else:
                items.append(dict(n=n, s=s, u=round(u, 2), un=round(un, 2), ek=None, g=None, gs=None, m=None, f=fa.get(i, 0)))
        items.sort(key=lambda x: -x["u"])
        un = sum(x["un"] for x in items); bek = [x for x in items if x["g"] is not None]
        g = sum(x["g"] for x in bek); ub = sum(x["un"] for x in bek)
        out[key] = dict(von=vb[key][0], bis=vb[key][1], items=items, sum=dict(
            stueck=sum(x["s"] for x in items), umsatz=round(sum(x["u"] for x in items), 2), umsatz_netto=round(un, 2),
            gewinn=round(g, 2), abdeckung=round(100 * ub / un) if un else 0, marge=round(100 * g / ub) if ub else None,
            gewinn_hochgerechnet=round(g / ub * un, 2) if ub else None))
    json.dump(out, open(sys.argv[7], "w", encoding="utf-8"), ensure_ascii=False)
    for k in ("woche", "vorwoche", "q13"): print(k, out[k]["sum"])

if __name__ == "__main__":
    main()
