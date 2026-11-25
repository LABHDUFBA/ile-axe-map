#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_v5.py — integra as fontes novas (Atlas do Axé/AM e AXÉS/LHS-UnB/DF) à base
publicada v4.8 e produz a camada v5.

Regras (todas auditáveis em data/v5/auditoria_v5.json):

1. Nada da v4.8 é alterado: os 8.036 registros entram como estão.
2. Deduplicação interna das fontes novas: mesmo nome normalizado + mesmo município
   + distância < 2 km → uma entidade. Casos com nome genérico em bairros distintos
   NÃO são fundidos.
3. Registros cuja categoria é comércio (loja) já vêm excluídos desde a ingestão;
   a plataforma AXÉS (categoria projeto/plataforma) é excluída aqui.
4. Taxonomia: a tradição DECLARADA pela fonte é autoritativa. Nação/linhagem só
   são convertidas para o vocabulário canônico quando compatíveis com a tradição
   declarada; caso contrário, o valor bruto é preservado e marcado para revisão.
   Nada é inferido a partir do nome da casa.
5. Coordenadas ausentes: centróide do município, com geo_status que oculta o ponto
   por padrão ('centroide_municipio_<fonte>').
6. Precisão fraca declarada pela fonte ('aproximada pelo endereço', centróides de
   região administrativa) também fica oculta por padrão.

