#!/usr/bin/env python3
"""Gera a base v2 com o CEAO completo como fonte primária."""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


COMPONENT_PATTERNS = [
    ("Ketu", r"\b(?:keto|ketu|alaketo|alaketu|nago)\b"),
    ("Angola", r"\bangola\b"),
    ("Jeje", r"\bjeje\b"),
    ("Umbanda", r"\bumbanda\b"),
    ("Candomblé", r"\bcandombl[eé]?\b|\bbatuque\b|\bxango\b"),
    ("Matriz Africana", r"\bmatriz\s+african[ao]?\b|\bafrican[ao]?\b"),
    ("Ijexá", r"\bijexa\b"),
    ("Bantu", r"\bbantu\b"),
    ("Caboclo", r"\bcaboclo\b"),
    ("Vodum", r"\bvodum\b"),
    ("Savalu", r"\bsavalu\b"),
    ("Paketan", r"\bpaketan\b"),
    ("Tapa", r"\btapa\b"),
    ("Giro", r"\bgiro\b"),
    ("Mina", r"\bmina\b"),
]
MAP_CATEGORIES = ("Ketu", "Angola", "Jeje", "Umbanda", "Candomblé", "Matriz Africana")


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def classify_nation(raw_nation: Any) -> dict[str, Any]:
    original = str(raw_nation).strip() if raw_nation is not None else ""
    normalized = normalize_text(original)
    normalized = re.sub(
        r"\b(keto|ketu)(tapa|giro|caboclo|angola|jeje|ijexa)\b",
        r"\1 \2",
        normalized,
    )
    missing = not normalized or normalized in {"nao informado", "nao informada", "sem informacao"}

    if missing:
        return {
            "nacao_original": original or None,
            "nacao_componentes": [],
            "nacao_primaria": None,
            "nacao_categoria": "Não informado",
            "metodo_classificacao": "ausente-v2",
        }

    matches = []
    for component, pattern in COMPONENT_PATTERNS:
        match = re.search(pattern, normalized)
        if match:
            matches.append((match.start(), component))
    components = [component for _, component in sorted(matches)]

    category = next((item for item in MAP_CATEGORIES if item in components), "Outras declarações")
    return {
        "nacao_original": original,
        "nacao_componentes": components,
        "nacao_primaria": None,
        "nacao_categoria": category,
        "metodo_classificacao": "declarado+tokenizacao-v2",
    }


def classify_record(record: dict[str, Any]) -> dict[str, Any]:
    declared = classify_nation(record.get("nacao"))
    if declared["nacao_categoria"] != "Não informado":
        return declared

    text = " ".join(
        str(record.get(key) or "")
        for key in ("religion", "denomination", "nome", "name", "amenity")
    )
    inferred = classify_nation(text)
    if inferred["nacao_categoria"] in MAP_CATEGORIES:
        inferred["nacao_original"] = record.get("nacao") or None
        inferred["nacao_primaria"] = None
        inferred["metodo_classificacao"] = "inferido_texto-v2"
        return inferred
    return declared


def valid_coordinates(record: dict[str, Any]) -> bool:
    try:
        lat = float(record["lat"])
        lng = float(record["lng"])
    except (KeyError, TypeError, ValueError):
        return False
    return -18.5 <= lat <= -8.0 and -47.0 <= lng <= -37.0


def clean_ceao_record(raw: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    record = {key: value for key, value in raw.items() if key != "raw_html"}
    record["ceao_id"] = str(record.pop("id", record.get("ceao_id", "")))
    record["fonte"] = "ceao"
    record["fonte_detalhe"] = "CEAO/UFBA - terreiros.ceao.ufba.br"
    record["geo_status"] = "in_bahia" if valid_coordinates(record) else "out_of_bahia"
    record["fontes"] = [{"fonte": "ceao", "id": record["ceao_id"]}]

    if previous:
        for key in ("rating", "reviews"):
            if previous.get(key) is not None:
                record[key] = previous[key]

    record.update(classify_record(record))
    return record


def prepare_other_record(raw: dict[str, Any]) -> dict[str, Any]:
    record = dict(raw)
    source = record.get("fonte") or "desconhecida"
    source_id = record.get("place_id") or record.get("osm_id") or record.get("sefaz_codigo")
    record["fontes"] = [{"fonte": source, "id": source_id}]
    record.update(classify_record(record))
    return record


def to_feature(record: dict[str, Any]) -> dict[str, Any]:
    properties = {key: value for key, value in record.items() if key not in {"lat", "lng"}}
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [float(record["lng"]), float(record["lat"])],
        },
        "properties": properties,
    }


