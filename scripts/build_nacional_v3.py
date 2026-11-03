#!/usr/bin/env python3
"""
build_nacional_v3.py — Rebuild auditável da base nacional (v3).

Princípios (convenções do projeto):
- NUNCA substitui a base existente; gera terreiros_nacional_v3.geojson lado a lado.
- Herda coordenadas validadas da v2 (BA/CEAO) por nome normalizado.
- Marca (não remove) pontos suspeitos: geo_status documenta a evidência.
- Exclusões curadas (exclusoes_curadas.csv) são aplicadas por nome normalizado;
  registros removidos são listados no relatório, nunca silenciosamente.

Uso: python3 scripts/build_nacional_v3.py
Saídas: data/terreiros_nacional_v3.geojson, data/auditoria_nacional_v3.json
"""
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"

V2 = DATA / "terreiros_v2.geojson"
NAC = DATA / "terreiros_nacional_teste.geojson"
EXC = DATA / "exclusoes_curadas.csv"
OUT = DATA / "terreiros_nacional_v3.geojson"
REP = DATA / "auditoria_nacional_v3.json"

# bbox aproximado por UF (lon_min, lon_max, lat_min, lat_max) — capitais/regiões
UF_BBOX = {
    "AC": (-73.8, -66.6, -9.5, -0.5), "AL": (-36.6, -34.8, -10.5, -8.0),
    "AM": (-73.8, -56.1, -9.9, 2.3), "AP": (-54.3, -49.9, -2.3, 5.4),
    "BA": (-46.6, -37.3, -18.3, -8.5), "CE": (-41.4, -37.3, -7.8, -2.8),
    "DF": (-48.3, -47.2, -16.1, -15.3), "ES": (-41.9, -39.6, -21.3, -17.9),
    "GO": (-53.6, -45.8, -18.9, -12.4), "MA": (-48.8, -41.8, -10.2, -0.9),
    "MG": (-51.0, -39.9, -22.9, -14.2), "MS": (-58.4, -50.2, -24.1, -17.2),
    "MT": (-60.2, -50.3, -18.5, -7.3), "PA": (-58.9, -46.3, -9.9, 2.7),
    "PB": (-38.5, -34.9, -8.3, -6.0), "PE": (-37.4, -34.7, -9.4, -7.0),
    "PI": (-45.5, -38.9, -10.9, -2.7), "PR": (-54.6, -48.0, -26.7, -22.5),
    "RJ": (-44.9, -40.7, -23.8, -20.8), "RN": (-38.5, -34.9, -6.9, -4.9),
    "RO": (-66.8, -59.8, -13.2, -7.7), "RR": (-64.4, -58.9, 2.3, 5.4),
    "RS": (-57.6, -49.6, -33.7, -27.1), "SC": (-53.9, -48.3, -29.3, -25.1),
    "SE": (-38.1, -36.3, -11.0, -9.3), "SP": (-53.1, -44.2, -25.4, -19.8),
    "TO": (-50.7, -45.0, -13.5, -1.5),
}


def norm(s):
    """Normaliza nome para junção: minúsculas, sem acentos, sem pontuação, espaços únicos."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def coord_in_uf(lon, lat, uf):
    bb = UF_BBOX.get((uf or "").upper())
    if not bb:
        return None
    return bb[0] <= lon <= bb[1] and bb[2] <= lat <= bb[3]


def main():
    v2 = json.loads(V2.read_text(encoding="utf-8"))["features"]
    nac = json.loads(NAC.read_text(encoding="utf-8"))["features"]
    excl = list(csv.DictReader(EXC.open(encoding="utf-8"))) if EXC.exists() else []

    # --- índice v2 por nome normalizado (coords validadas, preferindo CEAO) ---
    v2_by_name = defaultdict(list)
    for f in v2:
        p = f["properties"]
        n = norm(p.get("nome"))
        if n and f.get("geometry"):
            v2_by_name[n].append(f)

    excl_names = {norm(r["nome"]) for r in excl if r.get("nome")}

    # --- empilhamento por coordenada na base nacional ---
    stack = Counter()
    for f in nac:
        if f.get("geometry"):
            c = f["geometry"]["coordinates"]
            stack[(round(c[0], 5), round(c[1], 5))] += 1

    out_feats = []
    removed_excl = []
    inherited = 0
    centroid_flag = 0
    uf_div = 0
    status_counts = Counter()

    for f in nac:
        p = dict(f["properties"])
        nm = norm(p.get("nome"))

        # 1) exclusões curadas
        if nm in excl_names:
            removed_excl.append(p.get("nome", "?"))
            continue

        geom = f.get("geometry")
        lon = lat = None
        if geom:
            lon, lat = geom["coordinates"][:2]

        geo_status = p.get("geo_status", "")
        stacked = (
            stack.get((round(lon, 5), round(lat, 5)), 0)
            if lon is not None and lat is not None
            else 0
        )

        # 2) herança v2: nome presente na v2 com coordenada validada
        inherit = None
        if nm in v2_by_name:
            inherit = v2_by_name[nm][0]
        if inherit:
            c = inherit["geometry"]["coordinates"]
            if coord_in_uf(c[0], c[1], p.get("uf")) or not p.get("uf"):
                p["coord_herdada_v2"] = True
                if stacked >= 10:
                    geo_status = "herdado_v2_centroide_substituido"
                else:
                    geo_status = "herdado_v2_validado"
                geom = {"type": "Point", "coordinates": [c[0], c[1]]}
                inherited += 1
            else:
                # v2 tem coords, mas UF divergente — não herdar às cegas
                geo_status = "heranca_v2_uf_divergente_rejeitada"

        # 3) UF divergente da coordenada (ex.: 'Belém, PI' geocodificado em PA)
        if lon is not None and p.get("uf") and coord_in_uf(lon, lat, p["uf"]) is False:
            if "herdado" not in geo_status:
                geo_status = (geo_status + "|" if geo_status else "") + "uf_divergente"
                uf_div += 1

        # 4) centróide empilhado (sem herança possível)
        if "herdado" not in geo_status and stacked >= 10:
            geo_status = (geo_status + "|" if geo_status else "") + "centroide_suspeito"
            centroid_flag += 1

        p["geo_status"] = geo_status or p.get("geo_source", "csv")
        status_counts[p["geo_status"]] += 1
        nf = {"type": f.get("type", "Feature"), "properties": p}
        if geom:
            nf["geometry"] = geom
        out_feats.append(nf)

    report = {
        "versao": "nacional_v3",
        "input": str(NAC.name),
        "total_input": len(nac),
        "total_output": len(out_feats),
        "excluidos_curados": len(removed_excl),
        "excluidos_nomes": removed_excl,
        "coords_herdadas_v2": inherited,
        "centroide_suspeito": centroid_flag,
        "uf_divergente": uf_div,
        "geo_status_counts": dict(status_counts),
        "por_uf": dict(Counter(f["properties"].get("uf", "") or "?" for f in out_feats).most_common()),
    }
    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": out_feats}, ensure_ascii=False), encoding="utf-8")
    REP.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "excluidos_nomes"}, ensure_ascii=False, indent=2))
    print(f"\nOK: {OUT.name} ({len(out_feats)} features) + {REP.name}")


if __name__ == "__main__":
    sys.exit(main())