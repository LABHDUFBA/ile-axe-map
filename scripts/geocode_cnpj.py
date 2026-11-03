#!/usr/bin/env python3
"""Geocodifica terreiros com CNPJ via Nominatim (OpenStreetMap).

Fonte: Receita Federal (CNPJ) — 2.673 registros com endereço completo + CEP.
Estratégia: 
  1. Tentar endereço completo (logradouro, número, bairro, CEP, UF)
  2. Se falhar, tentar CEP + UF
  3. Se falhar, tentar cidade + UF
Cache local em JSONL para retomabilidade.
Rate limit: 1 req/seg (política Nominatim).

Uso:
  python3 scripts/geocode_cnpj.py
"""
import csv
import json
import time
import sys
import re
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urlencode

CSV_PATH = Path("/home/hermes/terreiros_cnpj/terreiros_cnpj.csv")
CACHE_DIR = Path(__file__).parent.parent / "data" / "cnpj" / "geocoding"
CACHE_FILE = CACHE_DIR / "nominatim_cache.jsonl"
RESULTS_DIR = CACHE_DIR

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {
    "User-Agent": "IlêAxéMap-CNPJ-Geocoder/1.0 (research@labhdufba.org)",
    "Accept": "application/json",
}
DELAY = 1.0  # 1 req/seg


def load_cache():
    """Carrega cache de CNPJs já geocodificados."""
    cache = {}
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    item = json.loads(line.strip())
                    cache[item["cnpj"]] = item
                except json.JSONDecodeError:
                    continue
    return cache


