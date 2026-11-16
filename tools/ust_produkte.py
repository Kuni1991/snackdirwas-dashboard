# Umsatzsteuer beim VERKAUF am Automaten (Lieferung, kein Vor-Ort-Service), recherchiert 16.11.2026.
# Regel: Lebensmittel/Snacks/Süßwaren 7 % (Anlage 2 UStG); Getränke 19 %; Ausnahme Milch und
# Milchmischgetränke mit >= 75 % Milchanteil ohne Alkohol 7 % (Anlage 2 Nr. 35); Nicht-Lebensmittel 19 %.
# Zweifel -> 7 % (Vorgabe Michael) bzw. Rückfrage, siehe FRAGLICH.
import re
MILCH_7 = ["Milram Kakao", "Münsterl Vanille", "Milka Schokomilch", "Müllermilch", "Nescafe Caramel Latte"]
FRAGLICH = {
 "Nescafe Caramel Latte": "7 % – von Michael festgelegt (16.11.2026)",
 "Secret Pack": "19 % – von Michael festgelegt (16.11.2026)",
}
GETRAENK = r"red bull|cola|desperados|sprite|fanta|wasser|uludag|havana|monster|durstl|fuzetea|spezi|paulaner|capri|hot blood|superpop|rotk|secco|mixery|lillet|28black|koawach|gorbatschow|brause grün|eistee|iced tea|pepsi|jack d"
NONFOOD = r"elfa|elfar|187 |pod|vape|sniff|billy boy|pokemon|booster"
def ust_verkauf(name):
    n = name.lower()
    if name == "Secret Pack": return 19
    if any(m.lower() in n for m in MILCH_7): return 7
    if re.search(NONFOOD, n): return 19
    if re.search(GETRAENK, n): return 19
    return 7   # Snacks, Süßwaren, Chips, Gebäck, Nudeln usw.
def begruendung(name):
    n = name.lower()
    if name in FRAGLICH: return FRAGLICH[name]
    if any(m.lower() in n for m in MILCH_7): return "Milchmischgetränk >= 75 % Milch – 7 %"
    if re.search(NONFOOD, n): return "kein Lebensmittel (Nikotin/Vape/Sonstiges) – 19 %"
    if re.search(GETRAENK, n): return "Getränk – 19 %"
    return "Lebensmittel/Snack – 7 %"
