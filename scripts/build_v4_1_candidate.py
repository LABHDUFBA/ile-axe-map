#!/usr/bin/env python3
"""Gera a v4.1 CANDIDATA sem modificar a v4 publicada.

Adições estritas:
- OSM: tier=provavel_terreiro, não duplicado espacial/nominalmente na v4.
- CNPJ: candidato de alta confiança, Nominatim house/place_of_worship/apartments,
  UF coerente e a >=500 m da v4. Sem CNPJ, contato ou endereço na saída.

Saída pública sanitizada em data/v4_1/. A cache CNPJ privada nunca é publicada.
"""
import json, math, re, sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
D = BASE / "data"
OUT = D / "v4_1"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(Path(__file__).parent))
from build_unified_v4 import norm
from build_nacional_v3 import UF_BBOX

RADIUS = 500.0
STRONG_PRECISION = {"house", "place_of_worship", "apartments"}

def hav(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2-p1)/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(math.radians(lon2-lon1)/2)**2
    return 2*R*math.asin(math.sqrt(a))

def grid_index(features):
    g = defaultdict(list)
    for f in features:
        lon, lat = f["geometry"]["coordinates"]
        g[(round(lat,2),round(lon,2))].append(f)
    return g

def near(feature, grid, radius=RADIUS):
    lon, lat = feature["geometry"]["coordinates"]
    for la in (round(lat,2)-.01, round(lat,2), round(lat,2)+.01):
        for lo in (round(lon,2)-.01, round(lon,2), round(lon,2)+.01):
            for f in grid.get((round(la,2),round(lo,2)),[]):
                flon, flat = f["geometry"]["coordinates"]
                if hav(lat,lon,flat,flon) < radius:
                    return True
    return False

def in_declared_uf(lat, lon, uf):
    bb = UF_BBOX.get(uf)
    return not bb or (bb[0] <= lon <= bb[1] and bb[2] <= lat <= bb[3])

def candidate_feature(name, lon, lat, uf, source, status, precision=None):
    return {"type":"Feature", "geometry":{"type":"Point","coordinates":[lon,lat]}, "properties":{
        "nome":name, "municipio":"", "uf":uf, "fontes":[source], "num_fontes":1,
        "coord_origin":source, "fonte_label":"OpenStreetMap" if source=="osm" else "CNPJ/Receita Federal",
        "geo_status":status, "nacao":None, "categoria":"Não informado",
        "geocode_precision":precision, "versao":"v4.1_candidata",
    }}

def main():
    v4 = json.loads((D/"v4/terreiros_nacional_v4.geojson").read_text(encoding="utf-8"))["features"]
    v4_names = {norm(f["properties"].get("nome")) for f in v4}
    existing_grid = grid_index(v4)
    selected, audit = [], {"base_v4":len(v4), "osm":{}, "cnpj":{}}

    # OSM: requer evidência religiosa direta ou local de culto + nome inequívoco.
    # Metadados conflitantes (ex. muslim/hindu/buddhist) e nomes comerciais não entram.
    osm = json.loads((D/"osm_nacional/triagem/osm_nacional_triagem.geojson").read_text(encoding="utf-8"))["features"]
    osm_high = [f for f in osm if f["properties"].get("tier")=="provavel_terreiro"]
    religion_direct = re.compile(r"(umbanda|candomble|afro|matriz|tambor|jurema)", re.I)
    name_religious = re.compile(r"\b(umbanda|candomble|terreiro|ile axe|ile ase|tenda|quimbanda|mina|jurema|abassa)\b", re.I)
    commercial_name = re.compile(r"\b(artigos|bazar|flora|consultorio|altar)\b", re.I)
    conflicting_religions = {"muslim", "hindu", "buddhist", "christian", "jewish"}
    osm_rejected = Counter()
    for f in osm_high:
        p=f["properties"]; name=p.get("nome") or ""
        religion = norm(p.get("religion") or "")
        worship = p.get("amenity") == "place_of_worship"
        if religion in conflicting_religions:
            osm_rejected["religiao_osm_conflitante"] += 1; continue
        if commercial_name.search(name):
            osm_rejected["nome_comercial_ou_altar"] += 1; continue
        if not (religion_direct.search(religion) or (worship and name_religious.search(norm(name)))):
            osm_rejected["evidencia_osm_insuficiente"] += 1; continue
        if norm(name) in v4_names or near(f, existing_grid):
            osm_rejected["duplicata_v4"] += 1; continue
        lon, lat = f["geometry"]["coordinates"]
        out=candidate_feature(name, lon, lat, p.get("uf") or "", "osm", "fonte_osm_alta_confianca")
        # dedupe intra-lote: mesmo nome ou <=500 m
        selgrid=grid_index(selected)
        if norm(name) in {norm(x["properties"]["nome"]) for x in selected} or near(out, selgrid):
            osm_rejected["duplicata_interna"] += 1; continue
        selected.append(out)
    audit["osm"]={"provaveis_entrada":len(osm_high),"adicionados":len(selected),"rejeitados":dict(osm_rejected)}

    # CNPJ, cache privado local. A saída não inclui CNPJ, query nem endereço.
    cache_path=D/"cnpj_nacional/geocoding_v41/cache_privado.jsonl"
    cnpj=[json.loads(line) for line in cache_path.open(encoding="utf-8")]
    cnpj_input=0; cnpj_add=0; bad_uf=0; dedup=0
    selected_grid=grid_index(selected)
    selected_names={norm(x["properties"]["nome"]) for x in selected}
    for r in cnpj:
        if r.get("lat") is None or r.get("precision") not in STRONG_PRECISION:
            continue
        cnpj_input += 1
        lat,lon=r["lat"],r["lon"]
        if not in_declared_uf(lat,lon,r.get("uf")):
            bad_uf += 1; continue
        f=candidate_feature(r["nome"],lon,lat,r.get("uf") or "","receita_federal_cnpj","geocodificado_endereco_alta_confianca",r.get("precision"))
        if norm(r["nome"]) in v4_names or near(f,existing_grid) or norm(r["nome"]) in selected_names or near(f,selected_grid):
            dedup += 1; continue
        selected.append(f); cnpj_add += 1
        selected_names.add(norm(r["nome"])); selected_grid=grid_index(selected)
    audit["cnpj"]={"precision_forte_entrada":cnpj_input,"adicionados":cnpj_add,"uf_divergente":bad_uf,"rejeitados_por_dedupe_espacial_ou_nominal":dedup}

    all_features=v4+selected
    result={"type":"FeatureCollection","features":all_features}
    (OUT/"terreiros_nacional_v4_1.geojson").write_text(json.dumps(result,ensure_ascii=False),encoding="utf-8")
    audit.update({"total_v4_1":len(all_features),"novas_entidades":len(selected),"por_fonte_nova":dict(Counter(f["properties"]["coord_origin"] for f in selected)),"nota":"v4.1: CNPJ sem CNPJ/endereço/contato. Demais CNPJ e OSM aguardam revisão."})
    (OUT/"auditoria_v4_1.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(audit,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
