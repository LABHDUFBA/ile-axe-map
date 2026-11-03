#!/usr/bin/env python3
"""Pipeline de unificação e deduplicação das 3 fontes de terreiros.

Fontes:
1. Mapeando Axé (3.923 regs, 2.721 com coords) — dados acadêmicos 2010
2. Terreiros do Brasil (260 regs, 138 com coords) — plataforma colaborativa
3. CNPJ/Receita Federal (2.673 regs, 2.526 com coords) — registros formais

Estratégia de deduplicação:
1. Match exato por CNPJ (quando disponível)
2. Match por proximidade geográfica (<100m) + similaridade de nome (≥70%)
3. Match por CEP + número + logradouro similar

Prioridade de fonte quando duplicata:
1. CNPJ (endereço verificado, ativo)
2. Mapeando Axé (dados acadêmicos validados)
3. Terreiros do Brasil (auto-declarado)

Saída:
- GeoJSON unificado
- CSV unificado
- Relatório de deduplicação

Uso:
  python3 scripts/unify_terreiros.py
"""
import json
import csv
import re
import math
import unicodedata
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher

# Paths
ROOT = Path(__file__).parent.parent
MAPEANDO_FILE = ROOT / "data" / "mapeando_axe" / "geocoding" / "unified_nominatim.json"
TERREIROS_FILE = ROOT / "data" / "terreirosdobrasil" / "terreirosdobrasil_recovered.json"
CNPJ_FILE = ROOT / "data" / "cnpj" / "geocoding" / "nominatim_results.json"
OUTPUT_DIR = ROOT / "data" / "unified"

# Taxonomia de nações
NACAO_MAP = {
    "ketu": "Ketu", "Ketu": "Ketu", "candomblé ketu": "Ketu", "candomble ketu": "Ketu",
    "angola": "Angola", "Angola": "Angola", "candomblé angola": "Angola", "candomble angola": "Angola",
    "jeje": "Jeje", "Jeje": "Jeje", "jejé": "Jeje", "candomblé jeje": "Jeje", "candomble jeje": "Jeje",
    "efon": "Efon", "Efon": "Efon", "èfọ́n": "Efon",
    "nago": "Nago", "Nago": "Nago", "nàgó": "Nago", "nagô": "Nago",
    "umbanda": "Umbanda", "Umbanda": "Umbanda",
    "jurema": "Jurema", "Jurema": "Jurema",
    "omoloko": "Omoloko", "Omoloko": "Omoloko", "omolokô": "Omoloko",
    "tambor de mina": "Tambor de Mina", "Tambor de Mina": "Tambor de Mina",
    "iseshe": "Iseshe", "Iseshe": "Iseshe", "ìṣẹ̀ṣe": "Iseshe",
    "matriz africana": "Matriz Africana",
    "outro": "Outro", "Outro": "Outro",
}

# Fonte priority (lower = higher priority)
SOURCE_PRIORITY = {"receita_federal_cnpj": 1, "mapeando_axe": 2, "terreirosdobrasil": 3}


def normalize_nacao(nacao_raw, nome=""):
    """Normaliza nação para a taxonomia unificada."""
    if not nacao_raw:
        # Tentar inferir do nome
        nome_lower = nome.lower()
        if "ketu" in nome_lower or "keto" in nome_lower:
            return "Ketu"
        if "angola" in nome_lower:
            return "Angola"
        if "jeje" in nome_lower or "jejé" in nome_lower:
            return "Jeje"
        if "umbanda" in nome_lower:
            return "Umbanda"
        if "jurema" in nome_lower:
            return "Jurema"
        if "efon" in nome_lower:
            return "Efon"
        return "Outro"
    key = nacao_raw.strip().lower()
    return NACAO_MAP.get(key, NACAO_MAP.get(nacao_raw.strip(), "Outro"))