def build_human_review(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mappable = [record for record in records if valid_coordinates(record)]
    selected: dict[int, dict[str, Any]] = {}

    for index, record in enumerate(mappable):
        components = record.get("nacao_componentes") or []
        if record.get("nacao_categoria") == "Outras declarações" or len(components) > 1:
            selected[index] = record

    for category in Counter(record["nacao_categoria"] for record in mappable):
        added = 0
        for index, record in enumerate(mappable):
            if record["nacao_categoria"] != category or index in selected:
                continue
            selected[index] = record
            added += 1
            if added == 10:
                break

    rows = []
    for index, record in sorted(selected.items()):
        source_id = (
            record.get("ceao_id")
            or record.get("place_id")
            or record.get("osm_id")
            or record.get("sefaz_codigo")
            or index
        )
        rows.append({
            "fonte": record.get("fonte", ""),
            "id_fonte": source_id,
            "nome": record.get("nome") or record.get("name") or "",
            "nacao_original": record.get("nacao_original") or "",
            "nacao_componentes": json.dumps(record.get("nacao_componentes") or [], ensure_ascii=False),
            "nacao_categoria": record.get("nacao_categoria", ""),
            "metodo_classificacao": record.get("metodo_classificacao", ""),
            "status_revisao": "pendente",
            "decisao_revisor": "",
            "observacoes": "",
        })
    return rows


def build_v2(ceao_path: Path, current_path: Path, output_dir: Path) -> dict[str, Any]:
    ceao_raw = json.loads(ceao_path.read_text(encoding="utf-8"))
    current = json.loads(current_path.read_text(encoding="utf-8"))
    current_records = current["terreiros"]

    previous_ceao = {
        str(record.get("ceao_id")): record
        for record in current_records
        if record.get("fonte") == "ceao"
    }
    ceao_records = [
        clean_ceao_record(raw, previous_ceao.get(str(raw.get("id") or raw.get("ceao_id"))))
        for raw in ceao_raw
    ]
    other_records = [
        prepare_other_record(record)
        for record in current_records
        if record.get("fonte") != "ceao"
    ]
    records = ceao_records + other_records
    features = [to_feature(record) for record in records if valid_coordinates(record)]

    source_counts = Counter(record.get("fonte", "desconhecida") for record in records)
    mapped_source_counts = Counter(feature["properties"].get("fonte") for feature in features)
    category_counts = Counter(feature["properties"]["nacao_categoria"] for feature in features)
    ceao_ids = [record["ceao_id"] for record in ceao_records]
    review_rows = build_human_review(records)

    audit = {
        "versao": "2.0",
        "criterio": "CEAO completo como fonte primária; Google, OSM e SEFAZ preservados como complementares",
        "total_registros": len(records),
        "total_georreferenciados": len(features),
        "fontes": dict(sorted(source_counts.items())),
        "fontes_georreferenciadas": dict(sorted(mapped_source_counts.items())),
        "classificacao_mapa": dict(category_counts.most_common()),
        "reconciliacao_ceao": {
            "extraidos": len(ceao_raw),
            "representados": len(ceao_records),
            "ids_unicos": len(set(ceao_ids)),
            "presentes_na_v1": len(previous_ceao),
            "adicionados_na_v2": len(ceao_records) - len(previous_ceao),
            "ausentes": len(ceao_raw) - len(ceao_records),
        },
        "seguranca": {
            "v1_preservada": True,
            "arquivos_v2": ["terreiros_all_sources_v2.json", "terreiros_v2.geojson"],
        },
        "revisao_humana": {
            "arquivo": "revisao_humana_nacao_v2.csv",
            "amostra": len(review_rows),
            "status": "pendente",
            "criterio": "todas as Outras declarações, todos os rótulos compostos e amostra de até 10 registros por categoria",
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    all_sources = {
        "metadata": {
            **current.get("metadata", {}),
            "versao": "2.0",
            "total_registros": len(records),
            "total_georreferenciados": len(features),
            "fonte_primaria": "CEAO/UFBA",
            "auditoria": "auditoria_v2.json",
        },
        "terreiros": records,
    }
    geojson = {
        "type": "FeatureCollection",
        "metadata": {
            "versao": "2.0",
            "total": len(features),
            "fonte_primaria": "CEAO/UFBA",
            "fontes": dict(sorted(mapped_source_counts.items())),
            "classificacao_mapa": dict(category_counts.most_common()),
        },
        "features": features,
    }

    (output_dir / "terreiros_all_sources_v2.json").write_text(
        json.dumps(all_sources, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "terreiros_v2.geojson").write_text(
        json.dumps(geojson, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    (output_dir / "auditoria_v2.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (output_dir / "revisao_humana_nacao_v2.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(review_rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(review_rows)

    return {
        "source_counts": dict(source_counts),
        "total_records": len(records),
        "mappable_records": len(features),
        "audit": audit,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ceao", type=Path, default=Path("data/ceao/terreiros_ceao_complete.json"))
    parser.add_argument("--current", type=Path, default=Path("data/terreiros_all_sources.json"))
    parser.add_argument("--output", type=Path, default=Path("data"))
    args = parser.parse_args()

    result = build_v2(args.ceao, args.current, args.output)
    print(json.dumps(result["audit"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
