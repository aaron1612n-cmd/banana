"""Collect research-grade iNaturalist banana (genus Musa) observations with CC-licensed photos."""
import json, os, sys, time, urllib.parse, urllib.request

OUT = sys.argv[1]
UA = "BananaCollector/1.0 (https://github.com/aaron1612n-cmd/banana)"
LIC = {"cc0": ("cc0", "1.0", "https://creativecommons.org/publicdomain/zero/1.0/")}
for code in ("by", "by-sa", "by-nc", "by-nc-sa", "by-nd", "by-nc-nd"):
    LIC["cc-" + code] = (code, "4.0", f"https://creativecommons.org/licenses/{code}/4.0/")
data = json.load(open(OUT)) if os.path.exists(OUT) else {"items": {}, "id_above": 0}

while True:
    q = urllib.parse.urlencode({"taxon_id": 62911, "photos": "true", "quality_grade": "research",
        "photo_license": ",".join(LIC), "per_page": 200, "order_by": "id", "order": "asc", "id_above": data["id_above"]})
    for attempt in range(6):
        try:
            req = urllib.request.Request("https://api.inaturalist.org/v1/observations?" + q, headers={"User-Agent": UA})
            res = json.load(urllib.request.urlopen(req, timeout=60)); break
        except Exception as e:
            print("retry", e, flush=True); time.sleep(10 * 2 ** attempt)
    else:
        sys.exit("gave up")
    obs = res["results"]
    if not obs:
        break
    for o in obs:
        photo = next((p for p in o["photos"] if p.get("license_code") in LIC), None)
        if not photo:
            continue
        t = o.get("taxon") or {}
        name = t.get("name") or "Musa"
        common = t.get("preferred_common_name")
        place = (o.get("place_guess") or "").split(",")
        place = ", ".join(s.strip() for s in place[-2:] if s.strip())
        lic = LIC[photo["license_code"]]
        user = (o.get("user") or {}).get("login") or ""
        data["items"][f"inat-{o['id']}"] = {
            "id": f"inat-{o['id']}", "title": f"{common or name} {place}".strip() if common else f"{name} {place}".strip(),
            "url": photo["url"].replace("/square.", "/large."),
            "foreign_landing_url": f"https://www.inaturalist.org/observations/{o['id']}",
            "creator": user, "creator_url": f"https://www.inaturalist.org/people/{user}",
            "license": lic[0], "license_version": lic[1], "license_url": lic[2],
            "provider": "inaturalist", "source": "inaturalist", "width": None, "height": None,
            "attribution": photo.get("attribution"), "query": name}
    data["id_above"] = obs[-1]["id"]
    json.dump(data, open(OUT, "w"))
    print(len(data["items"]), "items; id_above", data["id_above"], flush=True)
    time.sleep(1.5)
print("done", len(data["items"]))
