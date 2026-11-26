#!/usr/bin/env python3
"""Gera data/v5/indice_busca.json — o mínimo que o seletor de registro do formulário precisa.

O formulário baixava o GeoJSON inteiro (5,8 MB) para preencher um <select> com 8 mil opções,
que ninguém consegue percorrer. Este índice tem só o necessário para busca por texto:

  {"m": ["Salvador", "Simões Filho", ...],          # dicionário de municípios
   "e": [["e_7a1d2d666e31_BA", "Ilè Asé ...", 12, "BA", "grafia antiga"], ...]}

Os municípios vão num dicionário porque são repetidíssimos: escrever a string 8 mil vezes
inflaria o arquivo sem informar nada. O índice inteiro fica em ~450 KB (uns 120 KB com gzip
no Pages), contra 5,8 MB do GeoJSON.

`nome_anterior` entra porque quem conhece a casa pode procurar pela grafia antiga e precisa
achar o registro para propor a correção.

Uso: python3 scripts/build_indice_busca.py
"""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEOJSON = os.path.join(REPO, "data", "v5", "terreiros_nacional_v5.geojson")
SAIDA = os.path.join(REPO, "data", "v5", "indice_busca.json")


def construir():
    with open(GEOJSON, encoding="utf-8") as fh:
        dados = json.load(fh)

    municipios = {}
    lista_municipios = []
    entradas = []
    sem_nome = 0

    for f in dados.get("features", []):
        p = f.get("properties") or {}
        entidade = str(p.get("entity_id") or "").strip()
        if not entidade:
            continue
        nome = (p.get("nome") or "").strip()
        if not nome:
            sem_nome += 1
            continue

        mun = (p.get("municipio") or "").strip()
        idx = municipios.get(mun)
        if idx is None:
            idx = len(lista_municipios)
            municipios[mun] = idx
            lista_municipios.append(mun)

        uf = (p.get("uf") or "").strip()
        item = [entidade, nome, idx, uf]
        anterior = (p.get("nome_anterior") or "").strip()
        if anterior and anterior != nome:
            item.append(anterior)
        entradas.append(item)

    entradas.sort(key=lambda e: e[1].lower())

    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump({"m": lista_municipios, "e": entradas}, fh,
                  ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")

    kb = os.path.getsize(SAIDA) / 1024
    print(f"indice_busca.json: {len(entradas)} registros, {kb:.0f} KB, "
          f"{len(lista_municipios)} municípios, {sem_nome} sem nome (omitidos)")
    return len(entradas)


if __name__ == "__main__":
    construir()
