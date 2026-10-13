"""Move downloaded images to images/<topic>/<readable-name>.<ext> (<=900 files per folder), rewrite CREDITS.csv.

usage: organize.py STATE.json REPO MANIFEST [MANIFEST ...]
"""
import collections, csv, json, os, re, sys, unicodedata

STATEFILE, REPO, MANIFESTS = sys.argv[1], sys.argv[2], sys.argv[3:]
PER_DIR = 900
CAMERA = re.compile(r"^(img|dsc|dscn|dscf|pict|p|imgp|photo|image|dsc|sam|cimg|gopr|mvi|pxl|file)?[-_ ]?\d+$", re.I)
items = {}
for m in MANIFESTS:
    items.update(json.load(open(m))["items"])
state = json.load(open(STATEFILE))

def slug(s, maxlen=60):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:maxlen].rstrip("-")

def name_for(it, topic):
    title = re.sub(r"\.(jpe?g|png|gif|webp|tiff?|svg)$", "", (it.get("title") or "").strip(), flags=re.I)
    title = title.replace("_", " ")
    if not title or CAMERA.match(title.replace(" ", "")) or not re.search(r"[a-z]{3}", slug(title)):
        return topic
    return slug(title)

done = sorted((k for k, v in state.items() if "path" in v and k in items),
              key=lambda k: (slug(items[k]["query"].removeprefix("Category:")), k))
counts, used, moves = collections.Counter(), set(), []
fixed = [k for k in done if os.path.splitext(os.path.basename(state[k]["path"]))[0] != k]
for k in fixed:  # already organized in an earlier run: keep the name
    used.add(state[k]["path"]); counts[slug(items[k]["query"].removeprefix("Category:")) or "misc"] += 1
fixed_set = set(fixed)
for k in done:
    if k in fixed_set:
        continue
    topic = slug(items[k]["query"].removeprefix("Category:")) or "misc"
    n = counts[topic]; counts[topic] += 1
    folder = topic if n < PER_DIR else f"{topic}-{n // PER_DIR + 1}"
    base, ext = name_for(items[k], topic), os.path.splitext(state[k]["path"])[1]
    i, cand = 1, f"images/{folder}/{base}{ext}"
    while cand in used or (base == topic and i == 1):
        i += 1; cand = f"images/{folder}/{base}-{i}{ext}"
    used.add(cand)
    moves.append((k, cand))

# two-phase move so new names never collide with not-yet-moved old files
tmp = os.path.join(REPO, ".organize-tmp"); os.makedirs(tmp, exist_ok=True)
moves_new = moves
moves = [(k, state[k]["path"]) for k in fixed] + moves_new
for k, _ in moves_new:
    os.replace(os.path.join(REPO, state[k]["path"]), os.path.join(tmp, k))
for k, new in moves_new:
    os.makedirs(os.path.dirname(os.path.join(REPO, new)), exist_ok=True)
    os.replace(os.path.join(tmp, k), os.path.join(REPO, new))
    state[k]["path"] = new
os.rmdir(tmp)
for root, dirs, files in os.walk(os.path.join(REPO, "images"), topdown=False):
    if not os.listdir(root):
        os.rmdir(root)
json.dump(state, open(STATEFILE, "w"))

with open(os.path.join(REPO, "CREDITS.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["file", "title", "creator", "license", "license_version", "license_url", "source", "source_page"])
    for k, path in sorted(moves, key=lambda m: m[1]):
        it = items[k]
        w.writerow([path, it["title"], it["creator"], it["license"], it["license_version"],
                    it["license_url"], it["source"], it["foreign_landing_url"]])
sizes = collections.Counter(os.path.dirname(p) for _, p in moves)
print(len(moves), "images in", len(sizes), "folders; largest", max(sizes.values()))
