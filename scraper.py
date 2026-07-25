#!/usr/bin/env python3
"""Preia cursul EUR/USD/GBP/CHF si scrie rates.json.
- BNR: feedul oficial XML (sigur), pentru fiecare moneda.
- Banci: paginile publice cursvalutarbanci.ro (cumparare+vanzare pe banca).
Nu suprascrie o valoare buna anterioara cu una goala."""
import json, re, sys, datetime, urllib.request, xml.etree.ElementTree as ET

UA = "Mozilla/5.0 (curs-eur GitHub Action; +https://github.com)"
CURRENCIES = ["EUR", "USD", "GBP", "CHF"]
PLAUS = {"EUR": (4.4, 6.2), "USD": (3.8, 5.6), "GBP": (5.0, 7.5), "CHF": (4.8, 6.8)}
PAGES = {
    "EUR": "https://www.cursvalutarbanci.ro/curs-euro.html",
    "USD": "https://www.cursvalutarbanci.ro/curs-dolar-american.html",
    "GBP": "https://www.cursvalutarbanci.ro/curs-lira-sterlina.html",
    "CHF": "https://www.cursvalutarbanci.ro/curs-franc-elvetian.html",
}
BANKS = ["Banca Transilvania", "BCR", "BRD", "UniCredit Bank", "ING Bank",
         "Raiffeisen Bank", "CEC Bank", "EximBank", "Libra Bank",
         "Intesa Sanpaolo Bank", "Patria Bank"]

NUM = r"([0-9]{1,2}[.,][0-9]{3,4})"

def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def bnr_all():
    xml = get("https://www.bnr.ro/nbrfxrates.xml")
    root = ET.fromstring(xml)
    ns = {"n": "http://www.bnr.ro/xsd"}
    cube = root.find(".//n:Cube", ns)
    date = cube.attrib.get("date") if cube is not None else None
    out = {}
    for rate in root.findall(".//n:Rate", ns):
        c = rate.attrib.get("currency")
        if c in CURRENCIES:
            mult = float(rate.attrib.get("multiplier", "1"))
            out[c] = round(float(rate.text) / mult, 4)
    return date, out

def banks_for(cur):
    lo, hi = PLAUS[cur]
    out = {}
    try:
        html = get(PAGES[cur])
    except Exception as e:
        print(f"  {cur}: sursa indisponibila: {e}", file=sys.stderr)
        return out
    block = re.compile(r"Cump[a\u0103\u00e2]rare.{0,120}?" + NUM +
                       r".{0,200}?V[a\u00e2]nzare.{0,120}?" + NUM, re.I | re.S)
    def clean(s):
        v = float(s.replace(",", "."))
        return round(v, 4) if lo <= v <= hi else None
    for m in block.finditer(html):
        pre = html[max(0, m.start() - 300):m.start()]
        best, pos = None, -1
        for b in BANKS:
            p = pre.rfind(b)
            if p > pos:
                pos, best = p, b
        if not best:
            continue
        buy, sell = clean(m.group(1)), clean(m.group(2))
        if buy is None and sell is None:
            continue
        rec = {}
        if buy is not None:
            rec["cumparare"] = buy
        if sell is not None:
            rec["vanzare"] = sell
        out[best] = rec
    return out

def load_prev():
    try:
        with open("rates.json", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def main():
    prev = load_prev()
    prev_banks = prev.get("banks", {})
    data = {
        "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "currencies": CURRENCIES,
    }
    try:
        date, bnr = bnr_all()
        data["data"] = date or prev.get("data")
        data["bnr"] = bnr or prev.get("bnr", {})
    except Exception as e:
        print(f"BNR esuat: {e}", file=sys.stderr)
        data["data"] = prev.get("data")
        data["bnr"] = prev.get("bnr", {})

    banks = {}
    for cur in CURRENCIES:
        found = banks_for(cur)
        for bank, rec in found.items():
            banks.setdefault(bank, {})[cur] = rec
    for bank, prevcur in prev_banks.items():
        for cur, rec in prevcur.items():
            if cur not in banks.get(bank, {}):
                banks.setdefault(bank, {})[cur] = rec
    data["banks"] = banks

    with open("rates.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("OK:", data["data"], "| BNR:", data.get("bnr"), "| banci:", len(banks))

if __name__ == "__main__":
    main()
