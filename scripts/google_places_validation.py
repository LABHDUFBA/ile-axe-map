#!/usr/bin/env python3
"""
Validação cruzada de todos os 3.923 terreiros do Mapeando Axé via Google Places API.

Para cada registro:
1. Busca no Google Places Text Search: "{nome} {cidade} {UF}"
2. Avalia todos os resultados (não só o primeiro) com filtros de qualidade:
   a. Cidade/estado compatível
   b. Similaridade de nome (SequenceMatcher)
   c. Distância ao ponto Nominatim (se existir)
3. Classifica em:
   - confirmado: Google e Nominatim concordam (≤100m) E nome compatível
   - google_melhor: Google achou nome compatível na cidade certa, Nominatim errou ou não achou
   - nominatim_melhor: Nominatim ok, Google não achou nome compatível na cidade
   - divergente: ambos acharam mas pontos distantes E nomes diferentes (match errado)
   - novo_google: só Google achou, nome compatível, cidade certa
   - nao_encontrado: nenhum dos dois
   - sem_dados: sem info suficiente para buscar

Lógica chave: endereços de 2010 podem estar desatualizados.
O Google Places pode ter o endereço atual do terreiro.
"""

import json, time, urllib.request, urllib.parse, os, sys, math, re
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher
from collections import Counter

# Configuração
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "mapeando_axe" / "geocoding"
CACHE_PATH = DATA_DIR / "google_places_v2_cache.jsonl"
RESULTS_PATH = DATA_DIR / "google_places_v2_results.json"
UNIFIED_PATH = DATA_DIR / "unified_nominatim.json"

API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
if not API_KEY:
    env_path = Path.home() / ".hermes" / ".env"
    if env_path.exists():
        for line in env_path.read_text(errors="ignore").splitlines():
            if line.startswith("GOOGLE_PLACES_API_KEY="):
                API_KEY = line.split("=", 1)[1].strip()
                break

if not API_KEY:
    print("ERRO: GOOGLE_PLACES_API_KEY não encontrada", file=sys.stderr)
    sys.exit(1)

MAX_REQUESTS = 900
RATE_LIMIT_SEC = 1.2

# Thresholds
NAME_SIMILARITY_THRESHOLD = 0.45  # similaridade mínima de nome
DIST_CONFIRMED_M = 100    # ≤100m = confirmado
DIST_PROXIMO_M = 500      # ≤500m = próximo
DIST_MAX_CITY_M = 50000   # >50km = provavelmente outra cidade


STATE_NAMES = {
    "PE": "Pernambuco", "PA": "Pará", "RS": "Rio Grande do Sul",
    "BA": "Bahia", "SP": "São Paulo", "RJ": "Rio de Janeiro",
    "MG": "Minas Gerais", "CE": "Ceará", "MA": "Maranhão",
    "PI": "Piauí", "RN": "Rio Grande do Norte", "PB": "Paraíba",
    "AL": "Alagoas", "SE": "Sergipe", "TO": "Tocantins",
    "GO": "Goiás", "DF": "Distrito Federal", "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul", "ES": "Espírito Santo", "PR": "Paraná",
    "SC": "Santa Catarina", "AM": "Amazonas", "AP": "Amapá",
    "RR": "Roraima", "AC": "Acre", "RO": "Rondônia",
}

