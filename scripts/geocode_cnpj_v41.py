#!/usr/bin/env python3
"""Geocodifica candidatos CNPJ de alta confiança para a v4.1 candidata.

- Lê o CSV bruto local e reaplica a triagem conservadora.
- Mantém somente prováveis/confirmados que não batem por nome com a v4.
- Consulta Nominatim a 1 req/s, com cache JSONL retomável.
- Arquivos com CNPJ/endereço ficam em data/cnpj_nacional/geocoding_v41/ (gitignored).
- A saída sanitizada terá apenas nome, UF, tier e coordenadas, para dedupe posterior.

Uso: python3 scripts/geocode_cnpj_v41.py [--limit N]
"""
import argparse
import csv
import json
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from triage_cnpj_nacional import classify
from build_unified_v4 import norm

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "cnpj_nacional" / "terreiros_cnpj_nacional.csv"
V4 = BASE / "data" / "v4" / "terreiros_nacional_v4.geojson"
OUT = BASE / "data" / "cnpj_nacional" / "geocoding_v41"
CACHE = OUT / "cache_privado.jsonl"
SANITIZED = OUT / "geocodificados_sanitizados.json"
URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "IleAxeMap-LABHD-UFBA/1.0 (https://github.com/LABHDUFBA/ile-axe-map)", "Accept": "application/json"}


def load_cache():
    result = {}
    if CACHE.exists():
        for line in CACHE.open(encoding="utf-8"):
            try:
                r = json.loads(line)
                result[r["cnpj"]] = r
            except (json.JSONDecodeError, KeyError):
                continue
    return result


def request(query):
    params = urlencode({"q": query, "format": "jsonv2", "limit": 1, "countrycodes": "br", "addressdetails": 1})
    try:
        with urlopen(Request(f"{URL}?{params}", headers=HEADERS), timeout=30) as resp:
            values = json.loads(resp.read())
        if values:
            r = values[0]
            return float(r["lat"]), float(r["lon"]), r.get("type") or r.get("class") or ""
    except Exception as exc:
        return None, None, f"erro:{type(exc).__name__}"
    return None, None, "sem_resultado"


def queries(row):
    street = " ".join(x for x in [row.get("tipo_logradouro", "").strip(), row.get("logradouro", "").strip()] if x)
    number = row.get("numero", "").strip()
    bairro = row.get("bairro", "").strip()
    cep = row.get("cep", "").strip()
    uf = row.get("uf", "").strip()
    full = ", ".join(x for x in [street, number, bairro, f"{cep[:5]}-{cep[5:]}" if len(cep)==8 else cep, uf, "Brasil"] if x)
    fallback = ", ".join(x for x in [f"{cep[:5]}-{cep[5:]}" if len(cep)==8 else cep, uf, "Brasil"] if x)
    return [q for q in [full, fallback] if q]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    v4 = json.loads(V4.read_text(encoding="utf-8"))["features"]
    names_v4 = {norm(f["properties"].get("nome")) for f in v4}
    with RAW.open(encoding="utf-8") as f:
        raw = list(csv.DictReader(f))

    queue = []
    for row in raw:
        tier, _, _, _ = classify(row)
        if tier not in ("provavel_terreiro", "confirmado_humano"):
            continue
        if norm(row.get("razao_social")) in names_v4 or norm(row.get("nome_fantasia")) in names_v4:
            continue
        queue.append((row, tier))
    if args.limit:
        queue = queue[:args.limit]
    cache = load_cache()
    print(f"fila: {len(queue)} | cache: {len(cache)}", flush=True)

    for i, (row, tier) in enumerate(queue, 1):
        cnpj = row["cnpj"]
        if cnpj in cache:
            continue
        lat = lon = precision = None
        query_used = ""
        for q in queries(row):
            # Política pública Nominatim: máximo uma chamada por segundo.
            time.sleep(1.05)
            lat, lon, precision = request(q)
            query_used = q
            if lat is not None:
                break
        item = {
            "cnpj": cnpj, "nome": row.get("razao_social") or row.get("nome_fantasia"),
            "nome_fantasia": row.get("nome_fantasia"), "uf": row.get("uf"),
            "tier": tier, "lat": lat, "lon": lon, "precision": precision,
            "query_used": query_used, "endereco": {k: row.get(k) for k in ("tipo_logradouro", "logradouro", "numero", "bairro", "cep")},
        }
        with CACHE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
        cache[cnpj] = item
        if i % 25 == 0:
            ok = sum(x.get("lat") is not None for x in cache.values())
            print(f"{i}/{len(queue)} | geocodificados no cache: {ok}/{len(cache)}", flush=True)

    # Saída sanitizada: não expõe identificadores, contatos nem endereço.
    sanitized = [{k: r.get(k) for k in ("nome", "nome_fantasia", "uf", "tier", "lat", "lon", "precision")}
                 for r in cache.values()]
    SANITIZED.write_text(json.dumps(sanitized, ensure_ascii=False), encoding="utf-8")
    ok = sum(r.get("lat") is not None for r in cache.values())
    print(f"OK: cache {len(cache)} | coords {ok} | saída sanitizada {SANITIZED}", flush=True)

if __name__ == "__main__":
    main()
