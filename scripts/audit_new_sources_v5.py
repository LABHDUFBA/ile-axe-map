#!/usr/bin/env python3
"""
audit_new_sources_v5.py — auditoria e staging das novas fontes (Atlas do Axé/AM e AXÉS/UnB/DF)
contra a base publicada v4.8.

Nada aqui é publicado: gera apenas
  data/v5_staging/auditoria_fontes_novas.json
  data/v5_staging/novos_registros.csv
  data/v5_staging/terreiros_nacional_v5_staging.geojson  (v4.8 + novos, para inspeção)

Regra de correspondência (conservadora):
  mesma UF e [nome normalizado idêntico]  OU  [similaridade >= 0.90 e distância < 500 m]
  OU [similaridade >= 0.75 e distância < 120 m]
"""
import csv
import difflib
import json
import math
import os
import re
import unicodedata
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "data", "v4_8", "terreiros_nacional_v4_8.geojson")
NEW = {
    "atlas_axe": os.path.join(ROOT, "data", "atlas_axe", "atlas_axe.geojson"),
    "axes_unb": os.path.join(ROOT, "data", "axes_unb", "axes_unb.geojson"),
}
OUT = os.path.join(ROOT, "data", "v5_staging")


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def hav(a, b, c, d):
    R = 6371000.0
    p = math.radians
    dlat, dlon = p(c - a), p(d - b)
    x = math.sin(dlat / 2) ** 2 + math.cos(p(a)) * math.cos(p(c)) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def coords(f):
    if not f.get("geometry"):
        return None
    return f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0]


def main():
    os.makedirs(OUT, exist_ok=True)
    base = json.load(open(BASE, encoding="utf-8"))["features"]
    relatorio = {"base": {"versao": "v4.8", "n": len(base)}, "fontes": {}}
    novos = []

    for fonte, path in NEW.items():
        feats = json.load(open(path, encoding="utf-8"))["features"]
        ufs = sorted({f["properties"].get("uf") for f in feats})
        candidatos = [b for b in base if b["properties"].get("uf") in ufs]
        casados, avulsos = [], []
        for f in feats:
            p = f["properties"]
            n = norm(p["nome"])
            par = None
            for b in candidatos:
                bp = b["properties"]
                r = difflib.SequenceMatcher(None, n, norm(bp["nome"])).ratio()
                cf, cb = coords(f), coords(b)
                d = hav(*cf, *cb) if cf and cb else None
                if r == 1.0 or (r >= 0.90 and d is not None and d < 500) or (
                    r >= 0.75 and d is not None and d < 120
                ):
                    par = {"entity_id": bp.get("entity_id"), "nome": bp.get("nome"),
                           "sim": round(r, 2), "dist_m": int(d) if d else None}
                    break
            (casados if par else avulsos).append(
                {"nome": p["nome"], "municipio": p.get("municipio"),
                 "lat": coords(f)[0] if coords(f) else None,
                 "lon": coords(f)[1] if coords(f) else None,
                 "geo_status": p.get("geo_status"), "match": par}
            )
            if not par:
                novos.append(f)

        relatorio["fontes"][fonte] = {
            "registros": len(feats),
            "ufs": ufs,
            "municipios": dict(Counter(f["properties"].get("municipio") for f in feats).most_common()),
            "com_coordenada": sum(1 for f in feats if f.get("geometry")),
            "casados_com_base": len(casados),
            "novos": len(avulsos),
            "match_por_uf": {"base": len(candidatos)},
            "detalhe_casados": casados,
        }
        print(f"{fonte}: {len(feats)} registros | casados {len(casados)} | novos {len(avulsos)}")

    # staging: base + novos (sem sobrescrever a base)
    staging = {"type": "FeatureCollection", "features": base + novos}
    json.dump(staging, open(os.path.join(OUT, "terreiros_nacional_v5_staging.geojson"), "w",
                            encoding="utf-8"), ensure_ascii=False)
    json.dump(relatorio, open(os.path.join(OUT, "auditoria_fontes_novas.json"), "w",
                              encoding="utf-8"), ensure_ascii=False, indent=1)

    with open(os.path.join(OUT, "novos_registros.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["fonte", "entity_id", "nome", "municipio", "uf", "tradicao", "nacao",
                    "categoria", "geo_status", "lat", "lon"])
        for f in novos:
            p = f["properties"]
            c = coords(f)
            w.writerow([p["fontes"][0], p["entity_id"], p["nome"], p.get("municipio"), p.get("uf"),
                        p.get("tradicao"), p.get("nacao"), p.get("categoria"), p.get("geo_status"),
                        c[0] if c else "", c[1] if c else ""])

    print(f"total base {len(base)} + novos {len(novos)} = {len(base)+len(novos)} (staging)")


if __name__ == "__main__":
    main()