# Sinônimos comuns em nomes de terreiros (normalizar antes de comparar)
NAME_SYNONYMS = [
    (r"\babassá\b", "abassa"),
    (r"\babaça\b", "abassa"),
    (r"\bilê\b", "ile"),
    (r"\bilê axé\b", "ile axe"),
    (r"\biasé\b", "ase"),
    (r"\baxé\b", "axe"),
    (r"\bogum\b", "ogun"),
    (r"\boxum\b", "oxum"),
    (r"\boxalá\b", "oxala"),
    (r"\biemanjá\b", "iemanja"),
    (r"\bxangô\b", "xango"),
    (r"\biansã\b", "iansa"),
    (r"\bomulu\b", "omulu"),
    (r"\bobaluaiê\b", "obaluaye"),
    (r"\bnanã\b", "nana"),
    (r"\begunitá\b", "egunita"),
    (r"\bentidade afrocultural\b", ""),
    (r"\bassociaç[ãa]o beneficente\b", ""),
    (r"\bcentro esp[íi]rita\b", ""),
    (r"\bde\b", ""),
    (r"\bda\b", ""),
    (r"\bdo\b", ""),
    (r"\bd['\"]", ""),
    (r"\bcasa de\b", "casa"),
    (r"\bterreiro de\b", "terreiro"),
]


def normalize_name(name):
    """Normaliza nome para comparação: lowercase, sem acentos, sinônimos unificados."""
    if not name:
        return ""
    s = name.lower().strip()
    # Remover acentos
    s = re.sub(r"[áàâã]", "a", s)
    s = re.sub(r"[éê]", "e", s)
    s = re.sub(r"[í]", "i", s)
    s = re.sub(r"[óôõ]", "o", s)
    s = re.sub(r"[ú]", "u", s)
    s = re.sub(r"[ç]", "c", s)
    # Aplicar sinônimos
    for pattern, replacement in NAME_SYNONYMS:
        s = re.sub(pattern, replacement, s)
    # Remover pontuação e espaços extras
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def name_similarity(name1, name2):
    """Similaridade entre dois nomes normalizados (0-1)."""
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)
    if not n1 or not n2:
        return 0.0
    return SequenceMatcher(None, n1, n2).ratio()


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def check_city_match(google_address, record_city, record_state):
    """Verifica se o endereço do Google contém a cidade/estado do registro."""
    if not google_address:
        return False, False
    addr_lower = google_address.lower()
    city_lower = (record_city or "").lower().strip()
    state_name = STATE_NAMES.get(record_state, record_state or "").lower()
    
    city_match = False
    state_match = False
    
    if city_lower and city_lower in addr_lower:
        city_match = True
    # Também verificar sem acentos (unicodedata)
    import unicodedata
    def strip_accents(s):
        return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    city_norm = strip_accents(city_lower)
    addr_norm = strip_accents(addr_lower)
    if city_norm and city_norm in addr_norm:
        city_match = True
    
    if record_state and record_state.lower() in addr_lower:
        state_match = True
    if state_name and state_name in addr_lower:
        state_match = True
    
    return city_match, state_match


def evaluate_google_result(google_result, record):
    """Avalia um resultado individual do Google. Retorna score e dados."""
    g_name = google_result.get("name", "")
    g_addr = google_result.get("formatted_address", "")
    g_lat = google_result["geometry"]["location"]["lat"]
    g_lng = google_result["geometry"]["location"]["lng"]
    
    # Similaridade de nome
    sim = name_similarity(record.get("name", ""), g_name)
    
    # Cidade/estado
    city_match, state_match = check_city_match(g_addr, record.get("city", ""), record.get("state", ""))
    
    # Distância ao Nominatim (se existir)
    dist_m = None
    if record.get("nominatim_lat") is not None:
        dist_m = haversine_m(record["nominatim_lat"], record["nominatim_lng"], g_lat, g_lng)
    
    # Score: combina nome + cidade + estado
    score = 0.0
    score += sim * 0.5  # nome é 50% do score
    if city_match:
        score += 0.3
    if state_match:
        score += 0.2
    # Penalizar se muito longe do Nominatim e Nominatim existe
    if dist_m is not None and dist_m > DIST_MAX_CITY_M:
        score *= 0.3  # provavelmente cidade errada
    
    return {
        "place_id": google_result.get("place_id"),
        "name": g_name,
        "address": g_addr,
        "lat": g_lat,
        "lng": g_lng,
        "rating": google_result.get("rating"),
        "user_ratings_total": google_result.get("user_ratings_total"),
        "business_status": google_result.get("business_status"),
        "types": google_result.get("types", []),
        "name_similarity": round(sim, 3),
        "city_match": city_match,
        "state_match": state_match,
        "distance_to_nominatim_m": round(dist_m) if dist_m is not None else None,
        "score": round(score, 3),
    }


