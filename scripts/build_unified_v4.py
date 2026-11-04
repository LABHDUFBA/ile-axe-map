#!/usr/bin/env python3
"""
build_unified_v4.py — Unificação cuidadosa das fontes republicáveis do Ilê Axé Map.

MODELO: entidade ↔ ocorrência.
- Entidade: o terreiro real, com entity_id estável (hash do nome normalizado + UF).
- Ocorrência: um registro por fonte, preservando TODOS os campos originais.
- Nenhuma ocorrência é descartada; merges são reversíveis (basta reler as fontes).

ENTITY RESOLUTION (conservador):
- match: nome normalizado idêntico E (município/UF iguais OU coordenadas < 500 m).
- AxéCloud: apenas flag de evidência (match_axecloud por entidade), nunca fonte.

PRIORIDADE DE COORDENADA para o ponto da entidade:
herdado_v2/CEAO > google_places > nominatim/cnpj > sefaz > nenhuma.

SAÍDAS (tudo lado a lado, NÃO substitui v3):
- data/v4/entities.jsonl       — uma entidade por linha
- data/v4/occurrences.jsonl    — todas as ocorrências com entity_id
- data/v4/terreiros_nacional_v4.geojson — entidades com coordenada (candidata a base)
- data/v4/auditoria_v4.json    — relatório completo

Uso: python3 scripts/build_unified_v4.py
"""
import csv
import hashlib
import json
import math
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
D = BASE / "data"
OUT = D / "v4"

RAIO_M = 500.0

# prioridade de coordenada (menor = melhor)
COORD_PRIORITY = {
    "v2_validado": 0,
    "herdado_v2_validado": 0, "herdado_v2_centroide_substituido": 0,
    "ceao": 1, "google_places": 2, "google": 2, "ceap": 3, "osm": 3,
    "nominatim_fixed": 4, "nominatim": 4, "csv": 5, "sefaz": 6,
}
# prioridade para o "melhor nome" da entidade
NOME_PRIORITY = {"ceao": 0, "google_places": 1, "google": 1, "ceap": 2, "osm": 3,
                 "terreirosdobrasil": 4, "receita_federal_cnpj": 5, "csv": 6, "nominatim": 6, "sefaz": 7, "v2_validado": 0}


