# Ilê Axé Map — Terreiros de Candomblé da Bahia

Mapa interativo de terreiros de candomblé e espaços religiosos afro-brasileiros da Bahia.

## Dataset v2.1

- **Fonte primária:** CEAO/UFBA, com os 1.155 registros extraídos e georreferenciados.
- **Fontes complementares:** Google Places (693), OpenStreetMap (20) e SEMUR/SEFAZ Salvador (234 sem coordenadas).
- **Total:** 2.102 registros, dos quais 1.868 aparecem no mapa.
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
├── metodologia.html
├── data/
│   ├── terreiros_v2.geojson
│   ├── terreiros_all_sources_v2.json
│   ├── auditoria_v2.json
│   ├── revisao_humana_nacao_v2.csv
│   └── ceao/terreiros_ceao_complete.json
├── scripts/
│   ├── build_v2.py
│   └── collect_osm.py
└── tests/test_build_v2.py
```

## Regerar e validar

```bash
python3 scripts/build_v2.py
python3 -m unittest discover -s tests -v
```

## Stack

- MapLibre GL JS 4.7.1
- OpenFreeMap
- HTML, CSS e JavaScript sem build
- GitHub Pages

## Responsabilidade

Leonardo Fernandes Nascimento — Laboratório de Humanidades Digitais da Universidade Federal da Bahia (LABHD/UFBA).
