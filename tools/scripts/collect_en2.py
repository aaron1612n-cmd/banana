"""Collect banana image metadata from Openverse (anonymous: 20/min, 200/day)."""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error

OUT = sys.argv[1]
UA = "BananaCollector/1.0 (https://github.com/aaron1612n-cmd/banana)"
QUERIES = [
    "banana leaf plate", "banana lassi", "banoffee pie", "banana nut bread", "banana oatmeal",
    "banana yogurt", "banana crepe", "banana waffle", "banana cookies", "banana jam",
    "banana ketchup", "banana flour", "banana fiber", "banana trunk", "banana bud",
    "banana sucker", "panama disease banana", "black sigatoka", "banana weevil",
    "half peeled banana", "bananas on table", "banana macro", "banana pile",
    "banana bunch hanging", "banana grove", "banana field", "banana workers",
    "bananas bicycle", "banana truck", "banana leaves wrapped", "banana flower salad",
    "banana hearts", "baby bananas", "lady finger banana", "blue java banana",
    "manzano banana", "saba banana", "banana fritter", "banana roti", "banana spring roll",
    "turon", "banana cue", "banana leaf rice", "bananas supermarket", "banana display",
    "banana pancake", "banana bread slice", "banana loaf", "banana ripe yellow", "banana bunches",
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
