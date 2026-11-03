#!/usr/bin/env python3
"""Scraper de terreirosdobrasil.com.br via API REST WordPress + extração de coordenadas.

API: /wp-json/wp/v2/rtcl_listing (260 listings, 100 por página)
Para cada listing, extrai coordenadas do content HTML (data-lat/data-lng ou JSON).
"""
import json
import re
import time
import csv
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE_URL = "https://www.terreirosdobrasil.com.br"
API_URL = f"{BASE_URL}/wp-json/wp/v2/rtcl_listing"
CACHE_DIR = Path(__file__).parent.parent / "data" / "terreirosdobrasil"
CACHE_FILE = CACHE_DIR / "cache.jsonl"
RESULTS_DIR = CACHE_DIR

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


def normalize_nacao(cat: str) -> str:
    """Normaliza categoria/nação do terreirosdobrasil para padrão limpo."""
    if not cat:
        return "Outro"
    cat_lower = cat.lower().strip()
    nacoes = {
        "ketu": "Ketu", "kéto": "Ketu", "keto": "Ketu",
        "angola": "Angola",
        "jeje": "Jeje", "jejé": "Jeje",
        "nagó": "Nago", "nàgó": "Nago", "nago": "Nago",
        "umbanda": "Umbanda",
        "jurema": "Jurema",
        "tambor de mina": "Tambor de Mina", "tambor": "Tambor de Mina",
        "efon": "Efon", "èfọ́n": "Efon",
        "omolokô": "Omoloko", "omoloko": "Omoloko",
        "iseshe": "Iseshe", "ìṣẹ̀ṣe": "Iseshe",
        "nàgó ègbá": "Nago Egba",
        "jejé nàgó": "Jeje Nago",
    }
    for key, val in nacoes.items():
        if key in cat_lower:
            return val
    return "Outro"


def extract_coords_from_html(html: str):
    """Extrai lat/lng do HTML da página do terreiro."""
    # 1. Google Maps ll= (coords reais do marker, não do center do plugin)
    m = re.search(r'll=(-?\d{1,3}\.\d+),(-?\d{1,3}\.\d+)', html)
    if m:
        return float(m.group(1)), float(m.group(2))
    # 2. data-lat / data-lng
    m = re.search(r'data-lat=["\'](-?\d+\.?\d*)["\']', html)
    if m:
        m2 = re.search(r'data-lng=["\'](-?\d+\.?\d*)["\']', html)
        if m2:
            return float(m.group(1)), float(m2.group(1))
    # 3. Google Maps URL com coords q=
    m = re.search(r'q=(-?\d{1,3}\.\d+),(-?\d{1,3}\.\d+)', html)
    if m:
        return float(m.group(1)), float(m.group(2))
    # 4. center= no Google Maps
    m = re.search(r'center=(-?\d{1,3}\.\d+),(-?\d{1,3}\.\d+)', html)
    if m:
        return float(m.group(1)), float(m.group(2))
    # 5. JSON lat/lng (último recurso — pode ser center do plugin)
    m = re.search(r'"lat"["\s:]*(-?\d{1,3}\.\d+)', html)
    if m:
        m2 = re.search(r'"lng"["\s:]*(-?\d{1,3}\.\d+)', html)
        if m2:
            return float(m.group(1)), float(m2.group(1))
    return None, None


def extract_address_from_html(html: str) -> str:
    """Extrai endereço do HTML (geralmente em <li> ou <address>)."""
    # <li> com endereço — procurar por padrões: Cidade - UF, CEP, State of X, Brazil
    for m in re.finditer(r'<li[^>]*>([^<]+)</li>', html):
        text = m.group(1).strip()
        if re.search(r'\w+\s*-\s*[A-Z]{2}', text) or re.search(r'\d{5}-\d{3}', text) or 'Brazil' in text or 'State of' in text:
            if len(text) > 10 and len(text) < 200:
                return text
    # <address>
    m = re.search(r'<address[^>]*>(.*?)</address>', html, re.DOTALL)
    if m:
        return _clean_html(m.group(1))
    # Padrão: Cidade - UF, CEP, Brasil
    m = re.search(r'([^<"]+,\s*\w+\s*-\s*[A-Z]{2},\s*\d{5}-\d{3}[^<"]*)', html)
    if m:
        return _clean_html(m.group(1))
    return ""


def extract_description_from_html(html: str) -> str:
    """Extrai descrição/descricao do terreiro."""
    # blockquote
    m = re.search(r'<blockquote[^>]*>(.*?)</blockquote>', html, re.DOTALL)
    if m:
        return _clean_html(m.group(1)).strip()
    # p com classe description/details
    m = re.search(r'<p[^>]*class="[^"]*(?:description|details|content)[^"]*"[^>]*>(.*?)</p>', html, re.DOTALL | re.I)
    if m:
        return _clean_html(m.group(1)).strip()
    # Qualquer <p> com texto > 50 chars
    for m in re.finditer(r'<p[^>]*>(.*?)</p>', html, re.DOTALL):
        text = _clean_html(m.group(1)).strip()
        if len(text) > 50:
            return text
    return ""


