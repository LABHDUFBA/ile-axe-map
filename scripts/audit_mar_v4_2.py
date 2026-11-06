#!/usr/bin/env python3
"""Auditoria de pontos na água (v4.2 candidata).

Detecta registros do GeoJSON nacional cuja coordenada cai no mar/na baía,
usando paridade de cruzamentos (ray casting) contra a linha de costa do OSM
(natural=coastline) na região de Salvador, e gera uma versão candidata com
geo_status='coordenada_agua' para esses registros.

Método:
  1. Baixa ways natural=coastline do Overpass para a região metropolitana
     de Salvador (bbox -13.6,-39.3,-12.3,-37.7 — cobre península, ilhas da
     baía e litoral NE até lon -37.7).
  2. Para cada ponto do dataset no bbox estendido, conta quantos segmentos
     de costa o raio horizontal para leste cruza. Par = mar, ímpar = terra.
  3. Validado contra pontos de controle conhecidos (Pelourinho, Itapuã,
     Gantois real = terra; alto-mar = mar; centro da baía = mar).
  4. Registros no mar a >=250 m da costa (banda de confiança) recebem
     geo_status='coordenada_agua' na candidata; geo_status_anterior preserva
     o valor original. Nada é apagado.

Saídas:
  data/v4_2/terreiros_nacional_v4_2.geojson   (candidata, sanitizada)
  data/v4_2/auditoria_v4_2.json               (contagens e lista de flags)
  data/v4_2/pontos_na_agua.csv                (lista pública de flags)

Uso: python3 scripts/audit_mar_v4_2.py [--cache-dir ~/.hermes/cache/scratch]
"""
import argparse
import csv
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BBOX = (-13.6, -39.3, -12.3, -37.7)  # sul, oeste, norte, leste
POINT_BBOX = (-39.0, -38.0, -13.3, -12.4)  # região de pontos testada (lon_min, lon_max, lat_min, lat_max)
CONF_DIST_M = 250  # banda de confiança: distância mínima da costa

OVERPASS_QUERY = f'''
[out:json][timeout:120];
way["natural"="coastline"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
out geom;
'''


def fetch_coastline(cache_dir):
    cache = Path(cache_dir) / "salvador_coast.json"
    if cache.exists():
        return json.loads(cache.read_text())
    url = "https://overpass-api.de/api/interpreter?data=" + urllib.parse.quote(OVERPASS_QUERY)
    req = urllib.request.Request(url, headers={"User-Agent": "ile-axe-map-audit/1.0 (LABHDUFBA)"})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.load(r)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data))
    return data


def coast_segments(coast):
    segs = []
    for e in coast.get("elements", []):
        if e.get("type") == "way" and "geometry" in e:
            pts = [(g["lat"], g["lon"]) for g in e["geometry"]]
            for a, b in zip(pts, pts[1:]):
                if a != b:
                    segs.append((a, b))
    return segs


def crossings_east(segs, lat, lon):
    n = 0
    for (lat1, lon1), (lat2, lon2) in segs:
        if (lat1 > lat) != (lat2 > lat):
            x = (lon2 - lon1) * (lat - lat1) / (lat2 - lat1) + lon1
            if x > lon:
                n += 1
    return n


