#!/usr/bin/env python3
"""Turn munich-open-data.zip into a FLAT folder of analysis-ready CSVs.

`exakit data-load <folder>` reads a folder at its TOP LEVEL only and makes one
table per file, named after the file. The portal download is nested (one
sub-folder per dataset), uses German column names, mixed date formats, UTM
coordinates (EPSG:25832) in some files and WGS84 lat/lon in others. This script
fixes all of that once, so every agent can join the tables with plain SQL.

    python3 prepare_dataset.py ~/Downloads/munich-open-data.zip --out ~/munich-dataset
    EXAKIT_SCHEMA=MUNICH_DATASET exakit data-load ~/munich-open-data

Pure standard library. No pandas, no pyproj.

Output files (-> table names after load, schema MUNICH_DATASET):
  bike_counts_daily.csv        BIKE_COUNTS_DAILY       one row per station per day, with weather
  bike_counts_15min.csv        BIKE_COUNTS_15MIN       15-minute counts
  bike_count_stations.csv      BIKE_COUNT_STATIONS     the 6 permanent counters, lat/lon, district
  districts.csv                DISTRICTS               25 districts: population, area, density, centroid, polygon (WGS84 WKT)
  roadworks.csv                ROADWORKS               current/planned roadworks, dates, centroid, district
  cycling_infrastructure.csv   CYCLING_INFRASTRUCTURE  cycle-path segments, type, length, lat/lon, district
  mvv_agency.csv               MVV_AGENCY              GTFS
  mvv_routes.csv               MVV_ROUTES              GTFS, with route_mode decoded from route_type
  mvv_trips.csv                MVV_TRIPS               GTFS
  mvv_stops.csv                MVV_STOPS               GTFS, with district_no for stops inside Munich
  mvv_stop_times.csv           MVV_STOP_TIMES          GTFS (large: ~250 MB)
  mvv_calendar.csv             MVV_CALENDAR            GTFS
  mvv_calendar_dates.csv       MVV_CALENDAR_DATES      GTFS
  mvg_bike_trips.csv           MVG_BIKE_TRIPS          optional, --with-mvg-bikes 2024 2025
"""
from __future__ import annotations

import argparse
import csv
import io
import math
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# --------------------------------------------------------------------------- geo
A = 6378137.0
F = 1 / 298.257223563
K0 = 0.9996
E2 = F * (2 - F)
EP2 = E2 / (1 - E2)


def utm_to_latlon(easting: float, northing: float, zone: int = 32) -> tuple[float, float]:
    """EPSG:25832 (UTM 32N, ETRS89) -> WGS84 lat/lon. ETRS89 ~ WGS84 at metre level."""
    x = easting - 500000.0
    y = northing
    lon0 = math.radians((zone - 1) * 6 - 180 + 3)
    m = y / K0
    mu = m / (A * (1 - E2 / 4 - 3 * E2**2 / 64 - 5 * E2**3 / 256))
    e1 = (1 - math.sqrt(1 - E2)) / (1 + math.sqrt(1 - E2))
    phi1 = (mu + (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu)
            + (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu)
            + (151 * e1**3 / 96) * math.sin(6 * mu)
            + (1097 * e1**4 / 512) * math.sin(8 * mu))
    n1 = A / math.sqrt(1 - E2 * math.sin(phi1) ** 2)
    t1 = math.tan(phi1) ** 2
    c1 = EP2 * math.cos(phi1) ** 2
    r1 = A * (1 - E2) / (1 - E2 * math.sin(phi1) ** 2) ** 1.5
    d = x / (n1 * K0)
    lat = phi1 - (n1 * math.tan(phi1) / r1) * (
        d**2 / 2 - (5 + 3 * t1 + 10 * c1 - 4 * c1**2 - 9 * EP2) * d**4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1**2 - 252 * EP2 - 3 * c1**2) * d**6 / 720)
    lon = lon0 + (d - (1 + 2 * t1 + c1) * d**3 / 6
                  + (5 - 2 * c1 + 28 * t1 - 3 * c1**2 + 8 * EP2 + 24 * t1**2) * d**5 / 120) / math.cos(phi1)
    return round(math.degrees(lat), 6), round(math.degrees(lon), 6)


_RING = re.compile(r"\(([^()]+)\)")