def classify_record(record, best_google, all_google):
    """Classifica o registro baseado na melhor match do Google vs Nominatim."""
    has_nominatim = record.get("nominatim_lat") is not None
    has_google = best_google is not None

    if not has_google and not has_nominatim:
        return "nao_encontrado"

    if not has_google:
        return "nominatim_melhor"

    # Google achou — verificar qualidade
    g = best_google
    sim = g["name_similarity"]
    city_ok = g["city_match"]
    state_ok = g["state_match"]
    dist = g["distance_to_nominatim_m"]

    # Match de baixa qualidade: nome diferente + cidade errada
    if sim < NAME_SIMILARITY_THRESHOLD and not city_ok:
        if has_nominatim:
            return "nominatim_melhor"
        return "match_ruim"

    # Se Nominatim não existe
    if not has_nominatim:
        if sim >= NAME_SIMILARITY_THRESHOLD and (city_ok or state_ok):
            return "novo_google"
        elif city_ok or state_ok:
            return "novo_google_possivel"
        else:
            return "match_ruim"

    # Ambos existem — comparar
    if dist is not None:
        if dist <= DIST_CONFIRMED_M and sim >= NAME_SIMILARITY_THRESHOLD:
            return "confirmado"
        elif dist <= DIST_PROXIMO_M:
            if sim >= NAME_SIMILARITY_THRESHOLD:
                return "confirmado_proximo"
            else:
                return "proximo_nome_diferente"
        else:
            # Divergente — mas qual é melhor?
            if sim >= NAME_SIMILARITY_THRESHOLD and city_ok:
                # Google tem nome compatível e cidade certa → provável endereço atualizado
                return "google_melhor"
            elif sim < NAME_SIMILARITY_THRESHOLD:
                # Google achou coisa errada
                return "nominatim_melhor"
            else:
                return "divergente_inconclusivo"

    return "indefinido"


def load_cache():
    cache = {}
    if CACHE_PATH.exists():
        with open(CACHE_PATH) as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    cache[entry["source_record_id"]] = entry
    return cache


