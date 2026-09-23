#!/usr/bin/env python3
"""
Genera il tracciato stradale reale degli itinerari usando OSRM su dati OpenStreetMap.
Uso (dalla radice del repo):
  python3 build_routes.py                       # tutti i comuni
  python3 build_routes.py "Comune di Niscemi"   # un solo comune
Per ogni itinerario calcola il percorso tra le tappe (in ordine) secondo travel_mode e
aggiorna in itineraries.json:
  - path:        polilinea che segue le strade reali
  - distance_km: distanza reale del percorso
  - legs:        distanza e tempo di percorrenza tra ogni tappa e la successiva
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

# Server pubblico FOSSGIS: max 1 richiesta/secondo, uso non intensivo (va bene per build offline).
OSRM_BASE = "https://routing.openstreetmap.de"
PROFILES = {
    "walking": "routed-foot/route/v1/foot",
    "bicycling": "routed-bike/route/v1/bike",
    "driving": "routed-car/route/v1/driving",
}
USER_AGENT = "Heritage-content-builder (Magnetico Associazione Culturale)"


def fetch_route(coords, mode):
    lonlat = ";".join(f"{lon},{lat}" for lat, lon in coords)
    url = f"{OSRM_BASE}/{PROFILES[mode]}/{lonlat}?overview=full&geometries=geojson&steps=false"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    except urllib.error.URLError:
        # Il Python di sistema macOS (LibreSSL 2.x) fallisce l'handshake TLS: ripiego su curl.
        if not shutil.which("curl"):
            raise
        out = subprocess.run(
            ["curl", "-sSf", "--max-time", "30", "-A", USER_AGENT, url],
            capture_output=True, text=True,
        )
        if out.returncode != 0:
            raise RuntimeError(out.stderr.strip())
        data = json.loads(out.stdout)
    if data.get("code") != "Ok":
        raise RuntimeError(data.get("message") or data.get("code"))
    return data["routes"][0]


def build_path(geometry):
    path = []
    for lon, lat in geometry["coordinates"]:
        point = {"lat": round(lat, 5), "lon": round(lon, 5)}
        if not path or path[-1] != point:
            path.append(point)
    return path


def dump(data):
    text = json.dumps(data, ensure_ascii=False, indent=2)
    # Un punto del tracciato per riga, per tenere il file leggibile.
    return re.sub(
        r'\{\s*"lat": (-?[\d.]+),\s*"lon": (-?[\d.]+)\s*\}',
        r'{ "lat": \1, "lon": \2 }',
        text,
    ) + "\n"


def process(folder):
    with open(os.path.join(folder, "monuments.json"), encoding="utf-8") as f:
        monuments = {m["id"]: m for m in json.load(f)}
    it_file = os.path.join(folder, "itineraries.json")
    with open(it_file, encoding="utf-8") as f:
        itineraries = json.load(f)

    changed = False
    for it in itineraries:
        iid = it.get("id")
        mode = it.get("travel_mode", "walking")
        if mode not in PROFILES:
            print(f"  [{iid}] travel_mode sconosciuto '{mode}', salto")
            continue

        stops = sorted(it.get("stops", []), key=lambda s: s.get("order", 0))
        ids = [s["monument_id"] for s in stops]
        coords = []
        for mid in ids:
            m = monuments.get(mid)
            if not m or m.get("lat") is None or m.get("lon") is None:
                coords = None
                print(f"  [{iid}] tappa senza coordinate: {mid}, salto")
                break
            coords.append((m["lat"], m["lon"]))
        if not coords or len(coords) < 2:
            continue

        try:
            route = fetch_route(coords, mode)
        except (urllib.error.URLError, RuntimeError, TimeoutError) as e:
            print(f"  [{iid}] errore routing: {e}")
            continue
        finally:
            time.sleep(1)

        it["path"] = build_path(route["geometry"])
        it["distance_km"] = round(route["distance"] / 1000, 2)
        it["legs"] = [
            {
                "from": ids[i],
                "to": ids[i + 1],
                "distance_km": round(leg["distance"] / 1000, 2),
                "travel_minutes": round(leg["duration"] / 60),
            }
            for i, leg in enumerate(route["legs"])
        ]
        changed = True
        print(f"  [{iid}] {it['distance_km']} km, {len(it['path'])} punti ({mode})")
        for leg in it["legs"]:
            if leg["distance_km"] == 0:
                print(f"    ATTENZIONE: tappe {leg['from']} e {leg['to']} hanno le stesse coordinate")

    if changed:
        with open(it_file, "w", encoding="utf-8") as f:
            f.write(dump(itineraries))


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    folders = sys.argv[1:] or sorted(glob.glob(os.path.join(root, "Comune di *")))
    for folder in folders:
        print(os.path.basename(os.path.normpath(folder)))
        process(folder)


if __name__ == "__main__":
    main()
