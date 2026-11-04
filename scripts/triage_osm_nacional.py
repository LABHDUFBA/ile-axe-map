#!/usr/bin/env python3
"""Triagem auditável da coleta OSM nacional, sem alterar a v4."""
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OSM = BASE / "data" / "osm_nacional" / "osm_nacional.geojson"
V4 = BASE / "data" / "v4" / "terreiros_nacional_v4.geojson"
OUT = BASE / "data" / "osm_nacional" / "triagem"
OUT.mkdir(exist_ok=True)

CORE = re.compile(r"\b(candombl\w*|umbanda|terreiro|il[eê]\s+ax[eé]|tambor\s+de\s+min[áa]|babalorix\w*|ialorix\w*|quimbanda|\bnzo\b)\b", re.I)
AFRO_RELIGION = re.compile(r"afro|matriz|candombl|umbanda|tambor|africana|spiritualist", re.I)
NEGATIVE = re.compile(r"\b(rua|ladeira|avenida|estrada|artigos|loja|store|restaurante|bar|pub|feder[aã]ç[aã]o|associa[cç][aã]o)\b", re.I)


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def hav(a, b, c, d):
    R = 6371000
    p1, p2 = math.radians(a), math.radians(c)
    x = math.sin((p2-p1)/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(math.radians(d-b)/2)**2
    return 2*R*math.asin(math.sqrt(x))


def main():
    osm = json.loads(OSM.read_text(encoding="utf-8"))["features"]
    v4 = json.loads(V4.read_text(encoding="utf-8"))["features"]
    vnames = {norm(f["properties"].get("nome")) for f in v4}
    grid = defaultdict(list)
    for f in v4:
        lon, lat = f["geometry"]["coordinates"]
        grid[(round(lat, 2), round(lon, 2))].append((lat, lon))

    def near_v4(f):
        lon, lat = f["geometry"]["coordinates"]
        for la in (round(lat,2)-.01, round(lat,2), round(lat,2)+.01):
            for lo in (round(lon,2)-.01, round(lon,2), round(lon,2)+.01):
                for glat, glon in grid.get((round(la,2),round(lo,2)),[]):
                    if hav(lat,lon,glat,glon) <= 500:
                        return True
        return False

    out, stats = [], Counter()
    for f in osm:
        p = f["properties"]
        name = p.get("nome") or ""
        amenity, religion = p.get("amenity") or "", p.get("religion") or ""
        core, rel, neg = bool(CORE.search(name)), bool(AFRO_RELIGION.search(religion)), bool(NEGATIVE.search(name))
        duplicate = norm(name) in vnames or near_v4(f)
        # Topônimos, lojas e federações não viram duplicatas por mera proximidade.
        if neg and not rel:
            tier = "nao_terreiro_ou_insuficiente"
        elif duplicate:
            tier = "ja_na_v4"
        elif rel or (amenity == "place_of_worship" and core and not neg):
            tier = "provavel_terreiro"
        elif core and not neg:
            tier = "revisar_natureza"
        else:
            tier = "nao_terreiro_ou_insuficiente"
        stats[tier] += 1
        q = {"type":"Feature", "geometry":f["geometry"], "properties":{**p, "tier":tier, "evidencia":{"nome_religioso":core,"tag_religion":religion or None,"amenity":amenity or None,"possivel_duplicata_v4":duplicate}}}
        out.append(q)

    (OUT / "osm_nacional_triagem.geojson").write_text(json.dumps({"type":"FeatureCollection","features":out},ensure_ascii=False),encoding="utf-8")
    audit={"total_osm":len(osm),"tiers":dict(stats),"metodo":"provável = tag religion afro/matriz ou amenity=place_of_worship com nome religioso; duplicata = mesmo nome ou <=500 m da v4. Não incorporado automaticamente.","nota":"OSM é ODbL; crédito OpenStreetMap contributors obrigatório caso incorporado."}
    (OUT / "auditoria_triagem.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(audit,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