def normalize_text(text):
    """Remove acentos e normaliza para comparação."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower().strip()


def name_similarity(a, b):
    """Similaridade entre dois nomes (0-1). Usa SequenceMatcher em texto normalizado."""
    na = normalize_text(a)
    nb = normalize_text(b)
    if not na or not nb:
        return 0.0
    # Remover palavras comuns
    stopwords = {"de", "do", "da", "dos", "das", "e", "o", "a", "os", "as", "centro", "terreiro", "casa", "tenda"}
    na_words = set(w for w in na.split() if w not in stopwords and len(w) > 2)
    nb_words = set(w for w in nb.split() if w not in stopwords and len(w) > 2)
    if na_words and nb_words:
        intersection = na_words & nb_words
        union = na_words | nb_words
        jaccard = len(intersection) / len(union) if union else 0
        seq_ratio = SequenceMatcher(None, na, nb).ratio()
        return max(jaccard, seq_ratio)
    return SequenceMatcher(None, na, nb).ratio()


def haversine_m(lat1, lon1, lat2, lon2):
    """Distância em metros entre dois pontos."""
    R = 6371000  # raio da Terra em metros
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def load_mapeando_axe():
    """Carrega registros do Mapeando Axé."""
    if not MAPEANDO_FILE.exists():
        print(f"⚠ Mapeando Axé não encontrado: {MAPEANDO_FILE}")
        return []
    with open(MAPEANDO_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    records = []
    for item in data:
        lat = item.get("nominatim_lat")
        lng = item.get("nominatim_lng")
        if lat is None or lng is None or lat == "" or lng == "":
            continue
        records.append({
            "id": f"mapeando_{item.get('source_record_id', '')}",
            "nome": item.get("name", ""),
            "nacao": normalize_nacao(item.get("nation_line_raw", ""), item.get("name", "")),
            "endereco": item.get("address_raw", ""),
            "cidade": item.get("city", ""),
            "uf": item.get("state", ""),
            "cep": item.get("postcode", ""),
            "lat": float(lat),
            "lng": float(lng),
            "precision": item.get("nominatim_precision", ""),
            "source": "mapeando_axe",
            "source_priority": 2,
            "cnpj": "",
        })
    print(f"Mapeando Axé: {len(records)} registros com coords")
    return records


def load_terreiros_brasil():
    """Carrega registros do Terreiros do Brasil."""
    if not TERREIROS_FILE.exists():
        # Tentar arquivo original
        fallback = ROOT / "data" / "terreirosdobrasil" / "terreirosdobrasil_complete.json"
        if not fallback.exists():
            print(f"⚠ Terreiros do Brasil não encontrado")
            return []
        filepath = fallback
    else:
        filepath = TERREIROS_FILE
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    records = []
    # Plugin coords (Natal/RN padrão)
    PLUGIN_LAT, PLUGIN_LNG = -5.7842, -35.1999
    for item in data:
        lat = item.get("lat")
        lng = item.get("lng")
        if lat is None or lng is None:
            continue
        # Pular coords inválidas do plugin
        if abs(lat - PLUGIN_LAT) < 0.01 and abs(lng - PLUGIN_LNG) < 0.01:
            continue
        records.append({
            "id": f"terreirosbr_{item.get('id', '')}",
            "nome": item.get("nome", ""),
            "nacao": normalize_nacao(item.get("nacao", ""), item.get("nome", "")),
            "endereco": item.get("endereco", ""),
            "cidade": item.get("cidade", ""),
            "uf": item.get("uf", ""),
            "cep": "",
            "lat": float(lat),
            "lng": float(lng),
            "precision": item.get("precision", ""),
            "source": "terreirosdobrasil",
            "source_priority": 3,
            "cnpj": "",
        })
    print(f"Terreiros do Brasil: {len(records)} registros com coords reais")
    return records


def load_cnpj():
    """Carrega registros do CNPJ/Receita Federal."""
    if not CNPJ_FILE.exists():
        print(f"⚠ CNPJ não encontrado: {CNPJ_FILE}")
        return []
    with open(CNPJ_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    records = []
    for item in data:
        lat = item.get("lat")
        lng = item.get("lng")
        if lat is None or lng is None:
            continue
        nome = item.get("nome_fantasia") or item.get("razao_social", "")
        # Construir endereço
        logradouro = item.get("logradouro", "")
        numero = item.get("numero", "")
        bairro = item.get("bairro", "")
        endereco = f"{logradouro}, {numero}" if numero else logradouro
        records.append({
            "id": f"cnpj_{item.get('cnpj', '')}",
            "nome": nome,
            "nacao": normalize_nacao("", nome),  # Inferir do nome
            "endereco": endereco,
            "cidade": "",  # CNPJ não tem nome da cidade, só código
            "uf": item.get("uf", ""),
            "cep": item.get("cep", ""),
            "lat": float(lat),
            "lng": float(lng),
            "precision": item.get("precision", ""),
            "source": "receita_federal_cnpj",
            "source_priority": 1,
            "cnpj": item.get("cnpj", ""),
        })
    print(f"CNPJ/Receita: {len(records)} registros com coords")
    return records


def deduplicate(records):
    """Deduplica registros por proximidade geográfica + similaridade de nome."""
    # Ordenar por prioridade de fonte (CNPJ primeiro)
    records.sort(key=lambda r: r["source_priority"])

    kept = []
    duplicates = []
    seen_coords = []  # (lat, lng, index)

    for rec in records:
        is_dup = False
        matched_with = None

        for i, (slat, slng, sidx) in enumerate(seen_coords):
            dist = haversine_m(rec["lat"], rec["lng"], slat, slng)
            if dist < 100:  # <100m
                sim = name_similarity(rec["nome"], kept[sidx]["nome"])
                if sim >= 0.5:  # ≥50% similaridade (baixado de 70% pra captar mais)
                    is_dup = True
                    matched_with = sidx
                    break
            # Também checar por CEP
            if dist < 500 and rec.get("cep") and kept[sidx].get("cep"):
                if rec["cep"] == kept[sidx]["cep"]:
                    sim = name_similarity(rec["nome"], kept[sidx]["nome"])
                    if sim >= 0.3:
                        is_dup = True
                        matched_with = sidx
                        break

        if is_dup:
            duplicates.append({
                "kept": kept[matched_with]["id"],
                "kept_name": kept[matched_with]["nome"][:40],
                "kept_source": kept[matched_with]["source"],
                "removed": rec["id"],
                "removed_name": rec["nome"][:40],
                "removed_source": rec["source"],
                "similarity": round(name_similarity(rec["nome"], kept[matched_with]["nome"]), 3),
                "distance_m": round(dist, 1),
            })
        else:
            seen_coords.append((rec["lat"], rec["lng"], len(kept)))
            kept.append(rec)

    return kept, duplicates


def main():
    print("=" * 60)
    print("PIPELINE DE UNIFICAÇÃO E DEDUPLICAÇÃO")
    print("=" * 60)

    # Carregar fontes
    print("\n1. Carregando fontes...")
    mapeando = load_mapeando_axe()
    terreiros = load_terreiros_brasil()
    cnpj = load_cnpj()
    all_records = mapeando + terreiros + cnpj
    print(f"\nTotal bruto: {len(all_records)} registros")

    # Deduplicar
    print("\n2. Deduplicando...")
    kept, duplicates = deduplicate(all_records)
    print(f"  Mantidos: {len(kept)}")
    print(f"  Duplicatas removidas: {len(duplicates)}")
    print(f"  Redução: {len(duplicates)}/{len(all_records)} ({len(duplicates)/len(all_records)*100:.1f}%)")

    # Estatísticas
    from collections import Counter
    source_stats = Counter(r["source"] for r in kept)
    nacao_stats = Counter(r["nacao"] for r in kept)
    uf_stats = Counter(r["uf"] for r in kept)

    print(f"\n3. Estatísticas da base unificada:")
    print(f"\n  Por fonte:")
    for src, count in source_stats.most_common():
        print(f"    {src}: {count}")
    print(f"\n  Por nação:")
    for nacao, count in nacao_stats.most_common():
        print(f"    {nacao}: {count}")
    print(f"\n  Por UF (top 15):")
    for uf, count in uf_stats.most_common(15):
        print(f"    {uf}: {count}")

    # Amostra de duplicatas
    if duplicates:
        print(f"\n  Amostra de duplicatas (top 10):")
        for d in duplicates[:10]:
            print(f"    {d['kept_source']}:{d['kept_name']} ← {d['removed_source']}:{d['removed_name']} (sim={d['similarity']}, dist={d['distance_m']}m)")

    # Salvar GeoJSON
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    geojson = {"type": "FeatureCollection", "features": []}
    for r in kept:
        geojson["features"].append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r["lng"], r["lat"]]},
            "properties": {
                "id": r["id"],
                "nome": r["nome"],
                "nacao": r["nacao"],
                "endereco": r["endereco"],
                "cidade": r["cidade"],
                "uf": r["uf"],
                "cep": r["cep"],
                "precision": r["precision"],
                "source": r["source"],
                "cnpj": r["cnpj"],
            },
        })
    geojson_file = OUTPUT_DIR / "terreiros_unified.geojson"
    with open(geojson_file, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)
    print(f"\n4. Saídas:")
    print(f"  GeoJSON: {geojson_file} ({len(geojson['features'])} features)")

    # Salvar CSV
    csv_file = OUTPUT_DIR / "terreiros_unified.csv"
    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "nome", "nacao", "endereco", "cidade", "uf", "cep",
            "lat", "lng", "precision", "source", "cnpj"
        ])
        writer.writeheader()
        for r in kept:
            writer.writerow({
                "id": r["id"], "nome": r["nome"], "nacao": r["nacao"],
                "endereco": r["endereco"], "cidade": r["cidade"], "uf": r["uf"],
                "cep": r["cep"], "lat": r["lat"], "lng": r["lng"],
                "precision": r["precision"], "source": r["source"], "cnpj": r["cnpj"],
            })
    print(f"  CSV: {csv_file}")

    # Salvar relatório de deduplicação
    dup_file = OUTPUT_DIR / "deduplication_report.json"
    with open(dup_file, "w", encoding="utf-8") as f:
        json.dump({
            "total_bruto": len(all_records),
            "mantidos": len(kept),
            "duplicatas": len(duplicates),
            "reducao_pct": round(len(duplicates) / len(all_records) * 100, 2),
            "duplicates": duplicates,
        }, f, ensure_ascii=False, indent=2)
    print(f"  Relatório dedup: {dup_file}")

    print(f"\n{'='*60}")
    print(f"BASE UNIFICADA: {len(kept)} terreiros únicos")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()