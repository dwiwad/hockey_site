"""geo.py - map projection, flight arcs and a real basemap, with no map library.

The anaconda env has no cartopy, geopandas, basemap, shapely or pyproj. None of
them turned out to be necessary: what makes a map look real is the resolution
and the layering of the reference data, not the library that draws it. This
pulls Natural Earth's 50m land, state/province borders and lakes - the Great
Lakes matter a lot on a map of the NHL - and draws them with plain matplotlib.

  albers()       lon/lat -> planar x/y, the standard North America projection
  flight_arc()   a great circle, bowed for legibility, the way route maps draw
  load_layers()  Natural Earth land / borders / lakes, fetched once and cached
  basemap()      draw the layers and set the axes up
"""
import json
from pathlib import Path

import numpy as np
import requests

try:
    HERE = Path(__file__).resolve().parent
except NameError:                       # Spyder cell execution
    HERE = Path("/Users/dwiwad/dev/hockey_site/travel_inequality")

DATA = HERE / "data"
NE_BASE = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector"
           "/master/geojson/")

# Albers Equal Area Conic, the parameters every North America atlas uses.
LAT_1, LAT_2 = 29.5, 45.5               # standard parallels
LON_0, LAT_0 = -96.0, 37.5              # central meridian, origin

# Bounding box for the continent. Without it the United States feature drags in
# Hawaii and Guam, and Canada's Aleutian-side islands wrap past the
# antimeridian, either of which blows out the extent and shrinks the map.
BBOX = (-172.0, -52.0, 14.0, 72.0)      # lon_min, lon_max, lat_min, lat_max
COUNTRIES = {"Canada", "United States of America", "Mexico"}

# resolution -> (land file, borders file, lakes file). 110m is the crude one
# and is kept only for small multiples, where the detail would be mud anyway.
LAYERS = {
    "110m": ("ne_110m_admin_0_countries", None, None),
    "50m": ("ne_50m_admin_0_countries",
            "ne_50m_admin_1_states_provinces_lakes", "ne_50m_lakes"),
}
_CACHE = {}


def albers(lon, lat):
    """Project decimal degrees to planar x, y. Accepts scalars or arrays."""
    lon = np.radians(np.asarray(lon, dtype=float))
    lat = np.radians(np.asarray(lat, dtype=float))
    p1, p2, p0, l0 = map(np.radians, (LAT_1, LAT_2, LAT_0, LON_0))
    n = (np.sin(p1) + np.sin(p2)) / 2
    C = np.cos(p1) ** 2 + 2 * n * np.sin(p1)
    rho = np.sqrt(C - 2 * n * np.sin(lat)) / n
    rho0 = np.sqrt(C - 2 * n * np.sin(p0)) / n
    theta = n * (lon - l0)
    return rho * np.sin(theta), rho0 - rho * np.cos(theta)


def great_circle(lon1, lat1, lon2, lat2, n=96):
    """Interpolate the true great circle between two points (lon, lat arrays).

    Spherical linear interpolation on the unit vectors. Falls back to the
    endpoints when the two points coincide, which happens on the zero-distance
    legs - consecutive home games, and the Rangers visiting New Jersey.
    """
    a, b = np.radians([lon1, lat1]), np.radians([lon2, lat2])
    v1 = np.array([np.cos(a[1]) * np.cos(a[0]), np.cos(a[1]) * np.sin(a[0]), np.sin(a[1])])
    v2 = np.array([np.cos(b[1]) * np.cos(b[0]), np.cos(b[1]) * np.sin(b[0]), np.sin(b[1])])
    omega = np.arccos(np.clip(v1 @ v2, -1, 1))
    if omega < 1e-9:
        return np.array([lon1, lon2]), np.array([lat1, lat2])
    t = np.linspace(0, 1, n)[:, None]
    v = (np.sin((1 - t) * omega) * v1 + np.sin(t * omega) * v2) / np.sin(omega)
    return (np.degrees(np.arctan2(v[:, 1], v[:, 0])),
            np.degrees(np.arcsin(np.clip(v[:, 2], -1, 1))))


