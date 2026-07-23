# Ilê Axé Map — Terreiros de Candomblé da Bahia

Mapa interativo dos terreiros de candomblé (ilê axé) da Bahia, construído com dados abertos do OpenStreetMap.

## Stack
- **Mapa**: MapLibre GL JS + OpenStreetMap tiles (dark theme)
- **Dados**: OpenStreetMap (Overpass API)
- **Hospedagem**: GitHub Pages

## Estrutura
```
├── index.html          # Site estático
├── data/
│   └── terreiros.geojson  # Dados dos terreiros
└── scripts/
    └── collect_osm.py  # Script de coleta
```

## Fontes de dados
- OpenStreetMap — tags: `amenity=place_of_worship`, `religion=candomblé`, nomes com "terreiro", "ilê axé", etc.
- Futuramente: Google Maps Places API (complementar)

## LABHD/UFBA
Laboratório de Humanidades Digitais da Universidade Federal da Bahia.