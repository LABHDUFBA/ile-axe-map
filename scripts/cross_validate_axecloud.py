#!/usr/bin/env python3
"""
cross_validate_axecloud.py — Validação cruzada da base nacional v3 contra o
diretório AxéCloud (derivado de Google Maps), como evidência interna.

REGRAS:
- NÃO altera a base v3 nem nenhum dataset publicado; gera apenas um arquivo
  de evidências (data/validacao_cruzada_axecloud.json).
- Match = nome normalizado idêntico E (coordenada < 500 m OU mesma cidade/UF).
- A evidência é registrada por registro: 'corroborado_axecloud' ou
  'nao_encontrado_axecloud' + metadados do match.
- AVISO METODOLÓGICO: registros da nossa fonte Google e do AxéCloud têm a
  MESMA origem a montante (Google Maps) — para esses, o match é evidência
  circular. O valor real está nos registros CEAO/CNPJ/terreirosdobrasil/CEAP,
  para os quais o AxéCloud funciona como segunda fonte independente.

Uso: python3 scripts/cross_validate_axecloud.py
"""
import json
import math
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
V3 = BASE / "data" / "terreiros_nacional_v3.geojson"
ACS = BASE / "data" / "axecloud" / "axecloud_decoded.json"
OUT = BASE / "data" / "validacao_cruzada_axecloud.json"
RAIO_M = 500.0


def norm(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def main():
    v3 = json.loads(V3.read_text(encoding="utf-8"))["features"]
    acs = json.loads(ACS.read_text(encoding="utf-8"))

    # índice AxéCloud por nome normalizado
    acs_by_name = defaultdict(list)
    for a in acs:
        n = norm(a["nome"])
        if n:
            acs_by_name[n].append(a)

    evidencias = []
    stats = Counter()
    por_fonte = defaultdict(Counter)

    for ft in v3:
        p = ft["properties"]
        nm = norm(p.get("nome"))
        lon, lat = ft["geometry"]["coordinates"][:2]
        fonte = ""
        fl = str(p.get("fonte_label") or "")
        fonte = fl if fl and fl != "Outro" else str(p.get("geo_source") or "desconhecida")

        ev = {
            "nome": p.get("nome"),
            "uf": p.get("uf"),
            "municipio": p.get("municipio"),
            "geo_status": p.get("geo_status"),
            "fonte_label": fl or None,
            "match_axecloud": None,
            "distancia_m": None,
            "slug_axecloud": None,
        }

        cands = acs_by_name.get(nm, [])
        matched = None
        for a in cands:
            d = haversine_m(lat, lon, a["lat"], a["lng"])
            same_city = norm(a["cidade"]) == norm(p.get("municipio") or "") and a["uf"] == p.get("uf")
            if d <= RAIO_M or (same_city and d <= 8000):
                if matched is None or d < matched[1]:
                    matched = (a, d)

        if matched:
            ev["match_axecloud"] = "corroborado"
            ev["distancia_m"] = round(matched[1], 1)
            ev["slug_axecloud"] = matched[0]["slug"]
            stats["corroborado"] += 1
            por_fonte[fonte]["corroborado"] += 1
        elif cands:
            # mesmo nome em outro lugar — ambíguo
            ev["match_axecloud"] = "nome_existe_local_divergente"
            ev["distancia_m"] = round(min(haversine_m(lat, lon, a["lat"], a["lng"]) for a in cands), 1)
            stats["nome_divergente"] += 1
            por_fonte[fonte]["nome_divergente"] += 1
        else:
            ev["match_axecloud"] = "nao_encontrado"
            stats["nao_encontrado"] += 1
            por_fonte[fonte]["nao_encontrado"] += 1

        evidencias.append(ev)

    report = {
        "metodo": f"nome normalizado idêntico + coord < {RAIO_M:.0f} m (ou mesma cidade/UF < 8 km)",
        "aviso": "fonte AxéCloud é derivada de Google Maps: match é evidência CIRCULAR para nossa fonte Google; independente para CEAO/CNPJ/terreirosdobrasil. Match confirma existência de listagem, não natureza religiosa. Uso interno de validação — dados NÃO republicáveis.",
        "total_v3": len(v3),
        "total_axecloud": len(acs),
        "resumo": dict(stats),
        "por_fonte": {k: dict(v) for k, v in sorted(por_fonte.items())},
        "evidencias": evidencias,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "evidencias"}, ensure_ascii=False, indent=2))
    print(f"\nOK: {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())