def save_cache_entry(entry):
    with open(CACHE_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def search_places(query, request_counter):
    params = urllib.parse.urlencode({"query": query, "key": API_KEY, "language": "pt-BR"})
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?{params}"
    results = []
    page = 0

    while url and request_counter[0] < MAX_REQUESTS:
        page += 1
        request_counter[0] += 1
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            print(f"    ERRO: {e}", file=sys.stderr)
            break

        status = data.get("status", "")
        if status not in ("OK", "ZERO_RESULTS"):
            print(f"    API status: {status} — {data.get('error_message', '')}", file=sys.stderr)
            if status == "OVER_QUERY_LIMIT":
                return results, True
            break

        page_results = data.get("results", [])
        results.extend(page_results)

        next_token = data.get("next_page_token")
        if next_token:
            time.sleep(3)
            url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?pagetoken={next_token}&key={API_KEY}"
        else:
            url = None

    return results, False


def build_query(record):
    name = record.get("name", "").strip()
    city = record.get("city", "").strip()
    state = record.get("state", "").strip()
    state_full = STATE_NAMES.get(state, state)

    if name and city:
        return f"{name} {city} {state_full} Brazil"
    elif name:
        return f"{name} {state_full} Brazil"
    elif city:
        return f"terreiro candomblé {city} {state_full} Brazil"
    else:
        return None


def main():
    with open(UNIFIED_PATH) as f:
        records = json.load(f)

    print(f"Total de registros: {len(records)}")
    print(f"Cache: {CACHE_PATH}")

    cache = load_cache()
    print(f"Cache existente: {len(cache)} registros")

    to_process = [r for r in records if r["source_record_id"] not in cache]
    print(f"A processar: {len(to_process)} registros")

    if not to_process:
        print("Todos processados. Gerando resultados...")
    else:
        request_counter = [0]
        processed = 0
        total = len(to_process)
        quota_exceeded = False

        for record in to_process:
            if quota_exceeded or request_counter[0] >= MAX_REQUESTS:
                print(f"\n⚠ Limite de {MAX_REQUESTS} requisições. Processados: {processed}")
                break

            rid = record["source_record_id"]
            query = build_query(record)

            if not query:
                entry = {
                    "source_record_id": rid,
                    "name": record.get("name", ""),
                    "city": record.get("city", ""),
                    "state": record.get("state", ""),
                    "google_query": None,
                    "google_status": "skip_no_data",
                    "google_results_count": 0,
                    "google_all_evaluated": [],
                    "google_best": None,
                    "classification": "sem_dados",
                    "nominatim_lat": record.get("nominatim_lat"),
                    "nominatim_lng": record.get("nominatim_lng"),
                    "nominatim_precision": record.get("nominatim_precision"),
                    "processed_at": datetime.now().isoformat(),
                }
                save_cache_entry(entry)
                cache[rid] = entry
                processed += 1
                continue

            results, quota_hit = search_places(query, request_counter)
            if quota_hit:
                quota_exceeded = True

            # Avaliar TODOS os resultados
            evaluated = []
            for r in results:
                ev = evaluate_google_result(r, record)
                evaluated.append(ev)

            # Ordenar por score (melhor primeiro)
            evaluated.sort(key=lambda x: x["score"], reverse=True)

            best = evaluated[0] if evaluated else None
            classification = classify_record(record, best, evaluated)

            entry = {
                "source_record_id": rid,
                "name": record.get("name", ""),
                "city": record.get("city", ""),
                "state": record.get("state", ""),
                "google_query": query,
                "google_status": "found" if results else "zero_results",
                "google_results_count": len(results),
                "google_all_evaluated": evaluated[:5],  # top 5 apenas
                "google_best": best,
                "classification": classification,
                "nominatim_lat": record.get("nominatim_lat"),
                "nominatim_lng": record.get("nominatim_lng"),
                "nominatim_precision": record.get("nominatim_precision"),
                "processed_at": datetime.now().isoformat(),
            }
            save_cache_entry(entry)
            cache[rid] = entry

            processed += 1
            if processed % 50 == 0:
                pct = processed / total * 100
                print(f"  [{processed}/{total}] {pct:.1f}% — reqs: {request_counter[0]}/{MAX_REQUESTS}")

            time.sleep(RATE_LIMIT_SEC)

        print(f"\nProcessados: {processed}")
        print(f"Requisições usadas: {request_counter[0]}")

    # Consolidar resultados
    all_results = list(cache.values())
    with open(RESULTS_PATH, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    # Relatório
    classes = Counter(r.get("classification") for r in all_results)
    google_found = sum(1 for r in all_results if r.get("google_status") == "found")
    nominatim_found = sum(1 for r in all_results if r.get("nominatim_lat") is not None)

    print(f"\n{'='*60}")
    print(f"RELATÓRIO DE VALIDAÇÃO CRUZADA v2")
    print(f"{'='*60}")
    print(f"Total: {len(all_results)}")
    print(f"Nominatim encontrou: {nominatim_found} ({nominatim_found/len(all_results)*100:.1f}%)")
    print(f"Google encontrou: {google_found} ({google_found/len(all_results)*100:.1f}%)")
    print(f"\nClassificação:")
    for cls, count in classes.most_common():
        pct = count / len(all_results) * 100
        print(f"  {cls}: {count} ({pct:.1f}%)")

    print(f"\nResultados: {RESULTS_PATH}")
    print(f"Cache: {CACHE_PATH}")


if __name__ == "__main__":
    main()