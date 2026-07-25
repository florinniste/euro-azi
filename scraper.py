#!/usr/bin/env python3
"""Preia cursul EUR si scrie rates.json. BNR din feedul oficial (sigur);
UniCredit/BCR best-effort dintr-o sursa publica. Nu suprascrie o valoare buna cu una goala."""
import json, re, sys, datetime, urllib.request, xml.etree.ElementTree as ET

UA = "Mozilla/5.0 (curs-eur GitHub Action; +https://github.com)"
BUY_MIN, BUY_MAX = 4.4, 6.2

def get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def bnr_eur():
    xml = get("https://www.bnr.ro/nbrfxrates.xml")
    root = ET.fromstring(xml)
    ns = {"n": "http://www.bnr.ro/xsd"}
    cube = root.find(".//n:Cube", ns)
    date = cube.attrib.get("date") if cube is not None else None
    eur = None
    for rate in root.findall(".//n:Rate", ns):
        if rate.attrib.get("currency") == "EUR":
            mult = float(rate.attrib.get("multiplier", "1"))
            eur = round(float(rate.text) / mult, 4)
            break
    return date, eur

def plausible(x):
    try: return BUY_MIN <= float(x) <= BUY_MAX
    except Exception: return False

def bank_rates():
    out = {}
    sources = ["https://www.cursbnr.ro/curs-valutar-banci", "https://www.cursvalutarbanci.ro/"]
    targets = {"unicredit": ["unicredit"], "bcr": ["bcr", "banca comerciala"]}
    for url in sources:
        try: html = get(url)
        except Exception as e:
            print(f"  sursa {url} indisponibila: {e}", file=sys.stderr); continue
        low = html.lower(); num = re.compile(r"([4-6][.,]\d{3,4})")
        for bank, keys in targets.items():
            if bank in out: continue
            idx = -1
            for k in keys:
                idx = low.find(k)
                if idx != -1: break
            if idx == -1: continue
            window = html[idx: idx + 400]
            nums = [float(n.replace(",", ".")) for n in num.findall(window) if plausible(n.replace(",", "."))]
            if len(nums) >= 2:
                buy, sell = nums[0], nums[1]
                if buy > sell: buy, sell = sell, buy
                out[bank] = {"cumparare": round(buy, 4), "vanzare": round(sell, 4)}
        if len(out) == len(targets): break
    return out

def load_prev():
    try:
        with open("rates.json", encoding="utf-8") as f: return json.load(f)
    except Exception: return {}

def main():
    prev = load_prev()
    data = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    try:
        date, eur = bnr_eur()
        data["data"] = date or prev.get("data")
        data["bnr_eur"] = eur if eur is not None else prev.get("bnr_eur")
    except Exception as e:
        print(f"BNR esuat: {e}", file=sys.stderr)
        data["data"] = prev.get("data"); data["bnr_eur"] = prev.get("bnr_eur")
    banks = {}
    try: banks = bank_rates()
    except Exception as e: print(f"Banci esuat: {e}", file=sys.stderr)
    for b in ("unicredit", "bcr"):
        if b in banks: data[b] = banks[b]
        elif b in prev: data[b] = prev[b]
    with open("rates.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(json.dumps(data, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
