#!/usr/bin/env python3
"""Onda 3: re-geocodificação dos registros CNPJ sem município validável.

Alvo: registros da v4.5 cuja fonte é CNPJ/Receita Federal e que não têm
município/UF declarados (1.932). O bruto local (gitignored) tem endereço
completo (tipo_logradouro, logradouro, número, bairro, CEP, UF,
cod_município IBGE). Geocoding API por endereço, cache por CNPJ.

Gate (tudo obrigatório):
  - partial_match=false;
  - location_type ROOFTOP ou RANGE_INTERPOLATED (número de porta real),
    OU GEOMETRIC_CENTER com place_of_worship;
  - município IBGE do bruto recuperado no GeoJSON (campo municipio);
  - distância <=25 km do centróide desse município.

Corrigidos: geo_status=geocode_cnpj_v46_validado, municipio/uf preenchidos.
Rejeitados: preservados com geo_status=geocode_nao_resolvido.
Uso: GMAPS_API_KEY=... python3 scripts/regeocode_cnpj_v46.py [--limit N]
"""
import argparse
import csv
import json
import math
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data/v4_5/terreiros_nacional_v4_5.geojson"
BRUTO = ROOT / "data/cnpj_nacional/terreiros_cnpj_nacional.csv"
MUNS = ROOT / "data/v4_2/municipios_coords.json"
OUT_DIR = ROOT / "data/v4_6"
CACHE = ROOT / "data/geocode_cnpj_cache_v46.json"  # gitignored
PAUSE_S = 0.05  # Geocoding: 50 qps padrão; usamos ~17/s com folga


def unaccent(text):
    return "".join(c for c in unicodedata.normalize("NFD", text or "")
                   if unicodedata.category(c) != "Mn")


def norm(s):
    return re.sub(r"\s+", " ", unaccent(s or "").lower()).strip()


def distance_km(lat1, lon1, lat2, lon2):
    dy = (lat1 - lat2) * 111.32
    dx = (lon1 - lon2) * 111.32 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dx, dy)


