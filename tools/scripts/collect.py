"""Collect banana image metadata from Openverse (anonymous: 20/min, 200/day)."""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error

OUT = sys.argv[1]
UA = "BananaCollector/1.0 (https://github.com/aaron1612n-cmd/banana)"
QUERIES = [
    "banana", "bananas", "banana bunch", "banana tree", "banana plant",
    "plantain", "banana flower", "banana peel", "banana split", "banana bread",
    "ripe banana", "green bananas", "banana plantation", "banana leaf",
    "musa acuminata", "red banana", "banana market", "banana smoothie",
    "banana pancakes", "fried plantain", "banana blossom", "banana fruit",
    "banana illustration", "banana costume", "dried banana", "banana chips",
    "cavendish banana", "banana stand", "banana cake",
    "plantains", "banana pudding", "banana muffins", "banana harvest", "banana farm",
    "banana ice cream", "banana milkshake", "frozen banana", "chocolate banana",
    "banana sculpture", "banana art", "musa paradisiaca", "musa basjoo", "ensete",
    "banana heart", "banana inflorescence", "banana stem", "banana fritters",
    "pisang goreng", "maduros", "tostones", "bananas foster", "banana cream pie",
    "banana sundae", "banana still life", "banana duct tape", "banana bunch market",
    "overripe banana", "banana ripening", "banana boxes", "banana shipment",
    "banana trees", "wild banana", "banana seeds", "banana cross section",
    "sliced banana", "banana cereal", "banana toast", "banana dessert",
    "banana drawing", "banana painting", "banana toy", "banana slice",
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
        try:
            res, left = get(url)
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
        time.sleep(3.2)
        if left <= 2:
            print("daily quota nearly spent; stopping"); sys.exit(0)
        if page >= res.get("page_count", 0):
            break
