#!/usr/bin/env python3
"""Re-geocodificação dos registros problemáticos da v4.2 (Google Geocoding + Places API).

Ondas:
  1. Mapeando Axé (CSV) com coordenada >60 km do centróide do município declarado
     (concentrado em PE). Entrada: nome + município + UF.
  2. Registros `coordenada_agua` (v4.2). Entrada: nome + município + UF.
  3. (futura) CNPJ sem município validado. Entrada: endereço via cache local.

Método:
  a. Places API (New) Text Search: "nome, município, UF" — melhor para
     terreiros conhecidos (retorna o place real, não o endereço textual).
  b. Fallback Geocoding API: "nome, município, UF".
  c. Validação: resultado deve ficar a <=60 km do centróide IBGE do município
     declarado (mesma régua da auditoria). Fora disso → rejeitado.
  d. Cache local em data/geocode_cache_v43.json (chave = query) — nunca reconsulta.
  e. Rate: máx. 50 req/s (limite padrão), com pausa de 120 ms entre chamadas
     (~8/s, seguro). 174+166 chamadas ≈ 40 s.

Saídas (candidata v4.3, NADA publicado direto):
  data/v4_3/terreiros_nacional_v4_3.geojson      (candidata sanitizada)
  data/v4_3/auditoria_v4_3.json                  (contagens por onda/resultado)
  data/v4_3/regeocode_resultados.csv             (público: nome, coords novas, fonte do match)
  data/geocode_cache_v43.json                    (cache gitignored)

Uso:
  export GMAPS_API_KEY=...   # NUNCA commitada
  python3 scripts/regeocode_v43.py --ondas 1,2
"""
import argparse
import json
import math
import os
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

CACHE_PATH = Path("data/geocode_cache_v43.json")
OUT_DIR = Path("data/v4_3")
SRC = Path("data/v4_2/terreiros_nacional_v4_2.geojson")
MUN_PATH = Path("data/v4_2/municipios_coords.json")
AUDIT_MUN_PATH = Path("data/v4_2/audit_mun_far.json")
MAX_DIST_KM = 60.0
PAUSE_S = 0.12


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn")


def dist_km(lat1, lon1, lat2, lon2):
    dlat = (lat1 - lat2) * 111.32
    dlon = (lon1 - lon2) * 111.32 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dlat, dlon)


def load_municipios():
    muns = {}
    for k, v in json.loads(MUN_PATH.read_text()).items():
        nome, uf = k.split("|")
        muns[(nome, uf)] = (float(v[0]), float(v[1]))
    return muns


