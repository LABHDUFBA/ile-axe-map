#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera o payload da API (KV) a partir da camada publicada.

O arquivo de saída NÃO vai para o Git: é o mesmo dado, mas fora do repositório,
porque o ponto da API é justamente não manter a coleção completa num diretório
público. Ele carrega também a impressão digital do build, que sobrevive a cópias
ingênuas e serve de prova de origem.

Uso:
    python3 scripts/kv_payload_v5.py
    # depois, com a conta Cloudflare autenticada:
    npx wrangler kv key put --binding=TERREIROS v5 \
        --path=data/v5/kv_payload.json --remote
"""
import collections
import hashlib
import json
import os
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYER = os.path.join(REPO, "data", "v5", "terreiros_nacional_v5.geojson")
OUT = os.path.join(REPO, "data", "v5", "kv_payload.json")

CAMADAS_PUBLICAS = (
    "nome", "municipio", "uf", "bairro", "localidade", "tradicao", "tradicoes_adicionais",
    "nacoes", "linhas", "raiz", "pratica", "cruzamento", "fonte_label", "fontes",
    "num_fontes", "geo_status", "ano_fundacao", "foto_thumb", "regente", "entity_id",
    "nacao", "categoria", "nome_anterior", "endereco", "ponto_referencia", "instagram",
    "contribuicao", "coord_confirmada_por", "geo_cnefe",
)


def main():
    camada = json.load(open(LAYER, encoding="utf-8"))
    feats = camada["features"]
    bruto = open(LAYER, "rb").read()
    build = hashlib.sha256(bruto).hexdigest()[:12]

    # allowlist de campos: o que a interface precisa, nada além
    saida = []
    removidos = collections.Counter()
    for f in feats:
        props = f.get("properties") or {}
        novos = {}
        for k, v in props.items():
            if k in CAMADAS_PUBLICAS:
                novos[k] = v
            else:
                removidos[k] += 1
        saida.append({"type": "Feature", "geometry": f.get("geometry"), "properties": novos})

    por_fonte = collections.Counter(s for f in saida for s in (f["properties"].get("fontes") or []))
    payload = {
        "build": build,
        "meta": {
            "versao": "v5",
            "atualizado_em": datetime.now(timezone.utc).date().isoformat(),
            "entidades": len(saida),
            "fontes": dict(por_fonte.most_common()),
            "licenca": "uso livre para pesquisa, ensino e política pública com atribuição; vedado uso comercial",
            "impressao_digital": build,
        },
        "type": "FeatureCollection",
        "features": saida,
    }
    json.dump(payload, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)

    print(f"{OUT}: {len(saida)} entidades | build {build} | {os.path.getsize(OUT)/1e6:.1f} MB")
    if removidos:
        print("campos fora da allowlist:", dict(removidos))


if __name__ == "__main__":
    main()
