#!/usr/bin/env python3
"""Generate national GeoJSON from v3 deduplicated entity data.

Reads:
- data/processed/v3/entities_v3.jsonl  (8,565 deduplicated entities)
- data/processed/v3/entity_assignments_v3.jsonl  (maps entity_id -> source_record_key)
- data/processed/v3/source_records.jsonl  (original records with coordinates)

Strategy:
  For each entity, find all source records assigned to it via entity_assignments.
  Pick the best coordinate from any assigned source record:
    1. localizacao_original.latitude/longitude (if both non-null)
    2. dados_originais.nominatim_lat/nominatim_lng (if both non-null)
  If no assigned source record has coordinates, use placeholder (0, 0).

Outputs:
- data/terreiros_nacional_v3.geojson  (FeatureCollection, one Feature per entity)
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, 'data', 'processed', 'v3')
OUT_PATH = os.path.join(BASE, 'data', 'terreiros_nacional.geojson')

def load_jsonl(path):
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records

def main():
    print("Loading entities...")
    entities = load_jsonl(os.path.join(DATA_DIR, 'entities_v3.jsonl'))
    print(f"  {len(entities)} entities")

    print("Loading assignments...")
    assignments = load_jsonl(os.path.join(DATA_DIR, 'entity_assignments_v3.jsonl'))
    print(f"  {len(assignments)} assignments")

    print("Loading source records...")
    sources = load_jsonl(os.path.join(DATA_DIR, 'source_records.jsonl'))
    print(f"  {len(sources)} source records")

    # Index source records by source_record_key
    sources_by_key = {}
    for sr in sources:
        key = sr.get('source_record_key')
        if key:
            sources_by_key[key] = sr
    print(f"  {len(sources_by_key)} unique source keys indexed")

    # Group assignments by entity_id
    assignments_by_entity = {}
    for a in assignments:
        eid = a.get('entity_id')
        if eid not in assignments_by_entity:
            assignments_by_entity[eid] = []
        assignments_by_entity[eid].append(a)
    print(f"  {len(assignments_by_entity)} entities with assignments")

    def extract_coords(sr):
        """Extract best coordinate from a source record. Returns (lat, lng) or None."""
        loc = sr.get('localizacao_original', {}) or {}
        lat = loc.get('latitude')
        lng = loc.get('longitude')
        if lat is not None and lng is not None:
            try:
                lat_f = float(lat)
                lng_f = float(lng)
                if -90 <= lat_f <= 90 and -180 <= lng_f <= 180:
                    return (lat_f, lng_f)
            except (ValueError, TypeError):
                pass
        # Fallback: nominatim coords
        dados = sr.get('dados_originais', {}) or {}
        nlat = dados.get('nominatim_lat')
        nlng = dados.get('nominatim_lng')
        if nlat is not None and nlng is not None:
            try:
                nlat_f = float(nlat)
                nlng_f = float(nlng)
                if -90 <= nlat_f <= 90 and -180 <= nlng_f <= 180:
                    return (nlat_f, nlng_f)
            except (ValueError, TypeError):
                pass
        return None

    features = []
    with_coords = 0
    without_coords = 0

    for ent in entities:
        eid = ent.get('entity_id')
        canonical_name = ent.get('canonical_name', 'Sem nome')
        sources_list = ent.get('sources', [])
        occurrence_count = ent.get('occurrence_count', 1)

        # Find best coordinate from assigned source records
        best_coord = None
        best_source = None
        best_loc_info = None

        for a in assignments_by_entity.get(eid, []):
            sr_key = a.get('source_record_key')
            sr = sources_by_key.get(sr_key)
            if sr:
                coord = extract_coords(sr)
                if coord and best_coord is None:
                    best_coord = coord
                    best_source = sr
                    loc = sr.get('localizacao_original', {}) or {}
                    best_loc_info = {
                        'municipio': loc.get('municipio'),
                        'uf': loc.get('uf'),
                        'endereco': loc.get('endereco'),
                        'fonte_coordenada': loc.get('fonte_coordenada'),
                        'cep': loc.get('cep'),
                    }

        # Determine primary fonte (singular) from the first source
        primary_fonte = sources_list[0] if isinstance(sources_list, list) and sources_list else ''

        # Build properties
        props = {
            'entity_id': eid,
            'nome': canonical_name,
            'fonte': primary_fonte,
            'fontes': ', '.join(sources_list) if isinstance(sources_list, list) else str(sources_list),
            'num_fontes': len(sources_list) if isinstance(sources_list, list) else 0,
            'ocorrencias': occurrence_count,
        }

        if best_coord:
            with_coords += 1
            props['tem_coordenada'] = True
            if best_loc_info:
                props['municipio'] = best_loc_info.get('municipio') or ''
                props['uf'] = best_loc_info.get('uf') or ''
                props['endereco'] = best_loc_info.get('endereco') or ''
                props['fonte_coordenada'] = best_loc_info.get('fonte_coordenada') or ''
                props['cep'] = best_loc_info.get('cep') or ''
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [best_coord[1], best_coord[0]]  # [lng, lat]
                },
                'properties': props
            }
        else:
            without_coords += 1
            props['tem_coordenada'] = False
            props['municipio'] = ''
            props['uf'] = ''
            props['endereco'] = ''
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [0.0, 0.0]  # placeholder
                },
                'properties': props
            }

        features.append(feature)

    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    print(f"\nResults:")
    print(f"  Total features: {len(features)}")
    print(f"  With coordinates: {with_coords}")
    print(f"  Without coordinates (placeholder 0,0): {without_coords}")

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False)
    
    file_size = os.path.getsize(OUT_PATH)
    print(f"  Written to: {OUT_PATH}")
    print(f"  File size: {file_size / 1024 / 1024:.2f} MB")

if __name__ == '__main__':
    main()