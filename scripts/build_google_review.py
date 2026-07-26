#!/usr/bin/env python3
"""Gera a fila auditável de revisão humana das entradas Google."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


def record_key(record: dict[str, Any]) -> tuple[str, float, float]:
    return (
        str(record.get("nome") or "").strip().casefold(),
        round(float(record.get("lat", record.get("latitude"))), 6),
        round(float(record.get("lng", record.get("longitude"))), 6),
    )


def review_id(record: dict[str, Any]) -> str:
    name, lat, lng = record_key(record)
    value = f"google|{name}|{lat:.6f}|{lng:.6f}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def build_google_review(
    records_path: Path,
    suspects_path: Path,
    exclusions_path: Path,
    output_path: Path,
) -> dict[str, int]:
    source = json.loads(records_path.read_text(encoding="utf-8"))
    suspects = json.loads(suspects_path.read_text(encoding="utf-8"))

    google_records = [
        record for record in source["terreiros"] if record.get("fonte") == "google"
    ]
    ambiguous = {
        record_key(record): record.get("razao", "Caso ambíguo da triagem automática")
        for record in suspects.get("google_ambiguous", [])
    }
    automatic_false_positives = {
        record_key(record): record.get("razao", "Possível falso positivo")
        for record in suspects.get("google_false_positives", [])
    }

    with exclusions_path.open(encoding="utf-8", newline="") as handle:
        exclusions = {record_key(row): row for row in csv.DictReader(handle)}

    rows = []
    for record in google_records:
        key = record_key(record)
        lat = float(record["lat"])
        lng = float(record["lng"])
        exclusion = exclusions.get(key)

        if key in ambiguous:
            suggestion = "ambíguo"
            suggestion_reason = ambiguous[key]
        elif key in automatic_false_positives:
            suggestion = "possível falso positivo"
            suggestion_reason = automatic_false_positives[key]
        else:
            suggestion = "sem sinal automático"
            suggestion_reason = ""

        status = "falso_positivo" if exclusion else "pendente"
        rows.append({
            "review_id": review_id(record),
            "fonte": "google",
            "nome": record.get("nome", ""),
            "endereco": record.get("endereco", ""),
            "bairro": record.get("bairro", ""),
            "telefone": record.get("telefone", ""),
            "rating": record.get("rating"),
            "reviews": record.get("reviews"),
            "latitude": lat,
            "longitude": lng,
            "geo_status": record.get("geo_status", ""),
            "sugestao": suggestion,
            "motivo_sugestao": suggestion_reason,
            "status_revisao": status,
            "motivo_decisao": exclusion.get("motivo", "") if exclusion else "",
            "observacoes": "",
            "google_maps_url": "https://www.google.com/maps/search/?" + urlencode({
                "api": 1,
                "query": f"{lat},{lng}",
            }),
            "street_view_url": "https://www.google.com/maps/@?" + urlencode({
                "api": 1,
                "map_action": "pano",
                "viewpoint": f"{lat},{lng}",
            }),
        })

    priority = {"ambíguo": 0, "possível falso positivo": 1, "sem sinal automático": 2}
    rows.sort(key=lambda row: (
        row["status_revisao"] != "pendente",
        priority[row["sugestao"]],
        row["nome"].casefold(),
    ))

    summary = {
        "total": len(rows),
        "ambiguos": sum(row["sugestao"] == "ambíguo" for row in rows),
        "possiveis_falsos_positivos": sum(
            row["sugestao"] == "possível falso positivo" for row in rows
        ),
        "excluidos_curados": sum(
            row["status_revisao"] == "falso_positivo" for row in rows
        ),
    }
    payload = {
        "metadata": {
            "versao": "1.0",
            "fonte": "Google Places",
            "criterio": "Sugestões automáticas não constituem decisão de exclusão",
            **summary,
        },
        "registros": rows,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=Path("data/terreiros_all_sources.json"))
    parser.add_argument("--suspects", type=Path, default=Path("data/falsos_positivos_suspeitos.json"))
    parser.add_argument("--exclusions", type=Path, default=Path("data/exclusoes_curadas.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/revisao_google.json"))
    args = parser.parse_args()
    print(json.dumps(
        build_google_review(args.records, args.suspects, args.exclusions, args.output),
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
