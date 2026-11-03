#!/usr/bin/env python3
"""Recupera terreiros do Terreiros do Brasil sem endereço, buscando pelo nome no Nominatim."""
import json
import time
import re
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urlencode

DATA_FILE = Path(__file__).parent.parent / "data" / "terreirosdobrasil" / "terreirosdobrasil_complete.json"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "terreirosdobrasil" / "terreirosdobrasil_recovered.json"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "IlêAxéMap-Recovery/1.0 (research@labhdufba.org)", "Accept": "application/json"}
DELAY = 1.0

# Palavras-chave que indicam anúncio comercial (não terreiro)
AD_KEYWORDS = ['venda','vender','velas','ferro','assentamento','artes','workshop','consulta','oracular','bichos','instituto','kit ','curso','trabalhamos','vendo','produto','loja','comércio']

# Palavras que removemos do nome pra buscar (genéricas)
STOPWORDS = ['casa','centro','tenda','roça','ilê','ilé','asé','axé','terreiro','de','do','da','do','das','dos','e','o','a','os','as','umbanda','candomblé','ketu','angola','jeje','jurema','efon','nago','omoloko']

# Cidades-UF conhecidas do site (pra refinar busca)
KNOWN_UFS = ['BA','CE','SP','RJ','PE','RN','PA','GO','MG','PI','RS','SC','PR','DF','MA','MT','MS']


def is_ad(nome):
    nl = nome.lower()
    return any(k in nl for k in AD_KEYWORDS)


def clean_name_for_search(nome):
    """Remove HTML entities e stopwords do nome para buscar."""
    nome = nome.replace('&#8211;', '-').replace('&#8211', '-')
    nome = re.sub(r'&#\d+;', '', nome)
    nome = re.sub(r'[^\w\s-]', '', nome, flags=re.UNICODE)
    return nome.strip()


def nominatim_search(query, uf=None):
    params = {"q": query, "format": "json", "limit": 1, "countrycodes": "br", "addressdetails": "1"}
    if uf:
        params["state"] = uf
    url = f"{NOMINATIM_URL}?{urlencode(params)}"
    req = Request(url, headers=HEADERS)
    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data:
                r = data[0]
                return float(r["lat"]), float(r["lon"]), r.get("type", "") or r.get("class", "")
    except Exception:
        pass
    return None, None, None


def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        items = json.load(f)

    # Filtrar: sem coords reais (plugin ou None) E não é anúncio
    target = [i for i in items if not is_ad(i["nome"]) and (
        not i["lat"] or (abs(i["lat"] - (-5.7842)) < 0.01 and abs(i["lng"] - (-35.1999)) < 0.01)
    )]
    print(f"Alvos: {len(target)} terreiros sem coords reais (excluindo anúncios)")

    recovered = 0
    for item in target:
        nome = clean_name_for_search(item["nome"])
        uf = item.get("uf", "")

        # Tentativa 1: nome completo + Brasil
        time.sleep(DELAY)
        lat, lng, prec = nominatim_search(nome)
        if lat:
            item["lat"], item["lng"], item["precision"] = lat, lng, prec
            item["recovery_method"] = "nome_completo"
            recovered += 1
            print(f"  ✅ {item['nome'][:30]} → {lat}, {lng} ({prec})")
            continue

        # Tentativa 2: nome + UF
        if uf:
            time.sleep(DELAY)
            lat, lng, prec = nominatim_search(f"{nome}, {uf}, Brasil", uf)
            if lat:
                item["lat"], item["lng"], item["precision"] = lat, lng, prec
                item["recovery_method"] = "nome+uf"
                recovered += 1
                print(f"  ✅ {item['nome'][:30]} → {lat}, {lng} ({prec})")
                continue

        # Tentativa 3: palavras-chave do nome (sem stopwords) + Brasil
        words = [w for w in nome.split() if w.lower() not in STOPWORDS and len(w) > 2]
        if words and len(words) < len(nome.split()):
            keyword_query = " ".join(words[:5])
            time.sleep(DELAY)
            lat, lng, prec = nominatim_search(keyword_query)
            if lat:
                item["lat"], item["lng"], item["precision"] = lat, lng, prec
                item["recovery_method"] = "keywords"
                recovered += 1
                print(f"  ✅ {item['nome'][:30]} → {lat}, {lng} ({prec}) [kw: {keyword_query[:40]}]")
                continue

        # Tentativa 4: se tem cidade, buscar cidade (pelo menos saber onde é)
        cidade = item.get("cidade", "")
        if cidade and uf:
            time.sleep(DELAY)
            lat, lng, prec = nominatim_search(f"{cidade}, {uf}, Brasil")
            if lat:
                # Marcar como approximação de cidade (não é o terreiro exato)
                item["lat"], item["lng"] = lat, lng
                item["precision"] = "city_approximation"
                item["recovery_method"] = "cidade_only"
                recovered += 1
                print(f"  ~ {item['nome'][:30]} → {lat}, {lng} (aproximação por cidade)")

        if not item.get("lat") or (abs(item["lat"] - (-5.7842)) < 0.01 and abs(item["lng"] - (-35.1999)) < 0.01):
            print(f"  ❌ {item['nome'][:30]} — não encontrado")

    # Atualizar items originais
    by_id = {i["id"]: i for i in target}
    for i in items:
        if i["id"] in by_id:
            i.update(by_id[i["id"]])

    # Salvar
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    # Relatório
    com_coords_reais = sum(1 for i in items if i.get("lat") and not (abs(i["lat"]-(-5.7842))<0.01 and abs(i["lng"]-(-35.1999))<0.01))
    com_coords_plugin = sum(1 for i in items if i.get("lat") and (abs(i["lat"]-(-5.7842))<0.01 and abs(i["lng"]-(-35.1999))<0.01))
    sem_coords = sum(1 for i in items if not i.get("lat"))
    print(f"\n{'='*50}")
    print(f"Recuperados: {recovered}/{len(target)}")
    print(f"Total utilizável: {com_coords_reais}/260 ({com_coords_reais/260*100:.0f}%)")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()