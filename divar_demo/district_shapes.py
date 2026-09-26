"""مرز محله‌ها برای نمایش روی نقشه پنل.

دیوار مرز محله نمی‌دهد (فیلدهای polygon در کاتالوگش همه خالی‌اند)، پس مرزها
از محله‌های شهرداری در OpenStreetMap می‌آیند (admin_level=11). تقسیم‌بندی
دیوار با شهرداری یکی نیست؛ برچسب هر مرز نام محله‌های دیواری است که مرکزشان
داخل آن است، تا همان نامی دیده شود که در جعبه محله تایپ می‌شود.

فقط برای نمایش است، نه فیلتر. اجرا (یک بار، یا وقتی OSM عوض شد):
    python -m divar_demo.district_shapes
داده‌ی OSM تحت ODbL است — © OpenStreetMap contributors.
"""

import json
import os

import requests

from . import geo

OVERPASS = "https://overpass-api.de/api/interpreter"
OUT = os.path.join(geo.DATA_DIR, "district_shapes_tehran.json")


def _rings(relation):
    """تکه‌های outer یک relation را به حلقه‌های بسته وصل می‌کند."""
    segs = [[(round(p["lon"], 5), round(p["lat"], 5)) for p in m["geometry"]]
            for m in relation["members"]
            if m["type"] == "way" and m.get("role") in ("outer", "") and m.get("geometry")]
    rings = []
    while segs:
        ring = segs.pop(0)
        joined = True
        while ring[0] != ring[-1] and joined:
            joined = False
            for i, s in enumerate(segs):
                if s[0] == ring[-1]:
                    ring += s[1:]
                elif s[-1] == ring[-1]:
                    ring += s[::-1][1:]
                elif s[-1] == ring[0]:
                    ring = s[:-1] + ring
                elif s[0] == ring[0]:
                    ring = s[::-1][:-1] + ring
                else:
                    continue
                segs.pop(i)
                joined = True
                break
        if len(ring) > 3:
            rings.append(ring)
    return rings


def _centroid(ring):
    return (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))


def _smallest_bbox_containing(districts, point):
    lon, lat = point
    boxes = [d for d in districts if d.get("bbox")
             and d["bbox"][0] <= lon <= d["bbox"][2] and d["bbox"][1] <= lat <= d["bbox"][3]]
    return min(boxes, key=lambda d: (d["bbox"][2] - d["bbox"][0]) * (d["bbox"][3] - d["bbox"][1]),
               default=None)


def build(city="tehran"):
    bbox = geo.city_bbox(city)
    query = f"""[out:json][timeout:180];
relation["boundary"="administrative"]["admin_level"="11"]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
out geom;"""
    resp = requests.post(OVERPASS, data={"data": query}, timeout=300,
                         headers={"User-Agent": "divar-scraper"})
    resp.raise_for_status()

    districts = [d for d in geo.load_districts(city) if d["lon"] is not None]
    features = []
    for rel in resp.json()["elements"]:
        rings = _rings(rel)
        if not rings:
            continue
        inside = [{"id": d["id"], "name": d["name"]} for d in districts
                  if any(geo.point_in_polygon(d["lon"], d["lat"], r) for r in rings)]
        if not inside:
            # مرکز هیچ محله‌ی دیوار داخل این مرز نیست (محله‌ی دیوار بزرگ‌تر است و
            # مرکزش در مرز همسایه افتاده). کوچک‌ترین bbox دیوار که مرکز این مرز را
            # دارد. ۲۰۲۶-۰۹-۲۶ با نام محله‌ای که دیوار روی آگهی‌های داخل این مرزها
            # گذاشته مقایسه شد؛ هر جا آگهی بود، درست درآمد.
            owner = _smallest_bbox_containing(districts, _centroid(rings[0]))
            if owner:
                inside = [{"id": owner["id"], "name": owner["name"]}]
        features.append({
            "type": "Feature",
            "properties": {
                # محله‌ای از شهرداری که هیچ محله دیواری در آن نیست، با نام OSM
                "name": "، ".join(d["name"].strip() for d in inside)
                        or rel["tags"].get("name", ""),
                # برای انتخاب با کلیک — شناسه همان است که فیلتر محله دیوار می‌خواهد
                "districts": inside,
            },
            "geometry": {"type": "MultiPolygon",
                         "coordinates": [[[list(p) for p in r]] for r in rings]},
        })

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"type": "FeatureCollection", "features": features}, fh,
                  ensure_ascii=False, separators=(",", ":"))
    return len(features)


if __name__ == "__main__":
    print(f"{build()} مرز محله → {OUT}")
