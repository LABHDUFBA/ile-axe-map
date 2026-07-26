# Ilê Axé Map — Terreiros de Candomblé da Bahia

Mapa interativo de terreiros de candomblé e espaços religiosos afro-brasileiros da Bahia.

## Dataset v2.1

- **Fonte primária:** CEAO/UFBA, com os 1.155 registros extraídos e georreferenciados.
- **Fontes complementares:** Google Places (682), OpenStreetMap (20) e SEMUR/SEFAZ Salvador (234 sem coordenadas).
- **Total:** 2.091 registros, dos quais 1.857 aparecem no mapa.
- A v1 permanece preservada; a interface carrega `data/terreiros_v2.geojson`.

Os totais representam registros preservados por fonte e não devem ser interpretados automaticamente como entidades únicas entre fontes.

### Declarações de nação

- O filtro apresenta as declarações literais do CEAO, sem reunir Keto, Alaketo ou rótulos compostos.
- `Keto Angola`, `Jêje Nagô`, `KetoTapa` e demais valores permanecem separados.
- Apenas espaços duplicados são removidos para exibição.
- Registros sem campo de nação declarado aparecem como `Não informado`; nomes não são usados para inferir pertencimento.
- As cores servem à navegação e não representam parentesco entre tradições.

## Estrutura principal

```text
├── index.html
├── revisao-google.html
├── metodologia.html
├── data/
│   ├── terreiros_v2.geojson
│   ├── terreiros_all_sources_v2.json
│   ├── auditoria_v2.json
│   ├── revisao_humana_nacao_v2.csv
│   ├── revisao_google.json
│   └── ceao/terreiros_ceao_complete.json
├── scripts/
│   ├── build_v2.py
│   ├── build_google_review.py
│   └── collect_osm.py
└── tests/
    ├── test_build_v2.py
    └── test_google_review.py
```

## Revisão humana das entradas Google

A página `revisao-google.html` apresenta as 693 entradas Google em uma fila de
curadoria. Os 133 casos ambíguos da triagem anterior aparecem primeiro. Cada
registro pode ser marcado como `manter`, `falso_positivo` ou `pendente`.

As decisões são salvas no navegador e podem ser exportadas ou importadas em
CSV. Sugestões automáticas não removem registros. Após a conferência da lista,
os falsos positivos confirmados devem ser incorporados a
`data/exclusoes_curadas.csv`; somente então o build v2 aplica as exclusões aos
artefatos publicados. Os dados brutos permanecem preservados.

## Regerar e validar

```bash
python3 scripts/build_v2.py
python3 scripts/build_google_review.py
python3 -m unittest discover -s tests -v
```

## Stack

- MapLibre GL JS 4.7.1
- OpenFreeMap
- HTML, CSS e JavaScript sem build
- GitHub Pages

## Responsabilidade

Leonardo Fernandes Nascimento — Laboratório de Humanidades Digitais da Universidade Federal da Bahia (LABHD/UFBA).
