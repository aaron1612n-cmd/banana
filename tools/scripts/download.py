"""Download images from merged manifests into <repo>/images/<source>/, verify them, write CREDITS.csv.

usage: download.py STATE.json REPO MANIFEST [MANIFEST ...]
"""
import csv, io, json, os, re, sys, threading, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

STATEFILE, REPO, MANIFESTS = sys.argv[1], sys.argv[2], sys.argv[3:]
UA = "BananaCollector/1.0 (https://github.com/aaron1612n-cmd/banana)"
MAX_BYTES = 15 * 1024 * 1024
EXT = {"JPEG": "jpg", "PNG": "png", "GIF": "gif", "WEBP": "webp"}
items = {}
for m in MANIFESTS:
    items.update(json.load(open(m))["items"])
state = json.load(open(STATEFILE)) if os.path.exists(STATEFILE) else {}
lock = threading.Lock()
RESIZE = int(os.environ.get("RESIZE", "0"))

def wm_thumb(url, width):
    """Wikimedia only serves standard thumbnail widths without throttling; 960px works."""
    m = re.match(r"https://upload\.wikimedia\.org/wikipedia/commons/(?:thumb/)?([0-9a-f]/[0-9a-f]{2})/([^/]+)", url)
    if not m or (width and width <= 960) or m.group(2).lower().endswith(".gif"):
        return url
    return f"https://upload.wikimedia.org/wikipedia/commons/thumb/{m.group(1)}/{m.group(2)}/960px-{m.group(2)}"

def pending(it):
    prev = state.get(it["id"])
    return not prev or ("path" not in prev and "429" in prev.get("error", ""))

def fetch(it, retries):
    url = wm_thumb(it["url"], it.get("width")) if "wikimedia.org" in it["url"] else it["url"]
    err = ""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                return {"error": "too large"}
            Image.open(io.BytesIO(body)).verify()
            im = Image.open(io.BytesIO(body))
            if im.format not in EXT:
                return {"error": f"format {im.format}"}
            if min(im.size) < 100:
                return {"error": "too small"}
            ext = EXT[im.format]
            if RESIZE and im.format in ("JPEG", "PNG", "WEBP") and (max(im.size) > RESIZE or len(body) > 200_000):
                im = im.convert("RGB"); im.thumbnail((RESIZE, RESIZE))
                buf = io.BytesIO(); im.save(buf, "JPEG", quality=82, optimize=True); body, ext = buf.getvalue(), "jpg"
            rel = f"images/{it['source'] or 'other'}/{it['id']}.{ext}"
            os.makedirs(os.path.dirname(os.path.join(REPO, rel)), exist_ok=True)
            open(os.path.join(REPO, rel), "wb").write(body)
            return {"path": rel, "width": im.size[0], "height": im.size[1]}
        except Exception as e:
            err = str(e)[:200]
            if any(c in err for c in ("404", "403", "410", "cannot identify")):
                break
            if "429" in err:
                time.sleep(20)
            else:
                time.sleep(2 * (attempt + 1))
    return {"error": err}

done = [0]
def record(it, res):
    with lock:
        state[it["id"]] = res
        done[0] += 1
        if done[0] % 200 == 0:
            json.dump(state, open(STATEFILE, "w"))
            print(done[0], "processed", flush=True)

def wikimedia_worker(todo):
    for it in todo:
        record(it, fetch(it, 2))
        time.sleep(1)

todo = [it for it in items.values() if pending(it)]
wm = [it for it in todo if "wikimedia.org" in it["url"]]
rest = [it for it in todo if "wikimedia.org" not in it["url"]]
if os.environ.get("ONLY") == "wikimedia": rest = []
elif os.environ.get("ONLY") == "other": wm = []
print(f"{len(todo)} pending ({len(wm)} wikimedia)", flush=True)
t = threading.Thread(target=wikimedia_worker, args=(wm,)); t.start()
with ThreadPoolExecutor(8) as ex:
    for it, res in zip(rest, ex.map(lambda it: fetch(it, 3), rest)):
        record(it, res)
t.join()
json.dump(state, open(STATEFILE, "w"))

ok = sorted(((items[k], v) for k, v in state.items() if "path" in v and k in items), key=lambda x: x[1]["path"])
with open(os.path.join(REPO, "CREDITS.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["file", "title", "creator", "license", "license_version", "license_url", "source", "source_page"])
    for it, v in ok:
        w.writerow([v["path"], it["title"], it["creator"], it["license"], it["license_version"],
                    it["license_url"], it["source"], it["foreign_landing_url"]])
print("downloaded", len(ok), "of", len(items), "| errors", sum("error" in v for v in state.values()), flush=True)