def wkt_rings(wkt: str) -> list[list[tuple[float, float]]]:
    """Every coordinate ring in a POLYGON / MULTIPOLYGON WKT, as (x, y) lists."""
    rings = []
    for group in _RING.findall(wkt or ""):
        pts = []
        for pair in group.split(","):
            parts = pair.split()
            if len(parts) >= 2:
                pts.append((float(parts[0]), float(parts[1])))
        if len(pts) >= 3:
            rings.append(pts)
    return rings


def outer_rings(wkt: str) -> list[list[tuple[float, float]]]:
    """First ring of each polygon part (holes are ignored for this demo)."""
    out = []
    body = (wkt or "").strip()
    if body.upper().startswith("MULTIPOLYGON"):
        for part in re.findall(r"\(\((.*?)\)\)", body, flags=re.S):
            r = wkt_rings("((" + part + "))")
            if r:
                out.append(r[0])
    else:
        r = wkt_rings(body)
        if r:
            out.append(r[0])
    return out


def rings_to_wgs84(rings):
    return [[utm_to_latlon(x, y) for (x, y) in ring] for ring in rings]


def centroid(rings_ll):
    pts = [p for ring in rings_ll for p in ring]
    if not pts:
        return "", ""
    return (round(sum(p[0] for p in pts) / len(pts), 6),
            round(sum(p[1] for p in pts) / len(pts), 6))


def point_in_ring(lat, lon, ring):
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        yi, xi = ring[i]
        yj, xj = ring[j]
        if (yi > lat) != (yj > lat):
            x_cross = (xj - xi) * (lat - yi) / (yj - yi + 1e-18) + xi
            if lon < x_cross:
                inside = not inside
        j = i
    return inside


def polygon_wkt_wgs84(rings_ll):
    parts = []
    for ring in rings_ll:
        if ring[0] != ring[-1]:
            ring = ring + [ring[0]]
        parts.append("((" + ", ".join(f"{lon} {lat}" for lat, lon in ring) + "))")
    if len(parts) == 1:
        return "POLYGON" + parts[0]
    return "MULTIPOLYGON(" + ", ".join(parts) + ")"


class DistrictIndex:
    def __init__(self):
        self.items = []  # (district_no, rings_ll, bbox)

    def add(self, no, rings_ll):
        for ring in rings_ll:
            lats = [p[0] for p in ring]
            lons = [p[1] for p in ring]
            self.items.append((no, ring, (min(lats), max(lats), min(lons), max(lons))))

    def lookup(self, lat, lon):
        if lat == "" or lon == "":
            return ""
        for no, ring, (la0, la1, lo0, lo1) in self.items:
            if la0 <= lat <= la1 and lo0 <= lon <= lo1 and point_in_ring(lat, lon, ring):
                return no
        return ""


