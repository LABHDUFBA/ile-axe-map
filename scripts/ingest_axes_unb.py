#!/usr/bin/env python3
"""
ingest_axes_unb.py — coleta e normaliza a plataforma AXÉS (LHS/UnB, DF).

Fonte: https://lhs.unb.br/axes-social/communities  (Next.js; dados em
GET https://lhs.unb.br/axes/communities, JSON paginado).

Particularidades:
  - 8 comunidades (todas no DF), sem coordenadas no payload → geocodificação
    aproximada por Nominatim, com fallback para o centroide da região
    administrativa. O geo_status registra o nível de precisão obtido.
  - Contém dados pessoais (phone/e-mail publicados pela própria plataforma).
    Por política do Ilê Axé Map, contatos NÃO entram nas camadas publicáveis:
    o CSV só indica se a casa publica contato (booleano).

Saídas (data/axes_unb/):
  raw_communities.json  payload cru
  axes_unb.csv          tabela normalizada (sem telefone/e-mail)
  axes_unb.geojson      camada normalizada (v5 staging)
  geocode_cache.json    cache das consultas Nominatim

Uso: python3 scripts/ingest_axes_unb.py [--no-geocode]
"""
import csv
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "axes_unb")
API = "https://lhs.unb.br/axes/communities"
FONTE_LABEL = "AXÉS / LHS-UnB (DF)"
FONTE_URL = "https://lhs.unb.br/axes-social/communities"
UA = "IleAxeMap/1.0 (pesquisa academica LABHDUFBA; contato: labhdufba)"

# fallback: centroide aproximado da região administrativa / município
FALLBACK = {
    "ceilândia": (-15.8095, -48.1075),
    "recanto das emas": (-15.9050, -48.0620),
    "sobradinho": (-15.6520, -47.7900),
    "núcleo bandeirante": (-15.8700, -47.9700),
    "paranoá": (-15.7770, -47.7770),
    "brasília": (-15.7939, -47.8828),
    "planaltina": (-15.6170, -47.6480),
}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def entity_id(nome, municipio, uf):
    import hashlib
    return "axes_" + hashlib.sha1(f"{norm(nome)}|{norm(municipio)}|{uf}".encode()).hexdigest()[:12]


def fetch_all():
    out, page = [], 1
    while True:
        req = urllib.request.Request(
            f"{API}?page={page}", headers={"User-Agent": UA, "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read().decode())
        out.extend(d.get("communities", []))
        if len(out) >= d.get("total", 0) or not d.get("communities"):
            break
        page += 1
        time.sleep(0.5)
    return out


def nominatim(q, cache):
    if q in cache:
        return cache[q]
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "json", "limit": 1, "countrycodes": "br"}
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        res = [{"__error__": str(e)}]
    cache[q] = res
    time.sleep(1.1)  # política de uso do Nominatim: 1 req/s
    return res


def geocode(endereco, cache):
    """Retorna (lat, lon, geo_status)."""
    limpo = re.sub(r"\|", ",", endereco or "")
    limpo = re.sub(r"CEP:\s*[\d.\-]+", "", limpo)
    limpo = re.sub(r"\s+", " ", limpo).strip(" ,-")
    for q in (f"{limpo}, Brasil", f"{limpo}, DF, Brasil"):
        res = nominatim(q, cache)
        if res and "lat" in res[0]:
            return float(res[0]["lat"]), float(res[0]["lon"]), "nominatim_endereco"
    for chave, (lat, lon) in FALLBACK.items():
        if norm(chave) in norm(limpo):
            return lat, lon, f"centroide_{norm(chave).replace(' ', '_')}"
    return None, None, "sem_coordenada"


def main():
    os.makedirs(OUT, exist_ok=True)
    raw_path = os.path.join(OUT, "raw_communities.json")
    if "--from-cache" in sys.argv and os.path.exists(raw_path):
        comunidades = json.load(open(raw_path, encoding="utf-8"))["communities"]
    else:
        comunidades = fetch_all()
        json.dump({"communities": comunidades, "total": len(comunidades)},
                  open(raw_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    cache_path = os.path.join(OUT, "geocode_cache.json")
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}

    rows, feats = [], []
    for c in comunidades:
        end = c.get("fullAddress") or ""
        if "--no-geocode" in sys.argv:
            lat = lon = None
            status = "nao_geocodificado"
        else:
            lat, lon, status = geocode(end, cache)
        muni = "Brasília"
        localidade = "Brasília"
        for chave in ("Ceilândia", "Recanto das Emas", "Sobradinho II", "Sobradinho", "Paranoá",
                      "Planaltina", "Núcleo Bandeirante", "Taguatinga", "Gama", "Tororó",
                      "Núcleo Rural", "Pôr do Sol"):
            if norm(chave) in norm(end):
                localidade = chave  # RAs do DF; município formal é Brasília
                break
        nome = c.get("name") or c.get("nome")
        categoria = "projeto/plataforma" if "atlas dos terreiros" in norm(nome) else "terreiro"
        props = {
            "entity_id": entity_id(nome, muni, "DF"),
            "nome": nome,
            "municipio": muni,
            "uf": "DF",
            "fontes": ["axes_unb"],
            "num_fontes": 1,
            "fonte_label": FONTE_LABEL,
            "fonte_url": FONTE_URL,
            "tradicao": c.get("religion"),
            "nacao": c.get("nation"),
            "linha_religiosa": c.get("matrixLineage"),
            "categoria": categoria,
            "ano_fundacao": c.get("foundationYear"),
            "membros_declarados": c.get("membersCount"),
            # endereço completo, nome do dirigente e contatos ficam só no payload bruto (local),
            # conforme a política de privacidade do projeto (v4.7)
            "localidade": localidade,
            "geo_status": status,
            "coord_origin": "axes_unb",
            "plataforma_id": c.get("id"),
            "criado_em": c.get("createdAt"),
            "versao": "v5_staging",
        }
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]} if lat else None,
            "properties": props,
        })
        rows.append({
            "entity_id": props["entity_id"], "nome": nome, "uf": "DF", "municipio": muni,
            "localidade": localidade, "tradicao": props["tradicao"], "nacao": props["nacao"],
            "linhagem": props["linha_religiosa"],
            "ano_fundacao": props["ano_fundacao"], "membros_declarados": props["membros_declarados"],
            "publica_contato": bool(c.get("phone") or c.get("email") or c.get("websiteOrSocialMedia")),
            "tem_historia_fundacao": bool(c.get("foundationHistory")),
            "tem_projetos_sociais": bool(c.get("socialProjects")),
            "categoria": categoria, "lat": lat, "lon": lon, "geo_status": status,
        })

    json.dump(cache, open(cache_path, "w"), ensure_ascii=False, indent=1)
    json.dump({"type": "FeatureCollection", "features": feats},
              open(os.path.join(OUT, "axes_unb.geojson"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "axes_unb.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"AXÉS/UnB: {len(rows)} comunidades | geocodificadas: "
          f"{sum(1 for r in rows if r['lat'])} | status: "
          f"{sorted({r['geo_status'] for r in rows})}")


if __name__ == "__main__":
    main()
