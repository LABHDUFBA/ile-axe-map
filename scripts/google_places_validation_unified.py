#!/usr/bin/env python3
"""Validação cruzada da base unificada via Google Places API.

Valida registros que ainda não passaram pela validação:
- CNPJ/Receita Federal (1.841)
- Terreiros do Brasil (85)

Os registros do Mapeando Axé (2.409) já estão sendo validados pelo cron existente.

Para cada registro:
1. Busca no Google Places Text Search: "{nome} {cidade} {UF}"
2. Filtro de qualidade: cidade/UF + similaridade de nome
3. Classificação em 10 categorias

Uso:
  python3 scripts/google_places_validation_unified.py
"""
import json, time, urllib.request, urllib.parse, os, sys, math, re
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher
from collections import Counter
import unicodedata

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "unified"
CACHE_PATH = DATA_DIR / "google_places_cache.jsonl"
RESULTS_PATH = DATA_DIR / "google_places_results.json"
UNIFIED_GEOJSON = DATA_DIR / "terreiros_unified.geojson"

API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
if not API_KEY:
    env_path = Path.home() / ".hermes" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("GOOGLE_PLACES_API_KEY="):
                    API_KEY = line.split("=", 1)[1].strip()
                    break

if not API_KEY:
    print("ERRO: GOOGLE_PLACES_API_KEY não encontrada")
    sys.exit(1)

PLACES_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DELAY = 0.3  # ~200ms entre requests
MAX_REQUESTS = 900  # limite diário seguro


def normalize(text):
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower().strip()


def name_similarity(a, b):
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def check_city_match(google_addr, record_cidade, record_uf):
    """Verifica se o endereço do Google corresponde à cidade/UF do registro."""
    google_norm = normalize(google_addr)
    uf_norm = normalize(record_uf) if record_uf else ""
    cidade_norm = normalize(record_cidade) if record_cidade else ""

    # Verificar UF
    uf_match = False
    if uf_norm:
        # Padrões: "SP", "São Paulo", "State of São Paulo"
        if uf_norm in google_norm:
            uf_match = True
        elif len(uf_norm) == 2:
            # Verificar sigla como palavra isolada
            if re.search(rf'\b{re.escape(uf_norm)}\b', google_norm):
                uf_match = True

    # Verificar cidade
    city_match = False
    if cidade_norm:
        if cidade_norm in google_norm:
            city_match = True
        elif len(cidade_norm) > 3:
            # Similaridade fuzzy para cidade
            for word in google_norm.split(","):
                if name_similarity(cidade_norm, word.strip()) > 0.8:
                    city_match = True
                    break

    return uf_match, city_match


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def google_places_search(query):
    """Busca no Google Places Text Search."""
    params = urllib.parse.urlencode({
        "query": query,
        "key": API_KEY,
        "language": "pt-BR",
        "region": "br",
    })
    url = f"{PLACES_URL}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "IleAxeMap-Validator/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except Exception as e:
        return {"status": "ERROR", "error_message": str(e)}


def load_cache():
    cache = {}
    if CACHE_PATH.exists():
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    item = json.loads(line.strip())
                    cache[item["id"]] = item
                except json.JSONDecodeError:
                    continue
    return cache


def save_cache_item(item):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def classify(record, google_result):
    """Classifica o resultado da validação."""
    nome = record.get("nome", "")
    lat = record.get("lat")
    lng = record.get("lng")
    cidade = record.get("cidade", "")
    uf = record.get("uf", "")

    if not google_result or google_result.get("status") != "OK":
        return "nao_encontrado"

    results = google_result.get("results", [])
    if not results:
        return "nao_encontrado"

    # Encontrar melhor match
    best_match = None
    best_score = 0
    best_dist = float("inf")

    for r in results:
        g_name = r.get("name", "")
        g_addr = r.get("formatted_address", "")
        g_lat = r.get("geometry", {}).get("location", {}).get("lat")
        g_lng = r.get("geometry", {}).get("location", {}).get("lng")

        # Filtro de qualidade: cidade/UF
        uf_match, city_match = check_city_match(g_addr, cidade, uf)

        # Similaridade de nome
        sim = name_similarity(nome, g_name)

        # Score composto
        score = sim
        if city_match:
            score += 0.2
        if uf_match:
            score += 0.1

        # Distância
        dist = haversine_m(lat, lng, g_lat, g_lng) if g_lat and g_lng else float("inf")

        if score > best_score or (score == best_score and dist < best_dist):
            best_score = score
            best_match = r
            best_dist = dist

    if not best_match or best_score < 0.3:
        return "nao_encontrado"

    g_name = best_match.get("name", "")
    sim = name_similarity(nome, g_name)

    # Classificação
    if best_dist <= 100 and sim >= 0.6:
        return "confirmado"
    elif best_dist <= 500 and sim >= 0.5:
        return "confirmado_proximo"
    elif sim >= 0.5 and best_dist > 500:
        if best_dist > 2000:
            return "divergente_inconclusivo"
        return "google_melhor"
    elif sim >= 0.3 and best_dist <= 500:
        return "proximo_nome_diferente"
    elif sim >= 0.3:
        return "novo_google_possivel"
    elif best_dist <= 500:
        return "novo_google"
    else:
        return "match_ruim"