def extract_category_from_html(html: str) -> str:
    """Extrai categoria/nação do breadcrumb ou link."""
    # Padrão "Categoria: X" no Visão Geral
    m = re.search(r'Categoria:\s*</[^>]+>\s*<a[^>]*>([^<]+)</a>', html, re.I)
    if m:
        return m.group(1).strip()
    # Breadcrumb: Candomblé Ketu, Candomblé Angola, etc
    for m in re.finditer(r'>(Candombl[ée]\s+\w+|Umbanda|Jurema[^<]*|Tambor[^<]*|Èfọ́n|Ìṣẹ̀ṣe|Omolokô|Nàgó[^<]*|Jejé[^<]*)<', html):
        return m.group(1)
    return ""


def _clean_html(s: str) -> str:
    """Remove tags HTML e normaliza espaços."""
    s = re.sub(r'<[^>]+>', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def _extract_city_uf(address: str):
    """Extrai cidade e UF do endereço."""
    if not address:
        return "", ""
    # Padrão BR: Cidade - UF
    m = re.search(r'([^,]+)\s*-\s*([A-Z]{2})\b', address)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    # Padrão internacional: City - State of X, Brazil
    m = re.search(r'([^,]+)\s*-\s*State of\s+(\w+)', address, re.I)
    if m:
        state_map = {
            'São Paulo': 'SP', 'Rio de Janeiro': 'RJ', 'Bahia': 'BA',
            'Ceará': 'CE', 'Pernambuco': 'PE', 'Pará': 'PA',
            'Minas Gerais': 'MG', 'Goiás': 'GO', 'Piauí': 'PI',
            'Rio Grande do Norte': 'RN', 'Amazonas': 'AM',
        }
        state = m.group(2).strip()
        for full, sigla in state_map.items():
            if full.lower().startswith(state.lower()):
                return m.group(1).strip(), sigla
        return m.group(1).strip(), state[:2].upper()
    return "", ""


def geocode_nominatim(address: str, cidade: str = "", uf: str = "") -> tuple:
    """Geocodifica endereço via Nominatim (OpenStreetMap).
    Retorna (lat, lng) ou (None, None).
    """
    import time as _time
    if not address and not cidade:
        return None, None
    # Query: endereço completo + Brasil
    query = address if address else f"{cidade}, {uf}, Brasil"
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "countrycodes": "br",
    }
    headers = {
        "User-Agent": "TerreirosDoBrasil-Scraper/1.0 (research@labhdufba.org)",
    }
    try:
        _time.sleep(1.0)  # Respeitar política de uso do Nominatim (1 req/seg)
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        if resp.status_code == 200 and resp.json():
            r = resp.json()[0]
            return float(r["lat"]), float(r["lon"])
    except Exception:
        pass
    # Tentar só cidade/UF se endereço completo falhou
    if address and cidade:
        try:
            _time.sleep(1.0)
            query2 = f"{cidade}, {uf}, Brasil"
            resp = requests.get(url, params={"q": query2, "format": "json", "limit": 1, "countrycodes": "br"}, headers=headers, timeout=15)
            if resp.status_code == 200 and resp.json():
                r = resp.json()[0]
                return float(r["lat"]), float(r["lon"])
        except Exception:
            pass
    return None, None


def parse_listing(api_item: dict) -> dict:
    """Processa um item da API REST e extrai todos os campos."""
    content_html = api_item.get("content", {}).get("rendered", "")
    title = api_item.get("title", {}).get("rendered", "") if isinstance(api_item.get("title"), dict) else str(api_item.get("title", ""))
    link = api_item.get("link", "")
    listing_id = api_item.get("id", 0)

    lat, lng = extract_coords_from_html(content_html)
    address = extract_address_from_html(content_html)
    cidade, uf = _extract_city_uf(address)
    cat_raw = extract_category_from_html(content_html)
    nacao = normalize_nacao(cat_raw)
    desc = extract_description_from_html(content_html)

    # Se coords do HTML são o center padrão do plugin (-5.784, -35.199 = Natal/RN),
    # ou None, geocodificar via Nominatim
    if lat is None or (abs(lat - (-5.7842)) < 0.01 and abs(lng - (-35.1999)) < 0.01):
        if address or cidade:
            lat, lng = geocode_nominatim(address, cidade, uf)

    return {
        "id": listing_id,
        "nome": title.strip(),
        "nacao": nacao,
        "categoria_raw": cat_raw,
        "endereco": address,
        "cidade": cidade,
        "uf": uf,
        "lat": lat,
        "lng": lng,
        "link": link,
        "descricao": desc[:500] if desc else "",
        "source": "terreirosdobrasil.com.br",
    }


