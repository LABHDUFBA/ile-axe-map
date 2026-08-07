"""Gera candidatos conservadores de deduplicação sem remover ocorrências."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
import unicodedata
import uuid
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

import jsonschema

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


PROTOCOL = "dedup-candidate-v3"
EARTH_RADIUS_M = 6_371_000.0
CELL_SIZE_M = 500.0


class GenerationError(RuntimeError):
    """Falha de integridade ou contrato antes da publicação."""


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def _normalize_legacy(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return " ".join(text.casefold().split())


def _cnpj_digits(value: Any) -> str:
    return re.sub(r"\D", "", value) if isinstance(value, str) else ""


def _valid_cnpj(value: Any) -> str | None:
    digits = _cnpj_digits(value)
    if len(digits) != 14 or len(set(digits)) == 1:
        return None

    def digit(prefix: str, weights: tuple[int, ...]) -> str:
        remainder = sum(int(number) * weight for number, weight in zip(prefix, weights)) % 11
        return "0" if remainder < 2 else str(11 - remainder)

    first = digit(digits[:12], (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
    second = digit(digits[:12] + first, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
    return digits if digits[-2:] == first + second else None


def _municipality_key(record: dict[str, Any]) -> tuple[str, str, str] | None:
    location = record.get("localizacao_original", {})
    raw = record.get("dados_originais", {})
    uf = _normalize(location.get("uf"))
    if record.get("fonte") == "cnpj" and raw.get("codigo_municipio") not in (None, ""):
        return "ibge", str(raw["codigo_municipio"]).strip(), uf
    municipality = _normalize(location.get("municipio"))
    if municipality:
        return "text", municipality, uf
    return None


def _geography_relation(
    left: dict[str, Any], right: dict[str, Any]
) -> tuple[str, list[str]]:
    left_key = _municipality_key(left)
    right_key = _municipality_key(right)
    left_uf = left_key[2] if left_key else _normalize(left.get("localizacao_original", {}).get("uf"))
    right_uf = right_key[2] if right_key else _normalize(right.get("localizacao_original", {}).get("uf"))
    negatives = []
    if left_uf and right_uf and left_uf != right_uf:
        negatives.extend(("different_municipality", "different_uf"))
        return "different", negatives
    if left_key and right_key and left_key[:2] == right_key[:2]:
        return "same", negatives
    if left_key and right_key and left_key[0] == right_key[0]:
        negatives.append("different_municipality")
        return "different", negatives
    return "unknown", negatives


def _coordinates(record: dict[str, Any]) -> tuple[float, float, str] | None:
    location = record.get("localizacao_original", {})
    latitude = location.get("latitude")
    longitude = location.get("longitude")
    if latitude is not None and longitude is not None:
        return float(latitude), float(longitude), "declared"
    raw = record.get("dados_originais", {})
    if record.get("fonte") == "mapeando_axe":
        latitude, longitude = raw.get("nominatim_lat"), raw.get("nominatim_lng")
    elif record.get("fonte") == "cnpj":
        latitude, longitude = raw.get("lat"), raw.get("lng")
    else:
        return None
    if latitude is None or longitude is None:
        return None
    return float(latitude), float(longitude), "geocoder_auxiliary"


def _distance_m(left: tuple[float, float], right: tuple[float, float]) -> float:
    left_lat, left_lon = left
    right_lat, right_lon = right
    delta_lat = math.radians(right_lat - left_lat)
    delta_lon = math.radians(right_lon - left_lon)
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(math.radians(left_lat))
        * math.cos(math.radians(right_lat))
        * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(haversine)))


def _distance_bucket(distance: float) -> str:
    if distance <= 25:
        return "0-25m"
    if distance <= 100:
        return "25-100m"
    return "100-500m"


def _jaccard(left: Any, right: Any) -> float:
    left_tokens = set(_normalize(left).split())
    right_tokens = set(_normalize(right).split())
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _pair_key(left_key: str, right_key: str) -> str:
    left_key, right_key = sorted((left_key, right_key))
    digest = hashlib.sha256(
        f"{PROTOCOL}\0{left_key}\0{right_key}".encode("utf-8")
    ).hexdigest()
    return f"dedupv3:{digest}"


def _evidence(
    evidence_type: str,
    provenance: str,
    authority: str,
    *,
    score: float | None = None,
    distance_bucket: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "type": evidence_type,
        "provenance": provenance,
        "authority": authority,
    }
    if score is not None:
        item["score"] = round(score, 3)
    if distance_bucket is not None:
        item["distance_bucket"] = distance_bucket
    return item


def _evidence_identity(item: dict[str, Any]) -> str:
    return json.dumps(item, sort_keys=True, separators=(",", ":"))


def generate_candidates(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Gera pares e componentes de revisão, sem materializar entidades."""
    ordered_records = sorted(records, key=lambda row: row["source_record_key"])
    by_key = {row["source_record_key"]: row for row in ordered_records}
    if len(by_key) != len(ordered_records):
        raise GenerationError("source_record_key duplicada")

    candidates: dict[tuple[str, str], dict[str, Any]] = {}
    pair_modes: dict[tuple[str, str], set[str]] = defaultdict(set)

    def add_pair(
        left: dict[str, Any],
        right: dict[str, Any],
        evidence: dict[str, Any],
        mode: str,
    ) -> None:
        left_key, right_key = sorted(
            (left["source_record_key"], right["source_record_key"])
        )
        key = (left_key, right_key)
        item = candidates.setdefault(
            key,
            {
                "candidate_pair_key": _pair_key(left_key, right_key),
                "left_source_record_key": left_key,
                "right_source_record_key": right_key,
                "left_source": by_key[left_key]["fonte"],
                "right_source": by_key[right_key]["fonte"],
                "evidence": [],
                "negative_evidence": [],
                "suggested_relation": "unresolved",
                "review_status": "pending",
                "candidate_component_key": "",
                "canonical_entity_created": False,
            },
        )
        identities = {_evidence_identity(existing) for existing in item["evidence"]}
        if _evidence_identity(evidence) not in identities:
            item["evidence"].append(evidence)
        pair_modes[key].add(mode)

    cnpj_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    native_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    name_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    coordinate_groups: dict[tuple[float, float], list[str]] = defaultdict(list)
    coordinates: dict[str, tuple[float, float, str]] = {}

    for record in ordered_records:
        cnpj = _valid_cnpj(record.get("identificadores", {}).get("cnpj"))
        if cnpj:
            cnpj_groups[cnpj].append(record)
        native_id = record.get("id_fonte")
        if native_id and not record.get("id_fonte_sintetico", False):
            native_groups[(record["fonte"], str(native_id))].append(record)
        name = _normalize(record.get("nome_original"))
        if name:
            name_groups[name].append(record)
        coordinate = _coordinates(record)
        if coordinate:
            coordinates[record["source_record_key"]] = coordinate
            coordinate_groups[(coordinate[0], coordinate[1])].append(
                record["source_record_key"]
            )

    for group in cnpj_groups.values():
        for left, right in combinations(group, 2):
            add_pair(
                left,
                right,
                _evidence("exact_cnpj", "promoted_identifier", "source_native", score=1.0),
                "strong",
            )
    conflicted_native_pairs: set[tuple[str, str]] = set()
    for group in native_groups.values():
        group_cnpjs = {
            cnpj
            for row in group
            if (cnpj := _valid_cnpj(row.get("identificadores", {}).get("cnpj")))
        }
        if len(group_cnpjs) > 1:
            conflicted_native_pairs.update(
                tuple(sorted((left["source_record_key"], right["source_record_key"])))
                for left, right in combinations(group, 2)
            )
        for left, right in combinations(group, 2):
            add_pair(
                left,
                right,
                _evidence("exact_native_id", "source_namespace", "source_native", score=1.0),
                "strong",
            )

    geographic_homonym_pairs = 0
    exact_name_pairs_same_municipality = 0
    exact_name_cross_source_groups = 0
    exact_name_cross_source_pairs = 0
    for group in name_groups.values():
        if len(group) < 2:
            continue
        if len({row["fonte"] for row in group}) > 1:
            exact_name_cross_source_groups += 1
        for left, right in combinations(group, 2):
            geography, _ = _geography_relation(left, right)
            cross_source = left["fonte"] != right["fonte"]
            if cross_source:
                exact_name_cross_source_pairs += 1
            if geography == "different":
                geographic_homonym_pairs += 1
                continue
            if geography == "same":
                exact_name_pairs_same_municipality += 1
                add_pair(
                    left,
                    right,
                    _evidence("exact_name", "normalized_name", "declared", score=1.0),
                    "weak",
                )
            elif cross_source:
                add_pair(
                    left,
                    right,
                    _evidence("exact_name", "normalized_name", "declared", score=1.0),
                    "unresolved",
                )

    spatial_buckets: dict[tuple[tuple[str, str, str], int, int], list[str]] = defaultdict(list)
    for record in ordered_records:
        key = record["source_record_key"]
        coordinate = coordinates.get(key)
        municipality = _municipality_key(record)
        if not coordinate or not municipality:
            continue
        latitude, longitude, _ = coordinate
        x = EARTH_RADIUS_M * math.radians(longitude) * math.cos(math.radians(latitude))
        y = EARTH_RADIUS_M * math.radians(latitude)
        spatial_buckets[(municipality, math.floor(x / CELL_SIZE_M), math.floor(y / CELL_SIZE_M))].append(key)

    seen_spatial: set[tuple[str, str]] = set()
    proximity_pairs_compatible = 0
    for (municipality, bucket_x, bucket_y), left_keys in spatial_buckets.items():
        nearby = []
        for delta_x in (-1, 0, 1):
            for delta_y in (-1, 0, 1):
                nearby.extend(
                    spatial_buckets.get(
                        (municipality, bucket_x + delta_x, bucket_y + delta_y), []
                    )
                )
        for left_key in left_keys:
            for right_key in nearby:
                pair_key = (
                    min(left_key, right_key),
                    max(left_key, right_key),
                )
                if left_key == right_key or pair_key in seen_spatial:
                    continue
                seen_spatial.add(pair_key)
                left, right = by_key[pair_key[0]], by_key[pair_key[1]]
                similarity = _jaccard(left.get("nome_original"), right.get("nome_original"))
                if similarity < 0.8:
                    continue
                left_coordinate = coordinates[left_key]
                right_coordinate = coordinates[right_key]
                distance = _distance_m(left_coordinate[:2], right_coordinate[:2])
                if distance > 500:
                    continue
                proximity_pairs_compatible += 1
                authority = (
                    "geocoder_auxiliary"
                    if "geocoder_auxiliary" in (left_coordinate[2], right_coordinate[2])
                    else "declared"
                )
                add_pair(
                    left,
                    right,
                    _evidence(
                        "name_similarity",
                        "normalized_name_tokens",
                        "derived",
                        score=similarity,
                    ),
                    "weak",
                )
                add_pair(
                    left,
                    right,
                    _evidence(
                        "distance",
                        "derived_spatial_grid",
                        authority,
                        distance_bucket=_distance_bucket(distance),
                    ),
                    "weak",
                )

    collapsed_keys = {
        key
        for group in coordinate_groups.values()
        if len(group) >= 3
        for key in group
    }
    for key, candidate in candidates.items():
        left, right = by_key[key[0]], by_key[key[1]]
        negatives: set[str] = set()
        geography, geography_negatives = _geography_relation(left, right)
        negatives.update(geography_negatives)
        left_cnpj = _valid_cnpj(left.get("identificadores", {}).get("cnpj"))
        right_cnpj = _valid_cnpj(right.get("identificadores", {}).get("cnpj"))
        different_cnpj = bool(left_cnpj and right_cnpj and left_cnpj != right_cnpj)
        if different_cnpj:
            negatives.add("different_cnpj")
        if key in conflicted_native_pairs:
            negatives.add("strong_id_conflict")
        if key[0] in collapsed_keys and key[1] in collapsed_keys:
            left_coordinate = coordinates.get(key[0])
            right_coordinate = coordinates.get(key[1])
            if left_coordinate and right_coordinate and left_coordinate[:2] == right_coordinate[:2]:
                negatives.add("collapsed_coordinate")

        if different_cnpj:
            candidate["suggested_relation"] = "distinct_entities"
            candidate["review_status"] = "rejected"
        elif key in conflicted_native_pairs:
            candidate["suggested_relation"] = "unresolved"
            candidate["review_status"] = "pending"
        elif "strong" in pair_modes[key]:
            moved = geography == "different"
            left_coordinate = coordinates.get(key[0])
            right_coordinate = coordinates.get(key[1])
            if left_coordinate and right_coordinate:
                moved = moved or _distance_m(left_coordinate[:2], right_coordinate[:2]) > 500
            candidate["suggested_relation"] = (
                "possible_same_entity_moved" if moved else "same_entity_same_location"
            )
            candidate["review_status"] = "auto_linked_strong_id"
        elif "weak" in pair_modes[key]:
            candidate["suggested_relation"] = "possible_same_entity"
        else:
            candidate["suggested_relation"] = "unresolved"
        candidate["evidence"].sort(
            key=lambda item: (item["type"], _evidence_identity(item))
        )
        candidate["negative_evidence"] = [
            {"type": item} for item in sorted(negatives)
        ]

    adjacency: dict[str, set[str]] = defaultdict(set)
    for left_key, right_key in candidates:
        adjacency[left_key].add(right_key)
        adjacency[right_key].add(left_key)
    component_by_key: dict[str, str] = {}
    visited: set[str] = set()
    component_sizes: list[int] = []
    for start in sorted(adjacency):
        if start in visited:
            continue
        stack = [start]
        members = []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            members.append(current)
            stack.extend(sorted(adjacency[current] - visited, reverse=True))
        members.sort()
        digest = hashlib.sha256(
            ("dedup-component-v3\0" + "\0".join(members)).encode("utf-8")
        ).hexdigest()
        component_key = f"dedup-component-v3:{digest}"
        component_sizes.append(len(members))
        for member in members:
            component_by_key[member] = component_key
    for key, candidate in candidates.items():
        candidate["candidate_component_key"] = component_by_key[key[0]]

    candidate_pairs = sorted(candidates.values(), key=lambda item: item["candidate_pair_key"])
    same_municipality_name_groups: Counter[
        tuple[str, tuple[str, str, str]]
    ] = Counter()
    for row in records:
        normalized_name = _normalize(row.get("nome_original"))
        municipality = _municipality_key(row)
        if normalized_name and municipality:
            same_municipality_name_groups[(normalized_name, municipality)] += 1
    metrics = {
        "occurrences_preserved": len(records),
        "records_with_name": sum(bool(_normalize(row.get("nome_original"))) for row in records),
        "exact_name_groups_overall": sum(len(group) > 1 for group in name_groups.values()),
        "exact_name_cross_source_groups": exact_name_cross_source_groups,
        "exact_name_cross_source_pairs": exact_name_cross_source_pairs,
        "exact_name_groups_same_municipality": sum(
            count > 1 for count in same_municipality_name_groups.values()
        ),
        "exact_name_pairs_same_municipality": exact_name_pairs_same_municipality,
        "geographic_homonym_pairs": geographic_homonym_pairs,
        "proximity_name_compatible_pairs": proximity_pairs_compatible,
        "collapsed_coordinate_groups": sum(len(group) >= 3 for group in coordinate_groups.values()),
        "candidate_components": len(component_sizes),
        "candidate_component_records": sum(component_sizes),
    }
    return {"candidate_pairs": candidate_pairs, "metrics": metrics}