def dist_to_coast_m(segs, lat, lon):
    best = float("inf")
    for (a, b) in segs:
        ax, ay = a[0], a[1]
        bx, by = b[0], b[1]
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            t = 0.0
        else:
            t = max(0.0, min(1.0, ((lat - ax) * dx + (lon - ay) * dy) / (dx * dx + dy * dy)))
        qx, qy = ax + t * dx, ay + t * dy
        dlat = (lat - qx) * 111320.0
        dlon = (lon - qy) * 111320.0 * math.cos(math.radians(lat))
        best = min(best, math.hypot(dlat, dlon))
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default=os.path.expanduser("~/.hermes/cache/scratch"))
    ap.add_argument("--src", default="data/v4_1/terreiros_nacional_v4_1.geojson")
    ap.add_argument("--out-dir", default="data/v4_2")
    args = ap.parse_args()
    os.chdir(ROOT)

    src = json.loads(Path(args.src).read_text(encoding="utf-8"))
    feats = src["features"]

    segs = coast_segments(fetch_coastline(args.cache_dir))
    print(f"segmentos de costa: {len(segs)}")

    # pontos de controle
    controls = {
        "Pelourinho": (-12.9722, -38.5108, True),
        "Itapua": (-12.9489, -38.3691, True),
        "Gantois_real": (-12.9235, -38.5046, True),
        "alto_mar": (-12.9, -38.10, False),
        "baia_centro": (-13.0, -38.60, False),
    }
    ok = True
    for name, (lat, lon, expect_land) in controls.items():
        is_land = crossings_east(segs, lat, lon) % 2 == 1
        status = "OK" if is_land == expect_land else "FALHOU"
        if is_land != expect_land:
            ok = False
        print(f"  controle {name}: {'terra' if is_land else 'mar'} [{status}]")
    if not ok:
        sys.exit("ABORT: controles de validação falharam; não gerar candidata.")

    lon_min, lon_max, lat_min, lat_max = POINT_BBOX
    flagged = []
    for i, f in enumerate(feats):
        lon, lat = f["geometry"]["coordinates"]
        if not (lon_min <= lon <= lon_max and lat_min <= lat <= lat_max):
            continue
        if crossings_east(segs, lat, lon) % 2 == 0:
            p = f["properties"]
            d = dist_to_coast_m(segs, lat, lon)
            flagged.append((i, lat, lon, d, p))

    confident = [(i, lat, lon, d, p) for (i, lat, lon, d, p) in flagged if d >= CONF_DIST_M]
    borderline = [(i, lat, lon, d, p) for (i, lat, lon, d, p) in flagged if d < CONF_DIST_M]
    print(f"pontos na água: {len(flagged)} (confiantes >= {CONF_DIST_M}m: {len(confident)}; borda: {len(borderline)})")

    # candidata v4.2: apenas os confiantes recebem geo_status='coordenada_agua'
    out_feats = []
    changed = 0
    for i, f in enumerate(feats):
        g = {k: v for k, v in f.items()}
        g["properties"] = dict(f["properties"])
        hit = next((c for c in confident if c[0] == i), None)
        if hit:
            _, lat, lon, d, _ = hit
            g["properties"]["geo_status_anterior"] = g["properties"].get("geo_status", "")
            g["properties"]["geo_status"] = "coordenada_agua"
            changed += 1
        out_feats.append(g)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = {"type": "FeatureCollection", "name": src.get("name", "terreiros"), "features": out_feats}
    (out_dir / "terreiros_nacional_v4_2.geojson").write_text(
        json.dumps(out, ensure_ascii=False), encoding="utf-8")

    # auditoria
    audit = {
        "base": "v4.1",
        "candidata": "v4.2",
        "total_v4_1": len(feats),
        "total_v4_2": len(out_feats),
        "pontos_na_agua_regiao": len(flagged),
        "marcados_coordenada_agua": changed,
        "borderline_nao_marcados": len(borderline),
        "criterio_confianca_m": CONF_DIST_M,
        "bbox_costa": list(BBOX),
        "bbox_pontos": list(POINT_BBOX),
        "por_geo_status_anterior": {},
        "nota": "v4.2: coordenadas que caem no mar/na baía (paridade ray-casting contra coastline OSM) "
                "recebem geo_status=coordenada_agua e ficam ocultas por padrão; registro preservado.",
    }
    for _, _, _, _, p in confident:
        prev = p.get("geo_status", "") or "vazio"
        audit["por_geo_status_anterior"][prev] = audit["por_geo_status_anterior"].get(prev, 0) + 1
    (out_dir / "auditoria_v4_2.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    # lista pública de flags
    with open(out_dir / "pontos_na_agua.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["lat", "lon", "dist_costa_m", "geo_status_anterior", "nome"])
        for _, lat, lon, d, p in sorted(confident, key=lambda x: -x[1]):
            w.writerow([f"{lat:.6f}", f"{lon:.6f}", round(d), p.get("geo_status", ""),
                        (p.get("nome") or p.get("name") or "Sem nome")])
    print(f"candidata escrita: {out_dir/'terreiros_nacional_v4_2.geojson'} ({changed} registros marcados)")


if __name__ == "__main__":
    main()