# --------------------------------------------------------------------------- helpers
def norm_date(s: str) -> str:
    """'2026.01.01' / '01.01.2026' / '2026-01-01' / with time -> 'YYYY-MM-DD'."""
    s = (s or "").strip()
    m = re.match(r"^(\d{4})[.\-/](\d{2})[.\-/](\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.match(r"^(\d{2})[.\-/](\d{2})[.\-/](\d{4})", s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return s


def norm_datetime(s: str) -> str:
    s = (s or "").strip()
    d = norm_date(s)
    m = re.search(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", s[8:] if len(s) > 8 else "")
    if m and len(d) == 10:
        return f"{d} {int(m.group(1)):02d}:{m.group(2)}:{m.group(3) or '00'}"
    return d


def num(s: str) -> str:
    s = (s or "").strip().replace(",", ".")
    return s


def clean_header(h: str) -> str:
    h = h.strip().lower()
    h = (h.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss"))
    h = re.sub(r"[^a-z0-9]+", "_", h).strip("_")
    return h


def read_csv(path: Path, delimiter=None, encoding="utf-8-sig"):
    raw = path.read_text(encoding=encoding, errors="replace")
    if delimiter is None:
        first = raw.split("\n", 1)[0]
        delimiter = ";" if first.count(";") > first.count(",") else ","
    rdr = csv.reader(io.StringIO(raw), delimiter=delimiter)
    header = [clean_header(h) for h in next(rdr)]
    for row in rdr:
        if not row or all(not c.strip() for c in row):
            continue
        yield dict(zip(header, [c.strip() for c in row]))


def write_csv(path: Path, header: list[str], rows):
    n = 0
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for r in rows:
            w.writerow([r.get(h, "") for h in header])
            n += 1
    print(f"  wrote {path.name:<30} {n:>9,} rows")
    return n


def find_dir(root: Path, startswith: str) -> Path | None:
    for p in sorted((root / "datasets").iterdir()):
        if p.is_dir() and p.name.startswith(startswith):
            return p
    return None


STATIONS = [
    # name, long name, lat, lon, direction_1, direction_2  (Munich geoportal, mor_wfs:raddauerzaehlstellen)
    ("Arnulf", "Arnulfstr. 9 - 11 Suedseite", 48.14205, 11.55534, "Ost", "West"),
    ("Kreuther", "Bad-Kreuther-Str.", 48.12194, 11.62417, "West", "Ost"),
    ("Olympia", "Rudolf-Harbig-Weg (Olympiapark)", 48.16887, 11.55005, "Nord", "Sued"),
    ("Hirsch", "Birketweg HLP (Hirschgarten)", 48.14438, 11.51794, "West", "Ost"),
    ("Margareten", "Margaretenstr. (Harras)", 48.12032, 11.53599, "West", "Ost"),
    ("Erhardt", "Erhardtstr. (Deutsches Museum)", 48.13192, 11.58469, "Sued", "Nord"),
]

ROUTE_MODES = {"0": "Tram", "1": "U-Bahn", "2": "Rail", "3": "Bus", "4": "Ferry", "5": "Cable tram",
               "6": "Aerial lift", "7": "Funicular", "11": "Trolleybus", "12": "Monorail",
               "100": "Rail", "109": "S-Bahn", "400": "U-Bahn", "700": "Bus", "900": "Tram"}


# --------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("source", help="munich-open-data.zip or the extracted munich-open-data folder")
    ap.add_argument("--out", default=str(Path.home() / "munich-dataset"), help="flat output folder")
    ap.add_argument("--with-mvg-bikes", nargs="*", metavar="YEAR",
                    help="also build mvg_bike_trips.csv from these years (e.g. 2024 2025); large")
    ap.add_argument("--skip-stop-times", action="store_true", help="leave out the 250 MB GTFS stop_times file")
    args = ap.parse_args()

    src = Path(args.source).expanduser()
    out = Path(args.out).expanduser()
    tmp = None
    if src.is_file() and src.suffix == ".zip":
        tmp = Path(tempfile.mkdtemp(prefix="munich-"))
        print(f"Extracting {src.name} ...")
        with zipfile.ZipFile(src) as z:
            for m in z.namelist():
                if m.startswith("__MACOSX") or m.endswith(".DS_Store"):
                    continue
                z.extract(m, tmp)
        root = tmp / "munich-open-data"
    else:
        root = src
    if not (root / "datasets").is_dir():
        print(f"error: {root} has no datasets/ folder", file=sys.stderr)
        return 1

    out.mkdir(parents=True, exist_ok=True)
    print(f"Writing flat dataset to {out}")

    # --- 5 + 4. districts --------------------------------------------------------
    idx = DistrictIndex()
    d_bounds = find_dir(root, "5.")
    d_pop = find_dir(root, "4.")
    pop = {}
    for r in read_csv(next(d_pop.glob("*.csv"))):
        no = str(int(r["stadtbezirksnummer"]))
        pop[no] = r
    # A district split into several polygon parts (18, 19) is several rows in the
    # source; merge them into ONE row per district so joins never double count.
    parts: dict[str, dict] = {}
    for r in read_csv(next(p for p in d_bounds.glob("*.csv"))):
        no = str(int(r["sb_nummer"]))
        rings = rings_to_wgs84(outer_rings(r["shape"]))
        idx.add(no, rings)
        entry = parts.setdefault(no, {"name": r["sb_name"], "rings": [], "area_sqm": 0.0})
        entry["rings"].extend(rings)
        try:
            entry["area_sqm"] += float(num(r.get("flaeche_qm", "0")) or 0)
        except ValueError:
            pass
    districts = []
    for no, entry in parts.items():
        clat, clon = centroid(entry["rings"])
        p = pop.get(no, {})
        districts.append({
            "district_no": no, "district_name": entry["name"],
            "population": p.get("bevoelkerung", ""), "population_pct": num(p.get("bevoelkerung_in_prozent", "")),
            "area_ha": num(p.get("flaeche_in_ha", "")), "area_pct": num(p.get("flaeche_in_prozent", "")),
            "density_per_ha": p.get("einwohnerdichte", ""), "area_sqm": round(entry["area_sqm"], 2),
            "centroid_lat": clat, "centroid_lon": clon, "polygon_wkt": polygon_wkt_wgs84(entry["rings"]),
        })
    districts.sort(key=lambda d: int(d["district_no"]))
    write_csv(out / "districts.csv",
              ["district_no", "district_name", "population", "population_pct", "area_ha", "area_pct",
               "density_per_ha", "area_sqm", "centroid_lat", "centroid_lon", "polygon_wkt"], districts)

    # --- 1. bike counts -------------------------------------------------------------
    d_bike = find_dir(root, "1.")
    daily, q15 = [], []
    for f in sorted(d_bike.glob("*_tage.csv")):
        for r in read_csv(f):
            daily.append({
                "count_date": norm_date(r["datum"]), "station": r["zaehlstelle"],
                "dir_1": r["richtung_1"], "dir_2": r["richtung_2"], "total": r["gesamt"],
                "temp_min_c": num(r.get("min_temp", "")), "temp_max_c": num(r.get("max_temp", "")),
                "rain_mm": num(r.get("niederschlag", "")), "cloud_cover_pct": num(r.get("bewoelkung", "")),
                "sunshine_hours": num(r.get("sonnenstunden", "")),
            })
    for f in sorted(d_bike.glob("*_15min.csv")):
        for r in read_csv(f):
            q15.append({
                "count_date": norm_date(r["datum"]), "time_start": r["uhrzeit_start"], "time_end": r["uhrzeit_ende"],
                "station": r["zaehlstelle"], "dir_1": r["richtung_1"], "dir_2": r["richtung_2"], "total": r["gesamt"],
            })
    write_csv(out / "bike_counts_daily.csv",
              ["count_date", "station", "dir_1", "dir_2", "total", "temp_min_c", "temp_max_c", "rain_mm",
               "cloud_cover_pct", "sunshine_hours"], daily)
    write_csv(out / "bike_counts_15min.csv",
              ["count_date", "time_start", "time_end", "station", "dir_1", "dir_2", "total"], q15)
    write_csv(out / "bike_count_stations.csv",
              ["station", "station_name", "lat", "lon", "direction_1", "direction_2", "district_no"],
              [{"station": s[0], "station_name": s[1], "lat": s[2], "lon": s[3], "direction_1": s[4],
                "direction_2": s[5], "district_no": idx.lookup(s[2], s[3])} for s in STATIONS])

    # --- 3. roadworks -----------------------------------------------------------------
    d_road = find_dir(root, "3.")
    roads = []
    for r in read_csv(next(d_road.glob("*.csv"))):
        rings = rings_to_wgs84(outer_rings(r.get("shape", "")))
        clat, clon = centroid(rings)
        roads.append({
            "roadwork_id": r.get("fid", ""), "street": r.get("strasse_hausnr", ""),
            "affected_areas": r.get("betroffene_bereiche", ""), "description": r.get("beschreibung", ""),
            "impact": r.get("beeintraechtigung", ""), "kind": r.get("art", ""),
            "more_info": r.get("weitere_info", ""), "contact": r.get("kontakt_oeffentlich", ""),
            "start_date": norm_date(r.get("beginn_datum_kombiniert", "")),
            "end_date": norm_date(r.get("ende_datum_kombiniert", "")),
            "start_raw": r.get("beginn_datum_kombiniert", ""), "end_raw": r.get("ende_datum_kombiniert", ""),
            "source_id": r.get("fachliche_id", ""), "centroid_lat": clat, "centroid_lon": clon,
            "district_no": idx.lookup(clat, clon) if clat != "" else "",
            "shape_wkt": polygon_wkt_wgs84(rings) if rings else "",
        })
    write_csv(out / "roadworks.csv",
              ["roadwork_id", "street", "affected_areas", "description", "impact", "kind", "more_info", "contact",
               "start_date", "end_date", "start_raw", "end_raw", "source_id", "centroid_lat", "centroid_lon",
               "district_no", "shape_wkt"], roads)

    # --- 6. cycling infrastructure ------------------------------------------------
    d_cyc = find_dir(root, "6.")
    cyc = []
    for r in read_csv(next(d_cyc.glob("*.csv"))):
        try:
            slat, slon = utm_to_latlon(float(r["start_x"]), float(r["start_y"]))
            elat, elon = utm_to_latlon(float(r["end_x"]), float(r["end_y"]))
        except (ValueError, KeyError):
            continue
        mlat, mlon = round((slat + elat) / 2, 6), round((slon + elon) / 2, 6)
        cyc.append({
            "segment_id": r.get("fid", ""), "street": r.get("strassenna", ""),
            "length_m": num(r.get("shape_leng", "")), "path_type": r.get("d_radwegar", ""),
            "start_lat": slat, "start_lon": slon, "end_lat": elat, "end_lon": elon,
            "mid_lat": mlat, "mid_lon": mlon, "district_no": idx.lookup(mlat, mlon),
        })
    write_csv(out / "cycling_infrastructure.csv",
              ["segment_id", "street", "length_m", "path_type", "start_lat", "start_lon", "end_lat", "end_lon",
               "mid_lat", "mid_lon", "district_no"], cyc)

    # --- 2. MVV GTFS ------------------------------------------------------------------
    d_mvv = find_dir(root, "2.")
    simple = {"agency": "mvv_agency", "trips": "mvv_trips", "calendar": "mvv_calendar",
              "calendar_dates": "mvv_calendar_dates"}
    for name, target in simple.items():
        rows = list(read_csv(d_mvv / f"{name}.csv", delimiter=","))
        if name == "calendar":
            for r in rows:
                r["start_date"] = norm_date(re.sub(r"^(\d{4})(\d{2})(\d{2})$", r"\1-\2-\3", r["start_date"]))
                r["end_date"] = norm_date(re.sub(r"^(\d{4})(\d{2})(\d{2})$", r"\1-\2-\3", r["end_date"]))
        if name == "calendar_dates":
            for r in rows:
                r["date"] = re.sub(r"^(\d{4})(\d{2})(\d{2})$", r"\1-\2-\3", r["date"])
        header = list(rows[0].keys()) if rows else []
        write_csv(out / f"{target}.csv", header, rows)

    routes = list(read_csv(d_mvv / "routes.csv", delimiter=","))
    for r in routes:
        r["route_mode"] = ROUTE_MODES.get(r.get("route_type", ""), "Other")
    write_csv(out / "mvv_routes.csv", list(routes[0].keys()), routes)

    stops = []
    for r in read_csv(d_mvv / "stops.csv", delimiter=","):
        try:
            lat, lon = float(r["stop_lat"]), float(r["stop_lon"])
        except ValueError:
            lat, lon = "", ""
        r["district_no"] = idx.lookup(lat, lon) if lat != "" else ""
        r["in_munich"] = "1" if r["district_no"] else "0"
        stops.append(r)
    write_csv(out / "mvv_stops.csv", list(stops[0].keys()), stops)

    if not args.skip_stop_times:
        src_st = d_mvv / "stop_times.csv"
        print(f"  copying {src_st.name} ({src_st.stat().st_size / 1e6:.0f} MB) -> mvv_stop_times.csv")
        shutil.copyfile(src_st, out / "mvv_stop_times.csv")

    # --- 7. optional MVG bike trips ------------------------------------------------
    if args.with_mvg_bikes:
        d_mvg = find_dir(root, "7.")
        header = ["trip_no", "start_time", "end_time", "start_lat", "start_lon", "end_lat", "end_lon",
                  "rental_is_station", "rental_station_name", "return_is_station", "return_station_name", "year"]
        rows = []
        for year in args.with_mvg_bikes:
            f = d_mvg / f"MVG_Rad_Fahrten_{year}.csv"
            if not f.exists():
                print(f"  skip: {f.name} not in the archive")
                continue
            for r in read_csv(f, delimiter=";"):
                rows.append({
                    "trip_no": r.get("row", ""), "start_time": norm_datetime(r.get("starttime", "")),
                    "end_time": norm_datetime(r.get("endtime", "")),
                    "start_lat": num(r.get("startlat", "")), "start_lon": num(r.get("startlon", "")),
                    "end_lat": num(r.get("endlat", "")), "end_lon": num(r.get("endlon", "")),
                    "rental_is_station": r.get("rental_is_station", ""),
                    "rental_station_name": r.get("rental_station_name", ""),
                    "return_is_station": r.get("return_is_station", ""),
                    "return_station_name": r.get("return_station_name", ""), "year": year,
                })
        write_csv(out / "mvg_bike_trips.csv", header, rows)

    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\nDone. Load it with:\n"
          f"  EXAKIT_SCHEMA=MUNICH_DATASET exakit data-load {out}\n"
          "(answer the schema prompt with MUNICH_DATASET; set EXAKIT_ON_EXISTING=replace to re-run without questions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