def main():
    # Carregar GeoJSON unificado
    with open(UNIFIED_GEOJSON, "r", encoding="utf-8") as f:
        gj = json.load(f)

    # Filtrar: apenas CNPJ e TerreirosBR (Mapeando Axé já tem validação própria)
    targets = [
        f for f in gj["features"]
        if f["properties"]["source"] in ("receita_federal_cnpj", "terreirosdobrasil")
    ]
    print(f"Total de registros para validar: {len(targets)}")
    print(f"  CNPJ: {sum(1 for f in targets if f['properties']['source'] == 'receita_federal_cnpj')}")
    print(f"  TerreirosBR: {sum(1 for f in targets if f['properties']['source'] == 'terreirosdobrasil')}")

    # Carregar cache
    cache = load_cache()
    print(f"Cache: {len(cache)} registros")

    # Processar
    results = []
    requests_used = 0
    processed = 0

    for feat in targets:
        props = feat["properties"]
        rec_id = props["id"]

        # Usar cache
        if rec_id in cache:
            results.append(cache[rec_id])
            continue

        if requests_used >= MAX_REQUESTS:
            print(f"\n⚠ Limite de {MAX_REQUESTS} requisições. Processados: {processed}")
            break

        nome = props.get("nome", "")
        cidade = props.get("cidade", "")
        uf = props.get("uf", "")
        lat = feat["geometry"]["coordinates"][1]
        lng = feat["geometry"]["coordinates"][0]

        # Query: nome + UF (cidade nem sempre disponível no CNPJ)
        query_parts = [nome]
        if cidade:
            query_parts.append(cidade)
        if uf:
            query_parts.append(uf)
        query_parts.append("Brasil")
        query = ", ".join(query_parts)

        time.sleep(DELAY)
        google_result = google_places_search(query)
        requests_used += 1
        processed += 1

        classification = classify(
            {"nome": nome, "cidade": cidade, "uf": uf, "lat": lat, "lng": lng},
            google_result
        )

        # Extrair melhor resultado para o cache
        g_result = None
        if google_result.get("status") == "OK" and google_result.get("results"):
            g = google_result["results"][0]
            g_lat = g.get("geometry", {}).get("location", {}).get("lat")
            g_lng = g.get("geometry", {}).get("location", {}).get("lng")
            g_result = {
                "name": g.get("name", ""),
                "formatted_address": g.get("formatted_address", ""),
                "lat": g_lat,
                "lng": g_lng,
            }

        item = {
            "id": rec_id,
            "nome": nome,
            "cidade": cidade,
            "uf": uf,
            "lat": lat,
            "lng": lng,
            "source": props.get("source", ""),
            "google_name": g_result["name"] if g_result else None,
            "google_address": g_result["formatted_address"] if g_result else None,
            "google_lat": g_result["lat"] if g_result else None,
            "google_lng": g_result["lng"] if g_result else None,
            "classification": classification,
            "query": query,
            "validated_at": datetime.now().isoformat(),
        }
        save_cache_item(item)
        cache[rec_id] = item
        results.append(item)

        if processed % 50 == 0:
            cats = Counter(r["classification"] for r in results)
            google_found = sum(1 for r in results if r.get("google_lat"))
            print(f"  [{processed}/{len(targets)}] {processed/len(targets)*100:.1f}% — reqs: {requests_used}/{MAX_REQUESTS} — Google encontrou: {google_found}")

    # Relatório
    total = len(results)
    google_found = sum(1 for r in results if r.get("google_lat"))
    cats = Counter(r["classification"] for r in results)

    print(f"\n{'='*60}")
    print(f"RELATÓRIO DE VALIDAÇÃO — BASE UNIFICADA (CNPJ + TerreirosBR)")
    print(f"{'='*60}")
    print(f"Total: {total}")
    print(f"Google encontrou: {google_found} ({google_found/total*100:.1f}%)")
    print(f"\nClassificação:")
    for cat, count in cats.most_common():
        print(f"  {cat}: {count} ({count/total*100:.1f}%)")

    # Salvar resultados
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nResultados: {RESULTS_PATH}")
    print(f"Cache: {CACHE_PATH}")


if __name__ == "__main__":
    main()