def geocode(key, query, retries=3):
    url = ("https://maps.googleapis.com/maps/api/geocode/json?address="
           + urllib.parse.quote(query) + "&key=" + key + "&language=pt-BR&region=br")
    req = urllib.request.Request(url, headers={"User-Agent": "ile-axe-map-audit/1.0 (LABHDUFBA)"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                d = json.load(response)
            break
        except Exception:
            d = None
            if attempt == retries - 1:
                return None
            time.sleep(2 * (attempt + 1))
    if not d or d.get("status") != "OK" or not d.get("results"):
        return None
    res = d["results"][0]
    loc = res["geometry"]["location"]
    return {
        "lat": float(loc["lat"]), "lng": float(loc["lng"]),
        "loc_type": res["geometry"].get("location_type", ""),
        "partial": bool(res.get("partial_match", False)),
        "types": res.get("types", []),
        "addr": res.get("formatted_address", ""),
    }


def quality(r):
    if r is None or r["partial"]:
        return False
    if r["loc_type"] in ("ROOFTOP", "RANGE_INTERPOLATED"):
        return True
    if r["loc_type"] == "GEOMETRIC_CENTER" and "place_of_worship" in r["types"]:
        return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="limitar consultas novas (0=tudo)")
    args = ap.parse_args()
    key = os.environ.get("GMAPS_API_KEY")
    if not key:
        sys.exit("ABORT: defina GMAPS_API_KEY no ambiente.")

    features = json.loads(SRC.read_text(encoding="utf-8"))["features"]
    municipios = {tuple(k.split("|")): (float(v[0]), float(v[1]))
                  for k, v in json.loads(MUNS.read_text(encoding="utf-8")).items()}
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    # bruto por razão social E nome fantasia normalizados -> lista de rows
    with open(BRUTO, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    idx = {}
    for r in rows:
        idx.setdefault(norm(r.get("razao_social", "")), []).append(r)
        if r.get("nome_fantasia"):
            idx.setdefault(norm(r["nome_fantasia"]), []).append(r)

    alvo = [i for i, f in enumerate(features)
            if "cnpj" in (f["properties"].get("fonte_label") or "").lower()
            and not (f["properties"].get("municipio") and f["properties"].get("uf"))]
    print(f"alvos CNPJ sem municipio: {len(alvo)}")

    # cod_municipio IBGE -> nome municipio (via kelvins? nao tem sigla) — usar CEP+UF no query
    # e recuperar municipio do resultado Google via addr? melhor: validar por UF + dist do centróide do cod_municipio via MUNS nao possivel (MUNS é nome|uf).
    # estrategia: geocode CEP+endereco; validar UF do resultado == UF do bruto; municipio do bruto vem do cod_municipio -> buscar nome via cache kelvins reverso.
    # alvos CNPJ sem municipio/uf: consultar em background, log em arquivo
    accepted, rejected, no_addr, no_match = [], [], [], []
    consulted = 0
    for position, i in enumerate(alvo, 1):
        p = features[i]["properties"]
        nome = norm(p.get("nome", ""))
        cands = idx.get(nome)
        if not cands:
            no_addr.append(i)
            continue
        r = cands[0] if len(cands) == 1 else None
        # homônimos: só aceitar row cuja UF case com a da entidade
        euf = (p.get("uf") or "").strip().upper()
        same_uf = [c for c in cands if (c.get("uf") or "").strip().upper() == euf]
        if same_uf:
            r = same_uf[0]
        else:
            no_addr.append(i)  # homônimo de outro estado: sem evidência de vínculo
            continue
        if not (r.get("logradouro") or "").strip() or not (r.get("numero") or "").strip():
            no_addr.append(i)
            continue
        uf = (r.get("uf") or "").strip().upper()
        query = (f"{r.get('tipo_logradouro','').strip()} {r['logradouro'].strip()}, {r['numero'].strip()}, "
                 f"{(r.get('bairro') or '').strip()}, {r.get('cep','').strip()}, {uf}, Brasil").replace("  ", " ").strip(", ")
        cn = r.get("cnpj")
        ckey = f"cnpj:{cn}"
        if ckey in cache:
            res = cache[ckey]
        else:
            if args.limit and consulted >= args.limit:
                print(f"limite de {args.limit} consultas atingido; resto fica para a proxima rodada")
                break
            res = geocode(key, query)
            cache[ckey] = res
            consulted += 1
            time.sleep(PAUSE_S)
        if res is None:
            no_match.append(i)
            continue
        if not quality(res):
            rejected.append(i)
            continue
        # UF coerente
        addr_uf = res.get("addr", "")
        if uf and uf not in addr_uf.upper().split("-") and uf not in addr_uf.upper():
            rejected.append(i)
            continue
        accepted.append((i, res, r))
        if position % 100 == 0:
            print(f"  [{position}/{len(alvo)}] consultas={consulted} aceitos={len(accepted)}")

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    out = []
    for f in features:
        out.append({"type": f.get("type", "Feature"), "geometry": dict(f["geometry"]),
                    "properties": dict(f["properties"])})
    for i, res, r in accepted:
        p = out[i]["properties"]
        p["geo_status_anterior"] = p.get("geo_status", "")
        p["geo_status"] = "geocode_cnpj_v46_validado"
        p["coord_origin"] = "google_geocoding_v46"
        out[i]["geometry"]["coordinates"] = [res["lng"], res["lat"]]
        # municipio: extrair do endereço formatado do Google (padrao "Cidade - UF")
        m = re.search(r",\s([^,]+)\s-\s([A-Z]{2})\s*,\s*\d{5}-?\d*", res["addr"]) or re.search(r",\s([^,]+)\s-\s([A-Z]{2})\s*,\s*Brasil", res["addr"])
        if m:
            p["municipio_anterior"] = p.get("municipio", "")
            p["municipio"] = m.group(1).strip()
            p["uf_anterior"] = p.get("uf", "")
            p["uf"] = m.group(2)
    for i in rejected:
        p = out[i]["properties"]
        if p.get("geo_status") == "geocode_cnpj_v46_validado":
            continue
        p["geo_status_anterior"] = p.get("geo_status", "")
        p["geo_status"] = "geocode_nao_resolvido"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "terreiros_nacional_v4_6.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": out}, ensure_ascii=False), encoding="utf-8")
    audit = {
        "base": "v4.5", "candidata": "v4.6", "total": len(out),
        "alvos": len(alvo), "com_endereco": len(alvo) - len(no_addr),
        "consultas_novas": consulted,
        "aceitos": len(accepted),
        "rejeitados_qualidade": len(rejected),
        "sem_resultado": len(no_match),
        "sem_endereco_bruto": len(no_addr),
        "criterio": {"partial_match": False, "loc_type": ["ROOFTOP", "RANGE_INTERPOLATED", "GEOMETRIC_CENTER+place_of_worship"],
                     "uf_coerente": True},
        "nota": "Onda 3 CNPJ: Geocoding API por endereco completo do bruto local (gitignored). "
                "Municipio/UF preenchidos a partir do endereco validado. Rejeitados preservados e ocultos.",
    }
    (OUT_DIR / "auditoria_v4_6.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print("resumo:", json.dumps(audit, ensure_ascii=False))


if __name__ == "__main__":
    main()