def load_cache() -> dict:
    """Carrega cache de IDs já processados."""
    cache = {}
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    item = json.loads(line.strip())
                    cache[item["id"]] = item
                except (json.JSONDecodeError, KeyError):
                    pass
    return cache


def save_cache_item(item: dict):
    """Adiciona item ao cache (append)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def scrape_all_listings(per_page: int = 100, delay: float = 0.5) -> list:
    """Scrapes todos os listings via API REST, com cache local."""
    cache = load_cache()
    print(f"Cache: {len(cache)} registros")

    # Primeira requisição para descobrir total
    resp = requests.get(API_URL, params={"per_page": per_page, "page": 1}, timeout=30, headers=HEADERS)
    if resp.status_code != 200:
        print(f"Erro API: HTTP {resp.status_code}")
        return list(cache.values())

    total = int(resp.headers.get("X-WP-Total", 0))
    total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
    print(f"Total na API: {total} registros em {total_pages} paginas")

    all_listings = list(cache.values())
    processed_ids = set(cache.keys())

    for page in range(1, total_pages + 1):
        if page > 1:
            time.sleep(delay)
            resp = requests.get(API_URL, params={"per_page": per_page, "page": page}, timeout=30, headers=HEADERS)
            if resp.status_code != 200:
                print(f"Erro pagina {page}: HTTP {resp.status_code}")
                continue

        items = resp.json()
        for item in items:
            item_id = item.get("id")
            if item_id in processed_ids:
                continue

            # Sempre buscar a página individual para extrair coords/endereço
            if item.get("link"):
                try:
                    time.sleep(delay)
                    page_resp = requests.get(item["link"], timeout=30, headers=HEADERS)
                    if page_resp.status_code == 200:
                        item["content"]["rendered"] = page_resp.text
                except Exception:
                    pass

            parsed = parse_listing(item)
            save_cache_item(parsed)
            all_listings.append(parsed)
            processed_ids.add(item_id)

        print(f"Pagina {page}/{total_pages}: {len(items)} itens (total processado: {len(all_listings)})")

    return all_listings


def to_geojson(listings: list) -> dict:
    """Converte lista de listings para GeoJSON FeatureCollection."""
    features = []
    for l in listings:
        if l.get("lat") is None or l.get("lng") is None:
            continue
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [l["lng"], l["lat"]],
            },
            "properties": {
                "id": l["id"],
                "nome": l["nome"],
                "nacao": l.get("nacao", "Outro"),
                "categoria_raw": l.get("categoria_raw", ""),
                "endereco": l.get("endereco", ""),
                "cidade": l.get("cidade", ""),
                "uf": l.get("uf", ""),
                "link": l.get("link", ""),
                "descricao": l.get("descricao", ""),
                "source": l.get("source", "terreirosdobrasil.com.br"),
            },
        })
    return {"type": "FeatureCollection", "features": features}


def to_csv(listings: list, path: str):
    """Exporta listings para CSV."""
    fieldnames = ["id", "nome", "nacao", "categoria_raw", "endereco", "cidade", "uf", "lat", "lng", "link", "descricao", "source"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for l in listings:
            writer.writerow(l)


def main():
    print("Scraping terreirosdobrasil.com.br...")
    listings = scrape_all_listings()

    with_coords = [l for l in listings if l.get("lat") is not None]
    without_coords = [l for l in listings if l.get("lat") is None]

    print(f"\nResultados:")
    print(f"  Total: {len(listings)}")
    print(f"  Com coordenadas: {len(with_coords)}")
    print(f"  Sem coordenadas: {len(without_coords)}")

    # Nacoes
    from collections import Counter
    nacoes = Counter(l.get("nacao", "Outro") for l in listings)
    print(f"  Nacoes: {dict(nacoes)}")

    # Estados
    ufs = Counter(l.get("uf", "?") for l in listings if l.get("uf"))
    print(f"  UFs: {dict(ufs)}")

    # Salvar
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # JSON completo
    json_path = RESULTS_DIR / "terreirosdobrasil_complete.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(listings, f, ensure_ascii=False, indent=2)
    print(f"\nJSON: {json_path}")

    # GeoJSON
    gj = to_geojson(listings)
    geojson_path = RESULTS_DIR / "terreirosdobrasil.geojson"
    with open(geojson_path, "w", encoding="utf-8") as f:
        json.dump(gj, f, ensure_ascii=False)
    print(f"GeoJSON: {geojson_path} ({len(gj['features'])} features)")

    # CSV
    csv_path = RESULTS_DIR / "terreirosdobrasil.csv"
    to_csv(listings, str(csv_path))
    print(f"CSV: {csv_path}")


if __name__ == "__main__":
    main()