Uso: python3 scripts/build_v5.py
Saída: data/v5/terreiros_nacional_v5.geojson + data/v5/auditoria_v5.json
"""
import collections
import hashlib
import json
import math
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
from taxonomia_v48 import convert_token, norm, tokens_of  # noqa: E402

BASE = os.path.join(REPO, "data", "v4_8", "terreiros_nacional_v4_8.geojson")
FONTES = {
    "atlas_axe": os.path.join(REPO, "data", "atlas_axe", "atlas_axe.geojson"),
    "axes_unb": os.path.join(REPO, "data", "axes_unb", "axes_unb.geojson"),
}
OUT_DIR = os.path.join(REPO, "data", "v5")

# centróides municipais (Nominatim, 24/11/2026) — usados só quando a fonte não traz coordenada
CENTROIDES = {
    ("Manaus", "AM"): (-3.1316333, -59.9825041),
    ("Brasília", "DF"): (-15.7939869, -47.8828000),
}

# tradição declarada pela fonte → (tradição canônica, tradições adicionais)
# tradição declarada → (principal, adicionais, linhas)
TRAD_DECLARADA = {
    "candomble": ("Candomblé", [], []),
    "umbanda": ("Umbanda", [], []),
    "tambor de mina": ("Tambor de Mina", [], []),
    "umbanda e mina": ("Umbanda", ["Tambor de Mina"], []),
    "umbanda e quimbanda": ("Umbanda", [], ["Quimbanda"]),
    "nao especificado": ("Não especificada", [], []),
    "-": ("Não especificada", [], []),
    "": ("Não especificada", [], []),
}

# geo_status: mapeia o rótulo da fonte para o vocabulário do mapa (e define visibilidade)
STATUS_ATLAS = {
    "alta ponto do google maps": "fonte_declarada_alta",
    "alta": "fonte_declarada_alta",
    "aproximada pelo endereco": "fonte_declarada_aproximada",
    "aproximada": "fonte_declarada_aproximada",
    "baixa 100 m": "fonte_declarada_baixa",
    "baixa aprox 100 m": "fonte_declarada_baixa",
    "baixa": "fonte_declarada_baixa",
}


def hav(a, b, c, d):
    R = 6371000.0
    p = math.radians
    dlat, dlon = p(c - a), p(d - b)
    x = math.sin(dlat / 2) ** 2 + math.cos(p(a)) * math.cos(p(c)) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def coords(f):
    if not f.get("geometry"):
        return None
    return f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0]


def entity_id(nome, uf):
    return "e_" + hashlib.sha1(f"{norm(nome)}|{uf}".encode()).hexdigest()[:12] + "_" + uf


def taxonomia(trad_decl, nacao_decl):
    """Converte o que a fonte declara para o esquema v4.8, sem inferência."""
    chave = norm(trad_decl)
    principal, adicionais, linhas_decl = TRAD_DECLARADA.get(chave, (None, [], []))
    revisar = []
    if principal is None:
        principal, adicionais, linhas_decl = "Não especificada", [], []
        revisar.append(trad_decl)
    aceitas = {principal, *adicionais}
    nacoes, linhas, raiz = [], list(linhas_decl), None
    for decl in (nacao_decl,):
        if not decl:
            continue
        for tok in tokens_of(decl):
            d = convert_token(tok)
            if d["acao"] == "revisar":
                revisar.append(tok)
                continue
            if d["trad"] is not None and d["trad"] not in aceitas:
                revisar.append(tok)          # ex.: "Congo" numa casa de Tambor de Mina
                continue
            for x in d["nacoes"]:
                if x not in nacoes:
                    nacoes.append(x)
            for x in d["linhas"]:
                if x not in linhas:
                    linhas.append(x)
            raiz = raiz or d["raiz"]
    return {
        "tradicao": principal,
        "tradicoes_adicionais": adicionais,
        "nacoes": nacoes,
        "linhas": linhas,
        "raiz": raiz,
        "pratica": None,
        "cruzamento": bool(adicionais),
        "revisar": revisar,
    }


def dedupe_interno(feats, fonte):
    """Funde registros da MESMA fonte com nome idêntico e coordenadas próximas."""
    grupos = collections.defaultdict(list)
    for f in feats:
        p = f["properties"]
        grupos[(norm(p["nome"]), p.get("municipio"))].append(f)
    mantidos, fundidos = [], []
    for _, grupo in grupos.items():
        if len(grupo) == 1:
            mantidos.append(grupo[0])
            continue
        # ordena: com geometria primeiro, depois mais campos preenchidos
        grupo.sort(key=lambda f: (f["geometry"] is None, -sum(1 for v in f["properties"].values() if v)))
        base = grupo[0]
        for outro in grupo[1:]:
            cb, co = coords(base), coords(outro)
            dist = hav(*cb, *co) if cb and co else None
            if dist is not None and dist < 2000:
                fundidos.append({
                    "fonte": fonte, "mantido": base["properties"]["nome"],
                    "fundido": outro["properties"]["nome"], "dist_m": int(dist),
                })
            else:
                mantidos.append(outro)  # nome genérico em outro ponto: é outra casa
    return mantidos, fundidos


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    base = json.load(open(BASE, encoding="utf-8"))["features"]
    novos, auditoria = [], {"gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "base": {"arquivo": "v4_8", "n": len(base)}, "fontes": {}}

    for fonte, path in FONTES.items():
        feats = json.load(open(path, encoding="utf-8"))["features"]
        excluidos, mantidos, fundidos = [], [], []
        for f in feats:
            cat = norm(f["properties"].get("categoria"))
            if cat.startswith("projeto") or cat.startswith("plataforma"):
                excluidos.append({"nome": f["properties"]["nome"], "motivo": "categoria " + cat})
                continue
            mantidos.append(f)
        mantidos, fundidos = dedupe_interno(mantidos, fonte)

        convertidos = []
        for f in mantidos:
            p = f["properties"]
            uf, muni = p.get("uf"), p.get("municipio")
            t = taxonomia(p.get("tradicao"), p.get("nacao"))
            lat, lon = (coords(f) or (None, None))
            status = STATUS_ATLAS.get(norm(p.get("geo_status")), None)  # chaves já normalizadas abaixo
            if lat is None:
                centro = CENTROIDES.get((muni, uf))
                if centro:
                    lat, lon = centro
                    status = f"centroide_municipio_{fonte}"
                else:
                    status = f"sem_coordenada_{fonte}"
            if status is None:  # AXÉS: centroides de região administrativa, endereço etc.
                gs = norm(p.get("geo_status"))
                if gs.startswith("centroide"):
                    status = "centroide_suspeito_axes"
                elif gs.startswith("sem_coordenada"):
                    status = "centroide_suspeito_axes"
                else:
                    status = "fonte_declarada_endereco"
            props = {
                "entity_id": entity_id(p["nome"], uf),
                "nome": p["nome"],
                "municipio": muni,
                "uf": uf,
                "fontes": p.get("fontes") or [fonte],
                "num_fontes": 1,
                "coord_origin": fonte,
                "geo_status": status,
                "fonte_label": p.get("fonte_label"),
                "nacao": p.get("nacao") or None,
                "categoria": p.get("categoria"),
                "linha_religiosa": p.get("tradicao"),
                "match_axecloud": "nao_avaliado",
                "versao": "v5",
                "foto_thumb": None,
                "ano_fundacao": (str(p.get("ano_fundacao")) if p.get("ano_fundacao") else None),
                "regente": None,
                "tradicao": t["tradicao"],
                "tradicoes_adicionais": t["tradicoes_adicionais"],
                "nacoes": t["nacoes"],
                "raiz": t["raiz"],
                "linhas": t["linhas"],
                "pratica": t["pratica"],
                "cruzamento": t["cruzamento"],
                "classificacao_origem": "fonte_declarada_v5",
                "fonte_atualizado_em": p.get("fonte_atualizado_em"),
                "nacao_revisar": t["revisar"] or None,
            }
            if p.get("bairro"):
                props["bairro"] = p["bairro"]
            if p.get("localidade"):
                props["localidade"] = p["localidade"]
            convertidos.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]} if lat is not None else None,
                "properties": props,
            })

        novos.extend(convertidos)
        auditoria["fontes"][fonte] = {
            "entrada": len(feats),
            "excluidos": excluidos,
            "fundidos": fundidos,
            "publicados": len(convertidos),
            "por_status": dict(collections.Counter(c["properties"]["geo_status"] for c in convertidos)),
            "por_tradicao": dict(collections.Counter(c["properties"]["tradicao"] for c in convertidos)),
            "por_uf": dict(collections.Counter(c["properties"]["uf"] for c in convertidos)),
            "com_coordenada": sum(1 for c in convertidos if c["geometry"]),
            "revisar_nacao": dict(collections.Counter(
                tok for c in convertidos for tok in (c["properties"].get("nacao_revisar") or []))),
        }

    sem_geo = [c["properties"]["nome"] for c in novos if c["geometry"] is None]
    camada = {"type": "FeatureCollection", "features": base + novos}
    json.dump(camada, open(os.path.join(OUT_DIR, "terreiros_nacional_v5.geojson"), "w",
                           encoding="utf-8"), ensure_ascii=False)
    auditoria["total"] = {
        "v4_8": len(base), "novos": len(novos), "camada_v5": len(camada["features"]),
        "sem_geometria": sem_geo,
        "por_uf_novos": dict(collections.Counter(c["properties"]["uf"] for c in novos)),
        "por_fonte": {f: auditoria["fontes"][f]["publicados"] for f in auditoria["fontes"]},
    }
    json.dump(auditoria, open(os.path.join(OUT_DIR, "auditoria_v5.json"), "w",
                              encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"v4.8 {len(base)} + novos {len(novos)} = {len(camada['features'])} entidades")
    for fonte, a in auditoria["fontes"].items():
        print(f"  {fonte}: entrada {a['entrada']} | excluídos {len(a['excluidos'])} | "
              f"fundidos {len(a['fundidos'])} | publicados {a['publicados']} | "
              f"status {a['por_status']}")


if __name__ == "__main__":
    main()