def places_search(key, query):
    req = urllib.request.Request(
        f"https://places.googleapis.com/v1/places:searchText?key={key}",
        data=json.dumps({"textQuery": query, "languageCode": "pt-BR",
                         "maxResultCount": 1}).encode(),
        headers={"Content-Type": "application/json",
                 "X-Goog-FieldMask": "places.displayName,places.location,places.formattedAddress",
                 "User-Agent": "ile-axe-map-audit/1.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.load(r)
    ps = d.get("places", [])
    if not ps:
        return None
    p = ps[0]
    loc = p.get("location")
    if not loc:
        return None
    return {"lat": float(loc["latitude"]), "lng": float(loc["longitude"]),
            "nome": p.get("displayName", {}).get("text", ""),
            "addr": p.get("formattedAddress", "")}


def geocode(key, query):
    url = ("https://maps.googleapis.com/maps/api/geocode/json?address="
           + urllib.parse.quote(query) + "&key=" + key + "&language=pt-BR&region=br")
    req = urllib.request.Request(url, headers={"User-Agent": "ile-axe-map-audit/1.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.load(r)
    if d.get("status") != "OK" or not d.get("results"):
        return None
    res = d["results"][0]
    loc = res["geometry"]["location"]
    return {"lat": float(loc["lat"]), "lng": float(loc["lng"]),
            "nome": "", "addr": res.get("formatted_address", "")}


def geocode_full(key, query):
    """Geocoding API retornando metadados de qualidade (types, location_type)."""
    url = ("https://maps.googleapis.com/maps/api/geocode/json?address="
           + urllib.parse.quote(query) + "&key=" + key + "&language=pt-BR&region=br")
    req = urllib.request.Request(url, headers={"User-Agent": "ile-axe-map-audit/1.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.load(r)
    if d.get("status") != "OK" or not d.get("results"):
        return None
    res = d["results"][0]
    loc = res["geometry"]["location"]
    return {"lat": float(loc["lat"]), "lng": float(loc["lng"]),
            "nome": "", "addr": res.get("formatted_address", ""),
            "types": res.get("types", []),
            "loc_type": res["geometry"].get("location_type", ""),
            "partial_match": bool(res.get("partial_match", False))}


def quality(r):
    """'forte' = endereço de rua/estabelecimento (ROOFTOP, RANGE_INTERPOLATED,
    ou GEOMETRIC_CENTER de establishment/place_of_worship); 'fraca' = centróide
    genérico (locality/APPROXIMATE) — rejeitado para não recriar pilhas."""
    if not r:
        return "none"
    lt, ty = r.get("loc_type", ""), set(r.get("types", []))
    # Sem Place ID, Geocoding só é evidência suficiente quando o resultado
    # NÃO é parcial e a própria taxonomia do Google o reconhece como culto.
    # ROOFTOP isolado é insuficiente: pode ser restaurante, loja ou rua com
    # tokens parecidos no nome (falha empiricamente observada no dry-run).
    if not r.get("partial_match", False) and "place_of_worship" in ty and lt in ("ROOFTOP", "GEOMETRIC_CENTER"):
        return "forte"
    return "fraca"


def resolve(key, cache, query):
    """Geocoding API com gate de qualidade: só ROOFTOP/RANGE_INTERPOLATED ou
    GEOMETRIC_CENTER de establishment/place_of_worship contam como hit.
    Resultados genéricos (locality/APPROXIMATE) são rejeitados — recriariam
    o problema de centróide que a auditoria detectou."""
    if query in cache:
        return cache[query]
    hit, source = None, None
    try:
        raw = geocode_full(key, query)
        if raw and quality(raw) == "forte":
            hit = {"lat": raw["lat"], "lng": raw["lng"], "nome": "", "addr": raw["addr"]}
            source = "geocoding_api"
    except Exception:
        hit = None
    time.sleep(PAUSE_S)
    cache[query] = (hit, source)
    return hit, source


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ondas", default="1,2")
    ap.add_argument("--dry-run", action="store_true", help="consulta mas nao escreve candidata")
    args = ap.parse_args()
    ondas = {int(x) for x in args.ondas.split(",")}

    key = os.environ.get("GMAPS_API_KEY")
    if not key:
        sys.exit("ABORT: defina GMAPS_API_KEY no ambiente; a chave nunca vai no repo.")

    feats = json.loads(SRC.read_text(encoding="utf-8"))["features"]
    muns = load_municipios()
    cache = json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else {}

    # alvo onda 1: Mapeando Axé com >60km do centróide (recomputar da base)
    alvo1 = []
    for i, f in enumerate(feats):
        p = f["properties"]
        if "Mapeando" not in (p.get("fonte_label") or ""):
            continue
        mun = strip_accents((p.get("municipio") or "").strip().lower())
        uf = (p.get("uf") or "").strip().upper()
        if not mun or not uf or (mun, uf) not in muns:
            continue
        lon, lat = f["geometry"]["coordinates"]
        d = dist_km(lat, lon, *muns[(mun, uf)])
        if d > 60:
            alvo1.append(i)

    # alvo onda 2: coordenada_agua
    alvo2 = [i for i, f in enumerate(feats)
             if str(f["properties"].get("geo_status", "")).startswith("coordenada_agua")]

    print(f"alvos — onda 1 (Mapeando Axé >60km): {len(alvo1)} | onda 2 (agua): {len(alvo2)}")

    resultados = {"geocoding_api": 0, "cache": 0}
    rejeitados, sem_resultado, corrigidos = [], [], []
    targets = (alvo1 if 1 in ondas else []) + (alvo2 if 2 in ondas else [])
    # nomes genericos nao podem ser geocodificados por nome (falso match garantido)
    GENERICOS = ("sem nome", "terreiro sem", "casa sem")
    gen = [i for i in targets
           if any(g in (feats[i]["properties"].get("nome") or "").lower() for g in GENERICOS)]
    targets = [i for i in targets
               if not any(g in (feats[i]["properties"].get("nome") or "").lower() for g in GENERICOS)]
    # Genéricos são explicitamente não resolvidos: não podem continuar visíveis
    # só porque não entraram numa chamada de geocoding.
    sem_resultado.extend(gen)
    print(f"pulados por nome generico (marcados nao resolvidos): {len(gen)}")
    for n, i in enumerate(targets):
        p = feats[i]["properties"]
        nome = (p.get("nome") or "").strip()
        mun = (p.get("municipio") or "").strip()
        uf = (p.get("uf") or "").strip().upper()
        if not nome or not mun or not uf:
            sem_resultado.append(i)
            continue
        query = f"{nome}, {mun}, {uf}, Brasil"
        if query in cache:
            hit, source = cache[query]
            resultados["cache"] += 1
        else:
            time.sleep(PAUSE_S)
            hit, source = resolve(key, cache, query)
            source = source or "sem"
            resultados[source] = resultados.get(source, 0) + 1
        # validacao municipal
        mun_key = (strip_accents(mun.lower()), uf)
        status_str = "sem resultado"
        if hit is not None:
            if mun_key in muns:
                d = dist_km(hit["lat"], hit["lng"], *muns[mun_key])
                if d <= MAX_DIST_KM:
                    corrigidos.append((i, hit, source))
                    status_str = "OK " + str(source)
                else:
                    rejeitados.append((i, round(d, 1)))
                    status_str = f"REJ {d:.1f}km do municipio"
            else:
                rejeitados.append((i, None))
                status_str = "REJ municipio desconhecido"
        else:
            sem_resultado.append(i)
        print(f"  [{n+1}/{len(targets)}] {nome[:40]:<40} -> {status_str}")

    # persistir cache sempre (mesmo em dry-run)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False))

    print("\n== resumo ==")
    print(f"corrigidos: {len(corrigidos)} | rejeitados (>60km do municipio): {len(rejeitados)} | sem resultado: {len(sem_resultado)}")
    print("por metodo:", dict(resultados))

    if args.dry_run:
        print("dry-run: candidata NAO escrita; cache salvo.")
        json.dump({"corrigidos": [[i, h, s] for i, h, s in corrigidos],
                   "rejeitados": rejeitados, "sem_resultado": sem_resultado},
                  open("/home/hermes/.hermes/cache/scratch/regeocode_dryrun.json", "w"), ensure_ascii=False)
        return

    # === candidata v4.3 ===
    out_feats = []
    for i, f in enumerate(feats):
        g = {"type": f.get("type", "Feature"), "geometry": dict(f["geometry"]), "properties": dict(f["properties"])}
        out_feats.append(g)
    mudados = 0
    for i, hit, source in corrigidos:
        p = out_feats[i]["properties"]
        p["coord_origin_anterior"] = p.get("coord_origin", "")
        p["geo_status_anterior"] = p.get("geo_status", "")
        p["coord_origin"] = f"regeocode_v43_{source}"
        p["geo_status"] = "regeocode_v43_validado"
        out_feats[i]["geometry"]["coordinates"] = [hit["lng"], hit["lat"]]
        mudados += 1
    # rejeitados/sem resultado da onda 1 ficam ocultos com status explicito
    for i, d in rejeitados:
        p = out_feats[i]["properties"]
        if str(p.get("geo_status", "")).startswith("regeocode"):
            continue
        p["geo_status_anterior"] = p.get("geo_status", "")
        p["geo_status"] = "geocode_divergente"
    for i in sem_resultado:
        p = out_feats[i]["properties"]
        if str(p.get("geo_status", "")).startswith("regeocode"):
            continue
        p["geo_status_anterior"] = p.get("geo_status", "")
        p["geo_status"] = "geocode_nao_resolvido"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = {"type": "FeatureCollection", "features": out_feats}
    (OUT_DIR / "terreiros_nacional_v4_3.geojson").write_text(
        json.dumps(out, ensure_ascii=False), encoding="utf-8")

    audit = {
        "base": "v4.2", "candidata": "v4.3",
        "ondas": sorted(ondas),
        "total": len(out_feats),
        "regeocodificados_validados": mudados,
        "rejeitados_geocode_divergente": len(rejeitados),
        "sem_resultado_nao_resolvido": len(sem_resultado),
        "criterio_validacao_km": MAX_DIST_KM,
        "por_metodo": dict(resultados),
        "nota": "v4.3: Geocoding API do Google com gate estrito: somente partial_match=false, "
                "place_of_worship e ROOFTOP/GEOMETRIC_CENTER, além de validação municipal IBGE (<=60 km). "
                "Corrigidos recebem geo_status=regeocode_v43_validado; demais ficam ocultos como "
                "geocode_nao_resolvido. Nada é apagado; status anterior preservado. Places API (New) "
                "permanece pendente para ampliar a cobertura com Place IDs.",
    }
    (OUT_DIR / "auditoria_v4_3.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    import csv as _csv
    with open(OUT_DIR / "regeocode_resultados.csv", "w", newline="", encoding="utf-8") as fh:
        w = _csv.writer(fh)
        w.writerow(["nome", "municipio", "uf", "nova_lat", "nova_lon", "metodo", "endereco_google"])
        for i, hit, source in corrigidos:
            p = feats[i]["properties"]
            w.writerow([p.get("nome",""), p.get("municipio",""), p.get("uf",""),
                        f"{hit['lat']:.6f}", f"{hit['lng']:.6f}", source, hit.get("addr","")[:100]])
    print(f"\ncandidata v4.3 escrita em {OUT_DIR} ({mudados} corrigidos)")


if __name__ == "__main__":
    main()
