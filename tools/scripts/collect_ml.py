"""Collect banana image metadata from Openverse (anonymous: 20/min, 200/day)."""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error

OUT = sys.argv[1]
UA = "BananaCollector/1.0 (https://github.com/aaron1612n-cmd/banana)"
QUERIES = [
    "plátano", "platano", "banane", "bananen", "pisang", "guineo", "cambur", "banano",
    "banaan", "banan", "banaani", "μπανάνα", "банан", "バナナ", "香蕉", "바나나",
    "กล้วย", "chuối", "kela", "saging", "ndizi", "muz", "banany", "bananier",
    "platanera", "bananeira", "plátano macho", "banana verde", "banane plantain",
]

data = json.load(open(OUT)) if os.path.exists(OUT) else {"items": {}, "done": []}
done = set(data["done"])

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r), int(r.headers.get("x-ratelimit-available-anon_sustained", "999"))

for q in QUERIES:
    for page in range(1, 13):
        key = f"{q}|{page}"
        if key in done:
            continue
        url = "https://api.openverse.org/v1/images/?" + urllib.parse.urlencode(
            {"q": q, "page_size": 20, "page": page, "mature": "false"})
        for wait in (60, 300, 900, 1800, 3600, 3600, 3600, 3600, None):
            try:
                res, left = get(url); err = None; break
            except urllib.error.HTTPError as e:
                err = e
                if e.code != 429 or wait is None:
                    break
                print("rate limited; sleeping", wait, flush=True); time.sleep(wait)
        try:
            if err: raise err
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print("rate limited; stopping", flush=True); json.dump(data, open(OUT, "w")); sys.exit(0)
            print(q, page, "HTTP", e.code, flush=True); done.add(key); data["done"] = sorted(done); break
        new = 0
        for it in res.get("results", []):
            if it.get("mature") or it.get("unstable__sensitivity"):
                continue
            if it["id"] not in data["items"]:
                data["items"][it["id"]] = {k: it.get(k) for k in (
                    "id", "title", "url", "foreign_landing_url", "creator", "creator_url",
                    "license", "license_version", "license_url", "provider", "source",
                    "width", "height", "attribution")} | {"query": q}
                new += 1
        done.add(key); data["done"] = sorted(done)
        json.dump(data, open(OUT, "w"))
        print(f"{q!r} p{page}: +{new} (total {len(data['items'])}, quota left {left})", flush=True)
        time.sleep(4)
        if left <= 2:
            print("daily quota nearly spent; stopping"); sys.exit(0)
        if page >= res.get("page_count", 0):
            break
