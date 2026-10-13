"""Crawl Wikimedia Commons banana categories into a manifest compatible with download.py."""
import html, json, os, re, sys, time, urllib.parse, urllib.request, urllib.error

OUT = sys.argv[1]
UA = "BananaCollector/1.0 (https://github.com/aaron1612n-cmd/banana)"
API = "https://commons.wikimedia.org/w/api.php"
ROOTS = ["Category:Bananas", "Category:Musa", "Category:Plantains", "Category:Banana plants",
         "Category:Banana flowers", "Category:Banana leaves", "Category:Banana dishes"]
MAX_DEPTH = 3
SKIP = re.compile(r"(?i)(maps?\b|logos?\b|stamps|coats? of arms|flags|people|portraits|nude|songs?|music|albums?|films?|velvet underground|bananarama|banana republic|bananas in pyjamas)")
data = json.load(open(OUT)) if os.path.exists(OUT) else {"items": {}, "seen_cats": []}
seen = set(data["seen_cats"])

def api(params):
    params |= {"format": "json", "formatversion": 2, "maxlag": 5}
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(30):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                time.sleep(min(5 * 2 ** attempt, 300)); continue
            raise
    raise RuntimeError("gave up on " + url)

def strip(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()

def save():
    data["seen_cats"] = sorted(seen); json.dump(data, open(OUT, "w"))

queue = [tuple(x) for x in data.get("queue", [])] or [(r, 0) for r in ROOTS]
while queue:
    cat, depth = queue[0]
    if cat in seen:
        queue.pop(0); continue
    cont = {}
    while True:
        res = api({"action": "query", "generator": "categorymembers", "gcmtitle": cat,
                   "gcmtype": "file|subcat", "gcmlimit": 50, "prop": "imageinfo",
                   "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1280,
                   "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist|ImageDescription"} | cont)
        for p in res.get("query", {}).get("pages", []):
            t = p["title"]
            if p["ns"] == 14:
                if depth + 1 <= MAX_DEPTH and not SKIP.search(t):
                    queue.append((t, depth + 1))
                continue
            ii = (p.get("imageinfo") or [{}])[0]
            if ii.get("mime") not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
                continue
            md = ii.get("extmetadata", {})
            lic = md.get("LicenseShortName", {}).get("value", "")
            if not re.search(r"(?i)(cc|public domain|pd|gfdl|free)", lic):
                continue
            pid = f"commons-{p['pageid']}"
            if pid not in data["items"]:
                data["items"][pid] = {
                    "id": pid, "title": t.removeprefix("File:"), "url": ii.get("thumburl") or ii["url"],
                    "foreign_landing_url": ii.get("descriptionurl"), "creator": strip(md.get("Artist", {}).get("value"))[:200],
                    "creator_url": None, "license": lic, "license_version": "", "license_url": md.get("LicenseUrl", {}).get("value", ""),
                    "provider": "wikimedia", "source": "wikimedia", "width": ii.get("width"), "height": ii.get("height"),
                    "attribution": None, "query": cat}
        if "continue" not in res:
            break
        cont = res["continue"]
        time.sleep(1)
    seen.add(cat); queue.pop(0); data["queue"] = queue; save()
    print(f"{cat} (d{depth}): total {len(data['items'])}, queue {len(queue)}", flush=True)
save()
print("done", len(data["items"]))