def norm(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def norm_key(s):
    return hashlib.sha1(norm(s).encode()).hexdigest()[:12]


def hav_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def load_v3():
    feats = json.loads((D / "terreiros_nacional_v3.geojson").read_text(encoding="utf-8"))["features"]
    occs = []
    for f in feats:
        p = f["properties"]
        fl = str(p.get("fonte_label") or "")
        fonte = {
            "CNPJ": "receita_federal_cnpj", "CEAO/UFBA": "ceao",
            "Google Places": "google_places", "Outro": "mapeando_axe_csv",
        }.get(fl, "mapeando_axe_csv")
        # geo_source indica nominatim quando veio de regeocodificação
        gs = str(p.get("geo_source") or "")
        occ = {
            "fonte": fonte,
            "nome": p.get("nome"),
            "municipio": p.get("municipio") or "",
            "uf": p.get("uf") or "",
            "lon": f["geometry"]["coordinates"][0] if f.get("geometry") else None,
            "lat": f["geometry"]["coordinates"][1] if f.get("geometry") else None,
            "geo_status": p.get("geo_status"),
            "coord_origin": ("herdado_v2" if "herdado" in str(p.get("geo_status")) else fonte or gs),
            "origem_registro": "v3",
            "id_registro": p.get("entity_id"),
            "nacao": p.get("nacao"),
            "categoria": p.get("categoria"),
            "endereco": p.get("endereco"),
            "cep": p.get("cep"),
        }
        occs.append(occ)
    return occs


def load_v2():
    """Base BA v2.2 validada — a fonte com maior prioridade de coordenada."""
    feats = json.loads((D / "terreiros_v2.geojson").read_text(encoding="utf-8"))["features"]
    occs = []
    for f in feats:
        p = f["properties"]
        fonte = p.get("fonte") or "desconhecida"
        occs.append({
            "fonte": fonte,  # ceao | google | osm | sefaz (labels da v2.2)
            "nome": p.get("nome"),
            "municipio": p.get("municipio") or p.get("bairro") or "",
            "uf": "BA",
            "lon": f["geometry"]["coordinates"][0] if f.get("geometry") else None,
            "lat": f["geometry"]["coordinates"][1] if f.get("geometry") else None,
            "geo_status": "v2_validado",
            "coord_origin": "v2_validado",
            "origem_registro": "v2_2",
            "id_registro": p.get("ceao_id"),
            "nacao": p.get("nacao"),
            "nacao_categoria": p.get("nacao_categoria"),
            "endereco": p.get("endereco"),
            "cep": p.get("cep"),
            "bairro": p.get("bairro"),
        })
    return occs


def load_ceap():
    path = D / "ceap" / "ceap_terreiros.geojson"
    feats = json.loads(path.read_text(encoding="utf-8"))["features"]
    occs = []
    for f in feats:
        p = f["properties"]
        if p.get("pais") != "Brasil":
            occs.append({"fonte": "ceap_diaspora", "nome": p.get("nome"),
                         "municipio": p.get("municipio") or "", "uf": "", "pais": p.get("pais"),
                         "lon": f["geometry"]["coordinates"][0] if f.get("geometry") else None,
                         "lat": f["geometry"]["coordinates"][1] if f.get("geometry") else None,
                         "geo_status": "nao_validado", "coord_origin": "ceap", "origem_registro": "ceap",
                         "id_registro": p.get("id_ceap"), "linha_religiosa": p.get("linha_religiosa"),
                         "endereco": p.get("endereco"), "cep": p.get("cep")})
            continue
        # descarta os 34 que já batem com a v3? NÃO: o entity resolution cuida disso.
        occs.append({
            "fonte": "ceap", "nome": p.get("nome"),
            "municipio": p.get("municipio") or "", "uf": p.get("estado") or "",
            "lon": f["geometry"]["coordinates"][0] if f.get("geometry") else None,
            "lat": f["geometry"]["coordinates"][1] if f.get("geometry") else None,
            "geo_status": "nao_validado", "coord_origin": "ceap", "origem_registro": "ceap",
            "id_registro": p.get("id_ceap"), "linha_religiosa": p.get("linha_religiosa"),
            "endereco": p.get("endereco"), "cep": p.get("cep"),
        })
    return occs


def load_axecloud():
    path = D / "axecloud" / "axecloud_decoded.json"
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    OUT.mkdir(exist_ok=True)
    occs = load_v2() + load_v3() + load_ceap()
    acs = load_axecloud()

    # índice AxéCloud p/ flag de evidência
    acs_by_name = defaultdict(list)
    for a in acs:
        n = norm(a["nome"])
        if n:
            acs_by_name[n].append(a)

    # --- entity resolution ---
    # índice por (nome_norm) -> lista de entidades criadas
    ents_by_name = defaultdict(list)
    entities = []          # dicts completos
    occ_out = []

    def same_place(e, o):
        if e["uf"] and o["uf"] and e["uf"] != o["uf"]:
            return False
        if norm(e["municipio"]) and norm(o["municipio"]):
            if norm(e["municipio"]) == norm(o["municipio"]):
                return True
        # sem município comparável: cai na coordenada
        if e["lat"] is not None and o["lat"] is not None:
            return hav_m(e["lat"], e["lon"], o["lat"], o["lon"]) <= RAIO_M
        return False

    for o in occs:
        n = norm(o["nome"])
        target = None
        for e in ents_by_name.get(n, []):
            if same_place(e, o):
                target = e
                break
        if target is None:
            entity_id = "e_" + norm_key(o["nome"]) + "_" + (o["uf"] or "XX")
            target = {
                "entity_id": entity_id, "nome_norm": n, "nome": o["nome"],
                "municipio": o["municipio"], "uf": o["uf"],
                "lat": o["lat"], "lon": o["lon"],
                "coord_origin": o["coord_origin"], "coord_priority": COORD_PRIORITY.get(o["coord_origin"], 9),
                "fontes": set(),
            }
            entities.append(target)
            ents_by_name[n].append(target)
        # anexa ocorrência
        target["fontes"].add(o["fonte"])
        ro = dict(o)
        ro["entity_id"] = target["entity_id"]
        occ_out.append(ro)
        # atualiza coords se a nova ocorrência tem prioridade melhor
        if o["lat"] is not None:
            pr = COORD_PRIORITY.get(o["coord_origin"], 9)
            if pr < target["coord_priority"]:
                target.update(lat=o["lat"], lon=o["lon"], coord_origin=o["coord_origin"], coord_priority=pr)
            elif target["lat"] is None:
                target.update(lat=o["lat"], lon=o["lon"], coord_origin=o["coord_origin"], coord_priority=pr)
        # atualiza município/uf se vazio
        if not target["municipio"] and o["municipio"]:
            target["municipio"] = o["municipio"]
        if not target["uf"] and o["uf"]:
            target["uf"] = o["uf"]

    # --- flag AxéCloud por entidade (evidência, não fonte) ---
    acs_stats = Counter()
    for e in entities:
        cands = acs_by_name.get(e["nome_norm"], [])
        if not cands:
            e["match_axecloud"] = "nao_encontrado"
            acs_stats["nao_encontrado"] += 1
            continue
        if e["lat"] is not None:
            dmin = min(hav_m(e["lat"], e["lon"], a["lat"], a["lng"]) for a in cands)
            if dmin <= RAIO_M:
                e["match_axecloud"] = "corroborado"
                e["axecloud_dist_m"] = round(dmin, 1)
                acs_stats["corroborado"] += 1
                continue
        e["match_axecloud"] = "nome_existe_local_divergente"
        acs_stats["nome_divergente"] += 1

    # --- saídas ---
    multi = sum(1 for e in entities if len(e["fontes"]) > 1)
    com_coords = sum(1 for e in entities if e["lat"] is not None)

    # --- item 1: SINALIZAÇÃO geo_status por entidade ---
    # herda a pior evidência entre as ocorrências da entidade:
    #   herdado_v2/v2_validado (coords da base validada) > centroide_suspeito/uf_divergente
    occ_by_ent = defaultdict(list)
    for o in occ_out:
        occ_by_ent[o["entity_id"]].append(o)

    def entity_geo_status(e):
        occs_e = occ_by_ent.get(e["entity_id"], [])
        statuses = [str(o.get("geo_status") or "") for o in occs_e]
        if any("centroide_suspeito" in s for s in statuses):
            return "centroide_suspeito"
        if any("uf_divergente" in s for s in statuses):
            return "uf_divergente"
        if any("herdado_v2" in s or "v2_validado" in s for s in statuses):
            return "herdado_v2_validado"
        if e["coord_origin"] in ("v2_validado",):
            return "herdado_v2_validado"
        return "fonte_propria_" + (e["coord_origin"] or "desconhecida")

    for e in entities:
        e["geo_status"] = entity_geo_status(e)

    # --- campos de exibição: herda da melhor ocorrência (prioridade de fonte) ---
    FIELDS = ["nacao", "categoria", "endereco", "cep", "telefone", "linha_religiosa", "bairro", "nacao_categoria"]
    for e in entities:
        occs_e = sorted(occ_by_ent.get(e["entity_id"], []),
                        key=lambda o: NOME_PRIORITY.get(o["fonte"], 9))
        for f in FIELDS:
            for o in occs_e:
                if o.get(f) and str(o.get(f)).strip() and "revisar" not in str(o.get(f))[:20]:
                    e[f] = o[f]
                    break
        # fonte_label para exibição
        LABELS = {"ceao": "CEAO/UFBA", "google": "Google Places", "google_places": "Google Places",
                  "osm": "OSM", "sefaz": "SEFAZ/Salvador", "receita_federal_cnpj": "CNPJ/Receita Federal",
                  "mapeando_axe_csv": "Mapeando Axé (CSV)", "ceap": "CEAP/Mapa do Axé"}
        e["fonte_label"] = LABELS.get(e["coord_origin"], e["coord_origin"])
        if not e.get("categoria") and not e.get("nacao"):
            e["categoria"] = "Não informado"

    # --- item 2: EXCLUSÕES CURADAS por entidade ---
    excl = list(csv.DictReader((D / "exclusoes_curadas.csv").open(encoding="utf-8"))) if (D / "exclusoes_curadas.csv").exists() else []
    excl_names = {norm(r["nome"]) for r in excl if r.get("nome")}
    entities_out, removed_curadas, removed_diaspora = [], [], []
    for e in entities:
        if e["nome_norm"] in excl_names:
            removed_curadas.append(e["nome"])
            continue
        # item 2b: DIÁSPORA — Leo decidiu NÃO usar (04/11/2026)
        if "ceap_diaspora" in e["fontes"] or (e["lat"] is not None and not (-74 <= e["lon"] <= -30 and -34 <= e["lat"] <= 6)):
            removed_diaspora.append(e["nome"])
            continue
        entities_out.append(e)
    entities = entities_out

    # recontabiliza após as remoções
    multi = sum(1 for e in entities if len(e["fontes"]) > 1)
    com_coords = sum(1 for e in entities if e["lat"] is not None)

    with open(OUT / "entities.jsonl", "w", encoding="utf-8") as f:
        for e in entities:
            d = dict(e)
            d["fontes"] = sorted(e["fontes"])
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    with open(OUT / "occurrences.jsonl", "w", encoding="utf-8") as f:
        for o in occ_out:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")

    feats = []
    for e in entities:
        if e["lat"] is None:
            continue
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [e["lon"], e["lat"]]},
            "properties": {
                "entity_id": e["entity_id"], "nome": e["nome"],
                "municipio": e["municipio"], "uf": e["uf"],
                "fontes": sorted(e["fontes"]), "num_fontes": len(e["fontes"]),
                "coord_origin": e["coord_origin"], "geo_status": e["geo_status"],
                "fonte_label": e.get("fonte_label"),
                "nacao": e.get("nacao"), "categoria": e.get("categoria"),
                "endereco": e.get("endereco"), "cep": e.get("cep"),
                "linha_religiosa": e.get("linha_religiosa"),
                "match_axecloud": e["match_axecloud"],
                "versao": "v4",
            },
        })
    (OUT / "terreiros_nacional_v4.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False), encoding="utf-8")

    occ_por_ent_fonte = Counter((o["entity_id"], o["fonte"]) for o in occ_out)
    dup_mesma_fonte = sum(v - 1 for v in occ_por_ent_fonte.values() if v > 1)

    audit = {
        "ocorrencias_duplicadas_mesma_fonte_mesma_entidade": dup_mesma_fonte,
        "versao": "v4",
        "modelo": "entidade ↔ ocorrência; merges conservadores (nome idêntico + município/UF ou <500 m); AxéCloud = flag de evidência, nunca fonte",
        "total_ocorrencias": len(occ_out),
        "total_entidades": len(entities),
        "entidades_multi_fonte": multi,
        "entidades_com_coordenada": com_coords,
        "exclusoes_curadas_aplicadas": len(removed_curadas),
        "exclusoes_exemplos": removed_curadas[:10],
        "removidas_diaspora": len(removed_diaspora),
        "geo_status_entidades": dict(Counter(e["geo_status"] for e in entities)),
        "ocorrencias_por_fonte": dict(Counter(o["fonte"] for o in occ_out)),
        "entidades_por_uf": dict(Counter(e["uf"] or "?" for e in entities).most_common(30)),
        "flag_axecloud": dict(acs_stats),
        "nota": "v4: site único nacional; diáspora excluída por decisão de Leonardo (04/11/2026); exclusões curadas aplicadas por entidade.",
    }
    (OUT / "auditoria_v4.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())