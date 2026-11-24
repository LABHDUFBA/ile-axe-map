#!/usr/bin/env python3
"""
ingest_atlas_axe.py — coleta e normaliza o "Atlas do Axé" (Amazonas).

Fonte: https://atlasdoaxe.lovable.app/  (app TanStack Start publicando dados via
server function GET /_serverFn/<hash>, formato de serialização próprio: t0/t1/t2
escalares, t9 array, t10 objeto, t11 referência).

Saídas (data/atlas_axe/):
  raw_payload.json   resposta crua da server function (fidelidade)
  casas.json         lista decodificada das 177 casas
  atlas_axe.geojson  camada normalizada no esquema do Ilê Axé Map (v5 staging)
  README.md          proveniência, limites e regras de publicação

Uso: python3 scripts/ingest_atlas_axe.py [--from-cache]
"""
import json
import os
import re
import sys
import unicodedata
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "atlas_axe")
BASE = "https://atlasdoaxe.lovable.app"
SERVER_FN = "/_serverFn/1465697dfd8c8cb40d565648cbc66d2d3a8c4e398eb8d504d9e573abf898aa5b"
FONTE_LABEL = "Atlas do Axé (AM)"
FONTE_URL = "https://atlasdoaxe.lovable.app/"

# Categorias excluídas da camada normalizada (decisão de 24/11/2026: o mapa é de casas de axé,
# não de comércio religioso). Os registros seguem no payload bruto, recuperáveis.
EXCLUIR_CATEGORIAS = ("loja de artigos",)


def fetch_payload():
    req = urllib.request.Request(
        BASE + SERVER_FN,
        headers={
            "x-tsr-serverFn": "true",
            "Accept": "application/json",
            "Origin": BASE,
            "Referer": BASE + "/casas",
            "User-Agent": "IleAxeMap/1.0 (pesquisa academica LABHDUFBA)",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8")


def decode(o, memo=None):
    """Decodifica o formato de serialização do TanStack Start."""
    if memo is None:
        memo = {}

    def walk(node):
        if isinstance(node, list):
            return [walk(x) for x in node]
        if not isinstance(node, dict) or "t" not in node:
            return node
        t = node.get("t")
        i = node.get("i")
        if t == 9:
            val = [walk(x) for x in node.get("a", [])]
        elif t == 10:
            p = node.get("p") or {}
            val = {k: walk(v) for k, v in zip(p.get("k", []), p.get("v", []))}
        elif t == 11:
            val = memo.get(node.get("o"))
        elif t in (0, 1, 2):
            val = node.get("s")
        else:
            raise ValueError(f"tipo de serialização desconhecido: {t}")
        if i is not None:
            memo[i] = val
        return val

    return walk(o)


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def entity_id(nome, municipio, uf):
    import hashlib
    key = f"{norm(nome)}|{norm(municipio)}|{uf}"
    return "atlas_" + hashlib.sha1(key.encode()).hexdigest()[:12]


def main():
    os.makedirs(OUT, exist_ok=True)
    raw_path = os.path.join(OUT, "raw_payload.json")
    if "--from-cache" in sys.argv and os.path.exists(raw_path):
        raw_text = open(raw_path, encoding="utf-8").read()
    else:
        raw_text = fetch_payload()
        open(raw_path, "w", encoding="utf-8").write(raw_text)

    data = decode(json.loads(raw_text))
    result = data["result"]
    casas = result["casas"]
    atualizado = result.get("atualizadoEm")
    json.dump(
        {"atualizadoEm": atualizado, "coletado_em": None, "casas": casas},
        open(os.path.join(OUT, "casas.json"), "w", encoding="utf-8"),
        ensure_ascii=False, indent=1,
    )

    feats = []
    excluidos = []
    for c in casas:
        cat = (c.get("categoria") or "").lower()
        if any(x in cat for x in EXCLUIR_CATEGORIAS):
            excluidos.append({"nome": c.get("nome"), "categoria": c.get("categoria")})
            continue
        lat, lng = c.get("lat"), c.get("lng")
        tem_coord = bool(lat) and bool(lng)
        props = {
            "entity_id": entity_id(c.get("nome"), c.get("municipio"), c.get("uf")),
            "nome": c.get("nome"),
            "municipio": c.get("municipio"),
            "uf": c.get("uf"),
            "fontes": ["atlas_axe"],
            "num_fontes": 1,
            "fonte_label": FONTE_LABEL,
            "fonte_url": FONTE_URL,
            "fonte_atualizado_em": atualizado,
            "tradicao": c.get("tradicao"),
            "nacao": c.get("nacao"),
            "linha_religiosa": c.get("tradicao"),
            "categoria": c.get("categoria"),
            # nome do dirigente: dado pessoal — fica apenas no payload bruto (local), não na camada
            "bairro": c.get("bairro"),
            "geo_status": (c.get("precisao") or ("sem_coordenada" if not tem_coord else "declarado")),
            "coord_origin": "atlas_axe",
            "situacao_fonte": c.get("situacao"),
            "maps_url": c.get("mapsUrl"),
            "versao": "v5_staging",
        }
        geom = (
            {"type": "Point", "coordinates": [lng, lat]}
            if tem_coord
            else None
        )
        feats.append({"type": "Feature", "geometry": geom, "properties": props})

    gj = {"type": "FeatureCollection", "features": feats}
    json.dump(gj, open(os.path.join(OUT, "atlas_axe.geojson"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    n = len(casas)
    ncoord = sum(1 for f in feats if f["geometry"])
    print(f"Atlas do Axé: {n} registros na fonte | {len(feats)} na camada "
          f"({ncoord} com coordenada) | {len(excluidos)} excluídos por categoria")
    for e in excluidos:
        print(f"  excluído: {e['nome']} — {e['categoria']}")
    print(f"UF: {sorted({c.get('uf') for c in casas})}")


if __name__ == "__main__":
    main()