def _legacy_location_key(row: dict[str, Any]) -> tuple[str, str, float, float] | None:
    source_aliases = {"google places": "google"}
    source = source_aliases.get(_normalize_legacy(row.get("fonte")), _normalize_legacy(row.get("fonte")))
    latitude = row.get("lat", row.get("latitude"))
    longitude = row.get("lng", row.get("longitude"))
    name = row.get("nome")
    if not source or not name or latitude in (None, "") or longitude in (None, ""):
        return None
    return source, _normalize_legacy(name), round(float(latitude), 6), round(float(longitude), 6)


def _original_stable_key(row: dict[str, Any]) -> str:
    from src.audit.legacy_ledgers import build_stable_identity

    return build_stable_identity(row)["stable_key"]


def _reconcile_ledger(
    records: list[dict[str, Any]], curated_path: Path, original_path: Path
) -> tuple[dict[str, str], dict[str, int]]:
    with curated_path.open(encoding="utf-8", newline="") as handle:
        curated = list(csv.DictReader(handle))
    with original_path.open(encoding="utf-8", newline="") as handle:
        original = list(csv.DictReader(handle))
    if len({row["stable_key"] for row in curated}) != len(curated):
        raise GenerationError("stable_key duplicada no ledger curado")

    original_by_stable: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in original:
        original_by_stable[_original_stable_key(row)].append(row)
    records_by_cnpj: dict[str, list[dict[str, Any]]] = defaultdict(list)
    records_by_location: dict[tuple[str, str, float, float], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        cnpj = _valid_cnpj(record.get("identificadores", {}).get("cnpj"))
        if cnpj:
            records_by_cnpj[f"cnpj:{cnpj}"].append(record)
        location_key = _legacy_location_key(record.get("dados_originais", {}))
        if location_key:
            records_by_location[location_key].append(record)

    matched: dict[str, str] = {}
    counts = Counter()
    for row in curated:
        originals = original_by_stable.get(row["stable_key"], [])
        if len(originals) != 1:
            counts["bridge_original_missing" if not originals else "bridge_original_ambiguous"] += 1
            matches = []
        elif row.get("identity_synthetic") == "false":
            matches = records_by_cnpj.get(row["stable_key"], [])
        else:
            location_key = _legacy_location_key(originals[0])
            matches = records_by_location.get(location_key, []) if location_key else []
        if len(matches) == 1:
            counts["matched"] += 1
            reference = "curated-exclusion-v3:" + hashlib.sha256(
                row["stable_key"].encode("utf-8")
            ).hexdigest()
            matched[matches[0]["source_record_key"]] = reference
        elif not matches:
            counts["absent"] += 1
        else:
            counts["ambiguous"] += 1
    counts["rows"] = len(curated)
    for field in (
        "matched",
        "absent",
        "ambiguous",
        "bridge_original_missing",
        "bridge_original_ambiguous",
    ):
        counts.setdefault(field, 0)
    if counts["matched"] + counts["absent"] + counts["ambiguous"] != len(curated):
        raise GenerationError("equação do ledger curado não fecha")
    return matched, dict(counts)


def _jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return (
        "".join(
            json.dumps(
                row,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
            for row in rows
        )
    ).encode("utf-8")


def _write_synced(path: Path, content: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_release(contents: dict[Path, bytes]) -> None:
    token = uuid.uuid4().hex
    temporary = {path: path.parent / f".{path.name}.tmp-{token}" for path in contents}
    backups = {path: path.parent / f".{path.name}.bak-{token}" for path in contents}
    backed_up: set[Path] = set()
    published: set[Path] = set()
    directories = {path.parent for path in contents}
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    try:
        for destination, content in contents.items():
            _write_synced(temporary[destination], content)
        for directory in directories:
            _fsync_directory(directory)
        for destination in contents:
            if destination.exists():
                os.replace(destination, backups[destination])
                backed_up.add(destination)
        for destination in contents:
            os.replace(temporary[destination], destination)
            published.add(destination)
        for directory in directories:
            _fsync_directory(directory)
    except BaseException:
        for destination in published:
            destination.unlink(missing_ok=True)
        for destination in contents:
            if destination in backed_up and backups[destination].exists():
                os.replace(backups[destination], destination)
        for directory in directories:
            _fsync_directory(directory)
        raise
    finally:
        for path in (*temporary.values(), *backups.values()):
            path.unlink(missing_ok=True)
        for directory in directories:
            _fsync_directory(directory)


def _load_validated_source(source_path: Path, manifest_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = manifest.get("jsonl", {})
    actual_hash = _sha256_file(source_path)
    if actual_hash != expected.get("sha256"):
        raise GenerationError("hash do source_records.jsonl divergente")
    if source_path.stat().st_size != expected.get("bytes"):
        raise GenerationError("bytes do source_records.jsonl divergentes")
    with source_path.open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle]
    if len(records) != manifest.get("total"):
        raise GenerationError("contagem total do source_records.jsonl divergente")
    counts = Counter(record.get("fonte") for record in records)
    if dict(counts) != manifest.get("counts"):
        raise GenerationError("contagens por fonte do source_records.jsonl divergentes")
    if len({record.get("source_record_key") for record in records}) != len(records):
        raise GenerationError("source_record_key duplicada")
    return records, manifest


def build_dedup_candidates(
    *,
    root: Path,
    candidate_schema_path: Path,
    source_path: Path,
    source_manifest_path: Path,
    curated_ledger_path: Path,
    original_ledger_path: Path,
    candidate_output_path: Path,
    status_output_path: Path,
    summary_output_path: Path,
) -> dict[str, Any]:
    """Valida, gera e publica os três artefatos como uma liberação lógica."""
    del root
    paths = [
        candidate_schema_path,
        source_path,
        source_manifest_path,
        curated_ledger_path,
        original_ledger_path,
        candidate_output_path,
        status_output_path,
        summary_output_path,
    ]
    (
        candidate_schema_path,
        source_path,
        source_manifest_path,
        curated_ledger_path,
        original_ledger_path,
        candidate_output_path,
        status_output_path,
        summary_output_path,
    ) = [Path(path).resolve() for path in paths]
    records, source_manifest = _load_validated_source(source_path, source_manifest_path)
    generated = generate_candidates(records)
    schema = json.loads(candidate_schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    for index, pair in enumerate(generated["candidate_pairs"]):
        errors = list(validator.iter_errors(pair))
        if errors:
            raise GenerationError(
                f"candidato fora do schema no índice {index}: {errors[0].json_path}"
            )
    matched, ledger_counts = _reconcile_ledger(
        records, curated_ledger_path, original_ledger_path
    )
    statuses = []
    for record in sorted(records, key=lambda row: row["source_record_key"]):
        reference = matched.get(record["source_record_key"])
        statuses.append(
            {
                "source_record_key": record["source_record_key"],
                "fonte": record["fonte"],
                "exclusao_curada": reference is not None,
                "ledger_refs": [reference] if reference else [],
                "status": "preserved_curated_exclusion" if reference else "preserved",
            }
        )
    candidate_bytes = _jsonl_bytes(generated["candidate_pairs"])
    status_bytes = _jsonl_bytes(statuses)
    relation_counts = Counter(
        pair["suggested_relation"] for pair in generated["candidate_pairs"]
    )
    review_counts = Counter(pair["review_status"] for pair in generated["candidate_pairs"])
    evidence_counts = Counter(
        evidence["type"]
        for pair in generated["candidate_pairs"]
        for evidence in pair["evidence"]
    )
    negative_counts = Counter(
        evidence["type"]
        for pair in generated["candidate_pairs"]
        for evidence in pair["negative_evidence"]
    )
    summary = {
        "protocol_version": PROTOCOL,
        "input": {
            "sha256": source_manifest["jsonl"]["sha256"],
            "bytes": source_manifest["jsonl"]["bytes"],
            "occurrences": source_manifest["total"],
            "counts_by_source": source_manifest["counts"],
        },
        "outputs": {
            "candidates": {
                "sha256": _sha256_bytes(candidate_bytes),
                "bytes": len(candidate_bytes),
                "lines": len(generated["candidate_pairs"]),
            },
            "occurrence_status": {
                "sha256": _sha256_bytes(status_bytes),
                "bytes": len(status_bytes),
                "lines": len(statuses),
            },
        },
        "candidate_counts": {
            "total": len(generated["candidate_pairs"]),
            "by_relation": dict(sorted(relation_counts.items())),
            "by_review_status": dict(sorted(review_counts.items())),
            "by_evidence": dict(sorted(evidence_counts.items())),
            "by_negative_evidence": dict(sorted(negative_counts.items())),
        },
        "metrics": generated["metrics"],
        "curated_exclusions": ledger_counts,
        "equations": {
            "occurrences_preserved": f"{len(statuses)} = {len(records)}",
            "curated_ledger": (
                f"{ledger_counts.get('matched', 0)} + {ledger_counts.get('absent', 0)} + "
                f"{ledger_counts.get('ambiguous', 0)} = {ledger_counts.get('rows', 0)}"
            ),
            "candidate_relations": f"{sum(relation_counts.values())} = {len(generated['candidate_pairs'])}",
        },
        "canonical_entities_created": 0,
    }
    summary_bytes = (
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")
    _publish_release(
        {
            candidate_output_path: candidate_bytes,
            status_output_path: status_bytes,
            summary_output_path: summary_bytes,
        }
    )
    return summary


def _parser(root: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument("--source-records", type=Path)
    parser.add_argument("--candidate-schema", type=Path)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--curated-ledger", type=Path)
    parser.add_argument("--original-ledger", type=Path)
    parser.add_argument("--candidates-output", type=Path)
    parser.add_argument("--status-output", type=Path)
    parser.add_argument("--summary-output", type=Path)
    return parser


def _resolve_cli_paths(args: argparse.Namespace) -> dict[str, Path]:
    root = args.root.resolve()

    def resolve(value: Path | None, default: str) -> Path:
        if value is None:
            return root / default
        return value.resolve() if value.is_absolute() else (root / value).resolve()

    return {
        "root": root,
        "candidate_schema_path": resolve(
            args.candidate_schema, "schemas/dedup-candidate-v3.schema.json"
        ),
        "source_path": resolve(args.source_records, "data/processed/v3/source_records.jsonl"),
        "source_manifest_path": resolve(args.source_manifest, "data/processed/v3/source_records.manifest.json"),
        "curated_ledger_path": resolve(args.curated_ledger, "data/audit/v3/exclusoes_curadas_v3.csv"),
        "original_ledger_path": resolve(args.original_ledger, "data/exclusoes_curadas.csv"),
        "candidate_output_path": resolve(args.candidates_output, "data/processed/v3/dedup_candidates.jsonl"),
        "status_output_path": resolve(args.status_output, "data/processed/v3/dedup_occurrence_status.jsonl"),
        "summary_output_path": resolve(args.summary_output, "data/audit/v3/dedup_candidates_summary.json"),
    }


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    args = _parser(root).parse_args()
    summary = build_dedup_candidates(**_resolve_cli_paths(args))
    print(f"ocorrências preservadas: {summary['input']['occurrences']}")
    print(f"candidatos: {summary['candidate_counts']['total']}")
    print(f"componentes: {summary['metrics']['candidate_components']}")
    print(f"relações: {json.dumps(summary['candidate_counts']['by_relation'], sort_keys=True)}")
    print(f"status: {json.dumps(summary['candidate_counts']['by_review_status'], sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
