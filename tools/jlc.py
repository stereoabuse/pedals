"""Query JLCPCB assembly parts stock. Usage: jlc.py TERM [TERM...]"""
import json, subprocess, sys

URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"

def search(term, n=8):
    body = json.dumps({"keyword": term, "currentPage": 1, "pageSize": 40,
                       "searchSource": "search", "componentAttributes": []})
    out = subprocess.run(["curl", "-s", "-m", "40", "-X", "POST", URL,
                          "-H", "Content-Type: application/json",
                          "-H", "User-Agent: Mozilla/5.0", "-d", body],
                         capture_output=True, text=True).stdout
    comps = json.loads(out)["data"]["componentPageInfo"]["list"] or []
    comps.sort(key=lambda c: (c["componentLibraryType"] != "base",
                              not c.get("preferredComponentFlag"), -(c["stockCount"] or 0)))
    return comps[:n]

def get(code):
    for c in search(code, 40):
        if c["componentCode"] == code:
            return c
    return None

if __name__ == "__main__":
    for t in sys.argv[1:]:
        print(f"== {t}")
        try:
            for c in search(t):
                flag = "B" if c["componentLibraryType"] == "base" else ("P" if c.get("preferredComponentFlag") else "-")
                print(f"  {c['componentCode']:<10} {flag} {c['stockCount']:>8} {c['componentModelEn'][:26]:<26} "
                      f"{(c.get('componentSpecificationEn') or '')[:16]:<16} ${c.get('initialPrice')}  {(c.get('describe') or '')[:60]}")
        except Exception as e:
            print("  ERR", e)