def save_cache_item(item):
    """Salva um item no cache (append)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def build_query(row):
    """Constrói 3 queries em ordem de precisão."""
    logradouro = row.get("logradouro", "").strip()
    numero = row.get("numero", "").strip()
    bairro = row.get("bairro", "").strip()
    cep = row.get("cep", "").strip()
    uf = row.get("uf", "").strip()
    tipo = row.get("tipo_logradouro", "").strip()

    # Query 1: endereço completo
    parts = []
    if tipo and logradouro:
        parts.append(f"{tipo} {logradouro}")
    elif logradouro:
        parts.append(logradouro)
    if numero:
        parts.append(numero)
    if bairro:
        parts.append(bairro)
    if cep:
        parts.append(f"{cep[:5]}-{cep[5:]}")
    if uf:
        parts.append(uf)
    parts.append("Brasil")
    q1 = ", ".join(parts) if parts else ""

    # Query 2: CEP + UF
    q2 = f"{cep[:5]}-{cep[5:]}, {uf}, Brasil" if cep and uf else ""

    # Query 3: bairro + UF
    q3 = f"{bairro}, {uf}, Brasil" if bairro and uf else ""

    return [q for q in [q1, q2, q3] if q]


def nominatim_search(query):
    """Busca no Nominatim. Retorna (lat, lng, precision) ou (None, None, None)."""
    params = urlencode({
        "q": query,
        "format": "json",
        "limit": 1,
        "countrycodes": "br",
        "addressdetails": "1",
    })
    url = f"{NOMINATIM_URL}?{params}"
    req = Request(url, headers=HEADERS)
    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data:
                r = data[0]
                lat = float(r["lat"])
                lng = float(r["lon"])
                precision = r.get("type", "") or r.get("class", "")
                return lat, lng, precision
    except Exception:
        pass
    return None, None, None


def geocode_row(row):
    """Geocodifica um registro. Retorna dict com coords."""
    queries = build_query(row)
    for q in queries:
        time.sleep(DELAY)
        lat, lng, prec = nominatim_search(q)
        if lat is not None:
            return lat, lng, prec, q
    return None, None, None, queries[0] if queries else ""


def main():
    # Carregar CSV
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Total de registros CNPJ: {len(rows)}")

    # Carregar cache
    cache = load_cache()
    print(f"Cache: {len(cache)} registros")

    # Processar
    results = []
    processed = 0
    for row in rows:
        cnpj = row.get("cnpj", "").strip()
        if not cnpj:
            continue

        # Usar cache
        if cnpj in cache:
            results.append(cache[cnpj])
            continue

        # Geocodificar
        lat, lng, prec, query_used = geocode_row(row)

        item = {
            "cnpj": cnpj,
            "razao_social": row.get("razao_social", "").strip(),
            "nome_fantasia": row.get("nome_fantasia", "").strip(),
            "cep": row.get("cep", "").strip(),
            "logradouro": row.get("logradouro", "").strip(),
            "numero": row.get("numero", "").strip(),
            "bairro": row.get("bairro", "").strip(),
            "uf": row.get("uf", "").strip(),
            "codigo_municipio": row.get("codigo_municipio", "").strip(),
            "data_inicio": row.get("data_inicio_atividade", "").strip(),
            "lat": lat,
            "lng": lng,
            "precision": prec,
            "query_used": query_used,
            "source": "receita_federal_cnpj",
        }
        save_cache_item(item)
        results.append(item)
        cache[cnpj] = item

        processed += 1
        if processed % 50 == 0:
            with_coords = sum(1 for r in results if r["lat"] is not None)
            pct = with_coords / len(results) * 100
            print(f"  [{processed}/{len(rows)}] {pct:.1f}% com coords — cache: {len(results)}")

    # Relatório final
    total = len(results)
    with_coords = sum(1 for r in results if r["lat"] is not None)
    without = total - with_coords

    # Estatísticas por UF
    uf_stats = {}
    for r in results:
        uf = r.get("uf", "?")
        if uf not in uf_stats:
            uf_stats[uf] = {"total": 0, "geocoded": 0}
        uf_stats[uf]["total"] += 1
        if r["lat"]:
            uf_stats[uf]["geocoded"] += 1

    # Estatísticas por precisão
    from collections import Counter
    prec_stats = Counter(r.get("precision", "none") for r in results if r["lat"])

    print(f"\n{'='*60}")
    print(f"RELATÓRIO DE GEOCODIFICAÇÃO CNPJ")
    print(f"{'='*60}")
    print(f"Total: {total}")
    print(f"Com coordenadas: {with_coords} ({with_coords/total*100:.1f}%)")
    print(f"Sem coordenadas: {without} ({without/total*100:.1f}%)")
    print(f"\nPor UF (top 10):")
    for uf, s in sorted(uf_stats.items(), key=lambda x: -x[1]["total"])[:10]:
        print(f"  {uf}: {s['geocoded']}/{s['total']} ({s['geocoded']/s['total']*100:.0f}%)")
    print(f"\nPrecisão:")
    for p, c in prec_stats.most_common(10):
        print(f"  {p}: {c}")

    # Salvar resultados
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    results_file = RESULTS_DIR / "nominatim_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nResultados: {results_file}")
    print(f"Cache: {CACHE_FILE}")

    # Gerar GeoJSON
    geojson = {"type": "FeatureCollection", "features": []}
    for r in results:
        if r["lat"] is None:
            continue
        geojson["features"].append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r["lng"], r["lat"]]},
            "properties": {
                "nome": r["nome_fantasia"] or r["razao_social"],
                "razao_social": r["razao_social"],
                "cnpj": r["cnpj"],
                "endereco": f"{r.get('logradouro','')}, {r.get('numero','')}",
                "bairro": r.get("bairro", ""),
                "cep": r.get("cep", ""),
                "uf": r.get("uf", ""),
                "precision": r.get("precision", ""),
                "source": "receita_federal_cnpj",
            },
        })
    geojson_file = RESULTS_DIR / "terreiros_cnpj.geojson"
    with open(geojson_file, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)
    print(f"GeoJSON: {geojson_file} ({len(geojson['features'])} features)")

    # CSV
    csv_file = RESULTS_DIR / "terreiros_cnpj_geocoded.csv"
    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "cnpj", "razao_social", "nome_fantasia", "cep", "logradouro",
            "numero", "bairro", "uf", "lat", "lng", "precision", "source"
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({
                "cnpj": r["cnpj"],
                "razao_social": r["razao_social"],
                "nome_fantasia": r.get("nome_fantasia", ""),
                "cep": r.get("cep", ""),
                "logradouro": r.get("logradouro", ""),
                "numero": r.get("numero", ""),
                "bairro": r.get("bairro", ""),
                "uf": r.get("uf", ""),
                "lat": r["lat"],
                "lng": r["lng"],
                "precision": r.get("precision", ""),
                "source": "receita_federal_cnpj",
            })
    print(f"CSV: {csv_file}")


if __name__ == "__main__":
    main()