def flight_arc(lon1, lat1, lon2, lat2, amp=3.0, bow=0.055, n=96):
    """Projected x, y for one leg, curved the way a route map draws it.

    A great circle really does bow north of the straight chord, but Albers is
    built to flatten exactly that, so over the continental United States the
    true curve renders as a nearly straight line. This keeps the real shape and
    exaggerates it: the great circle's own perpendicular deviation from the
    chord is multiplied by `amp`, and `bow` adds a small half-sine on top so
    that short hops curve visibly too.

    The curve is therefore stylistic, and deliberately so. Every distance in
    this project is the exact haversine great-circle distance and none of them
    come from this function - it only draws.
    """
    x, y = albers(*great_circle(lon1, lat1, lon2, lat2, n))
    x0, y0, x1, y1 = x[0], y[0], x[-1], y[-1]
    dx, dy = x1 - x0, y1 - y0
    chord = np.hypot(dx, dy)
    if chord < 1e-12:
        return x, y
    # unit normal to the chord, pointing to the northern side
    nx, ny = -dy / chord, dx / chord
    if ny < 0:
        nx, ny = -nx, -ny
    t = np.linspace(0, 1, n)
    base_x, base_y = x0 + dx * t, y0 + dy * t
    dev = (x - base_x) * nx + (y - base_y) * ny        # signed deviation
    off = amp * dev + bow * chord * np.sin(np.pi * t)
    return base_x + nx * off, base_y + ny * off


def _fetch(name):
    path = DATA / f"{name}.geojson"
    if not path.exists():
        r = requests.get(NE_BASE + f"{name}.geojson", timeout=120)
        r.raise_for_status()
        path.write_bytes(r.content)
        print(f"  cached {path.name} ({len(r.content)/1e6:.1f} MB)")
    return json.loads(path.read_text())


def _rings(doc, keep=None, key="NAME", outer_only=True):
    """Projected rings from a GeoJSON, filtered and clipped to North America."""
    out = []
    for feat in doc["features"]:
        if keep is not None and feat["properties"].get(key) not in keep:
            continue
        geom = feat.get("geometry") or {}
        if geom.get("type") == "MultiPolygon":
            polys = geom["coordinates"]
        elif geom.get("type") == "Polygon":
            polys = [geom["coordinates"]]
        elif geom.get("type") in ("LineString", "MultiLineString"):
            polys = [[geom["coordinates"]]] if geom["type"] == "LineString" \
                else [[c] for c in geom["coordinates"]]
        else:
            continue
        for poly in polys:
            for ring in (poly[:1] if outer_only else poly):
                a = np.asarray(ring, dtype=float)
                if a.ndim != 2 or len(a) < 3:
                    continue
                lon, lat = a[:, 0], a[:, 1]
                if (lon.min() < BBOX[0] or lon.max() > BBOX[1]
                        or lat.min() < BBOX[2] or lat.max() > BBOX[3]):
                    continue
                out.append(albers(lon, lat))
    return out


def load_layers(res="50m"):
    """{'land', 'borders', 'lakes'} of projected rings. Cached per resolution."""
    if res in _CACHE:
        return _CACHE[res]
    land_f, bord_f, lake_f = LAYERS[res]
    layers = {"land": _rings(_fetch(land_f), COUNTRIES, "NAME"),
              "borders": [], "lakes": []}
    assert layers["land"], "bounding box removed every land ring"
    if bord_f:
        layers["borders"] = _rings(_fetch(bord_f),
                                   {"Canada", "United States of America"}, "admin")
    if lake_f:
        # scalerank filters out ponds; the Great Lakes and the big Canadian
        # lakes are what actually read at this scale.
        doc = _fetch(lake_f)
        doc["features"] = [f for f in doc["features"]
                           if (f["properties"].get("scalerank") or 99) <= 2]
        layers["lakes"] = _rings(doc, None)
    _CACHE[res] = layers
    return layers


def basemap(ax, res="50m", land="#EFE9DE", edge="#BFB4A2", border="#D6CCBB",
            water="#DFE7EA", lw=0.7):
    """Draw land, internal borders and lakes, then set the axes up for a map.

    The land fill is a shade off the site's cream background rather than white,
    so it reads as land on a transparent PNG.
    """
    L = load_layers(res)
    for x, y in L["land"]:
        ax.fill(x, y, facecolor=land, edgecolor=edge, linewidth=lw, zorder=0)
    for x, y in L["borders"]:
        ax.plot(x, y, color=border, linewidth=lw * 0.55, zorder=1)
    for x, y in L["lakes"]:
        ax.fill(x, y, facecolor=water, edgecolor=edge, linewidth=lw * 0.5,
                zorder=2)
    ax.set_aspect("equal")
    ax.axis("off")
    return ax


def extent(lons, lats, pad=0.10):
    """(xmin, xmax, ymin, ymax) around some points, with a proportional pad."""
    x, y = albers(lons, lats)
    dx, dy = x.max() - x.min(), y.max() - y.min()
    return (x.min() - pad * dx, x.max() + pad * dx,
            y.min() - pad * dy, y.max() + pad * dy)
