"""Gera candidatos conservadores de deduplicação sem remover ocorrências."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import sys
import unicodedata
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

import jsonschema

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.v3.adapters.common import make_source_record_key

PROTOCOL = "dedup-candidate-v3"
OCCURRENCE_REF_PROTOCOL = "occurrence-ref-v1"
EARTH_RADIUS_M = 6_371_000.0
CELL_SIZE_M = 500.0
DEFAULT_MAX_STRONG_GROUP = 100
DEFAULT_MAX_NAME_BUCKET = 200
DEFAULT_MAX_SPATIAL_BUCKET = 200
DEFAULT_MAX_PAIR_COMPARISONS = 250_000

UF_ALIASES = {
    "acre": "AC", "ac": "AC", "alagoas": "AL", "al": "AL", "amapa": "AP", "ap": "AP",
    "amazonas": "AM", "am": "AM", "bahia": "BA", "ba": "BA", "ceara": "CE", "ce": "CE",
    "distrito federal": "DF", "df": "DF", "espirito santo": "ES", "es": "ES", "goias": "GO", "go": "GO",
    "maranhao": "MA", "ma": "MA", "mato grosso": "MT", "mt": "MT", "mato grosso do sul": "MS", "ms": "MS",
    "minas gerais": "MG", "mg": "MG", "para": "PA", "pa": "PA", "paraiba": "PB", "pb": "PB",
    "parana": "PR", "pr": "PR", "pernambuco": "PE", "pe": "PE", "piaui": "PI", "pi": "PI",
    "rio de janeiro": "RJ", "rj": "RJ", "rio grande do norte": "RN", "rn": "RN",
    "rio grande do sul": "RS", "rs": "RS", "rondonia": "RO", "ro": "RO", "roraima": "RR", "rr": "RR",
    "santa catarina": "SC", "sc": "SC", "sao paulo": "SP", "sp": "SP", "sergipe": "SE", "se": "SE",
    "tocantins": "TO", "to": "TO",
}
PLACEHOLDER_NAMES = frozenset({
    "terreiro sem nome", "sem nome", "nao informado", "nao informada", "ignorado", "ignorada",
    "desconhecido", "desconhecida", "sem informacao", "nao identificado", "nao identificada", "n a",
})


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
    """Casefold, remove marcas combinantes e converte pontuação em espaços."""
    if not isinstance(value, str):
        return ""
    decomposed = unicodedata.normalize("NFKD", value).casefold()
    chars = []
    for char in decomposed:
        category = unicodedata.category(char)
        if category.startswith("M"):
            continue
        chars.append(char if category[0] in {"L", "N"} else " ")
    return " ".join("".join(chars).split())


def _normalize_legacy(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    text = "".join(char for char in decomposed if not unicodedata.category(char).startswith("M"))
    return " ".join(text.casefold().split())


def _canonical_uf(value: Any) -> str | None:
    return UF_ALIASES.get(_normalize(value))


@dataclass(frozen=True)
class MunicipalityIndex:
    by_code: dict[str, tuple[str, str]]
    by_name_uf: dict[tuple[str, str], str]
    by_siafi: dict[str, str]

    @classmethod
    def from_rows(cls, rows: Iterable[dict[str, Any]]) -> "MunicipalityIndex":
        by_code: dict[str, tuple[str, str]] = {}
        by_name_uf: dict[tuple[str, str], str] = {}
        by_siafi: dict[str, str] = {}
        for row in rows:
            code = str(row["codigo_ibge"]).strip()
            name = _normalize(row["nome"])
            uf = _canonical_uf(row["uf"])
            if not re.fullmatch(r"\d{7}", code) or not name or not uf:
                raise GenerationError("linha inválida no mapping IBGE")
            if code in by_code or (name, uf) in by_name_uf:
                raise GenerationError("chave duplicada no mapping IBGE")
            by_code[code] = (name, uf)
            by_name_uf[(name, uf)] = code
            siafi = str(row.get("codigo_siafi", "")).strip()
            if siafi:
                if not re.fullmatch(r"\d{4}", siafi) or siafi in by_siafi:
                    raise GenerationError("código SIAFI inválido ou duplicado no mapping")
                by_siafi[siafi] = code
        return cls(by_code, by_name_uf, by_siafi)

    @classmethod
    def empty(cls) -> "MunicipalityIndex":
        return cls({}, {}, {})

    @classmethod
    def load(cls, path: Path) -> "MunicipalityIndex":
        with path.open(encoding="utf-8", newline="") as handle:
            return cls.from_rows(csv.DictReader(handle))


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


def _municipality_key(record: dict[str, Any], index: MunicipalityIndex | None = None) -> tuple[str, str] | None:
    index = index or MunicipalityIndex.empty()
    location = record.get("localizacao_original", {})
    raw = record.get("dados_originais", {})
    uf = _canonical_uf(location.get("uf"))
    code_value = raw.get("codigo_municipio") if record.get("fonte") == "cnpj" else None
    if code_value not in (None, ""):
        code = str(code_value).strip()
        if re.fullmatch(r"\d{4}", code):
            code = index.by_siafi.get(code, "")
        mapped = index.by_code.get(code)
        return (code, mapped[1]) if mapped else None
    municipality = _normalize(location.get("municipio"))
    if not municipality or not uf:
        return None
    code = index.by_name_uf.get((municipality, uf))
    if code:
        return code, uf
    # Compatibilidade apenas para chamadas unitárias sem mapping. A CLI sempre exige o mapping oficial.
    if not index.by_code:
        return f"text:{municipality}", uf
    return None


def _geography_relation(left: dict[str, Any], right: dict[str, Any], index: MunicipalityIndex | None = None) -> tuple[str, list[str]]:
    left_key = _municipality_key(left, index)
    right_key = _municipality_key(right, index)
    left_uf = left_key[1] if left_key else _canonical_uf(left.get("localizacao_original", {}).get("uf"))
    right_uf = right_key[1] if right_key else _canonical_uf(right.get("localizacao_original", {}).get("uf"))
    negatives: list[str] = []
    if left_uf and right_uf and left_uf != right_uf:
        return "different", ["different_municipality", "different_uf"]
    if left_key and right_key:
        if left_key == right_key:
            return "same", negatives
        return "different", ["different_municipality"]
    return "unknown", negatives


def _coordinates(record: dict[str, Any]) -> tuple[float, float, str] | None:
    location = record.get("localizacao_original", {})
    latitude, longitude = location.get("latitude"), location.get("longitude")
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
    delta_lat = math.radians(right[0] - left[0])
    delta_lon = math.radians(right[1] - left[1])
    haversine = math.sin(delta_lat / 2) ** 2 + math.cos(math.radians(left[0])) * math.cos(math.radians(right[0])) * math.sin(delta_lon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(haversine)))


def _distance_bucket(distance: float) -> str:
    return "0-25m" if distance <= 25 else "25-100m" if distance <= 100 else "100-500m"


def _jaccard(left: Any, right: Any) -> float:
    left_tokens, right_tokens = set(_normalize(left).split()), set(_normalize(right).split())
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens) if left_tokens and right_tokens else 0.0


def _occurrence_ref(source_record_key: str) -> str:
    return hashlib.sha256(f"{OCCURRENCE_REF_PROTOCOL}\0{source_record_key}".encode()).hexdigest()


def _pair_key(left_ref: str, right_ref: str) -> str:
    left_ref, right_ref = sorted((left_ref, right_ref))
    digest = hashlib.sha256(f"{PROTOCOL}\0{left_ref}\0{right_ref}".encode()).hexdigest()
    return f"dedupv3:{digest}"


def _component_key(pair_key: str) -> str:
    digest = hashlib.sha256(f"dedup-component-v3\0{pair_key}".encode()).hexdigest()
    return f"dedup-component-v3:{digest}"


def _evidence(evidence_type: str, provenance: str, authority: str, *, score: float | None = None, distance_bucket: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"type": evidence_type, "provenance": provenance, "authority": authority}
    if score is not None:
        item["score"] = round(score, 3)
    if distance_bucket is not None:
        item["distance_bucket"] = distance_bucket
    return item


def _evidence_identity(item: dict[str, Any]) -> str:
    return json.dumps(item, sort_keys=True, separators=(",", ":"))


def generate_candidates(
    records: list[dict[str, Any]], *, municipality_index: MunicipalityIndex | None = None,
    max_strong_group: int = DEFAULT_MAX_STRONG_GROUP, max_name_bucket: int = DEFAULT_MAX_NAME_BUCKET,
    max_spatial_bucket: int = DEFAULT_MAX_SPATIAL_BUCKET, max_pair_comparisons: int = DEFAULT_MAX_PAIR_COMPARISONS,
) -> dict[str, Any]:
    """Gera pares preservadores com orçamentos explícitos e componentes por par."""
    municipality_index = municipality_index or MunicipalityIndex.empty()
    ordered = sorted(records, key=lambda row: row["source_record_key"])
    by_key = {row["source_record_key"]: row for row in ordered}
    if len(by_key) != len(ordered):
        raise GenerationError("source_record_key duplicada")
    refs = {key: _occurrence_ref(key) for key in by_key}
    candidates: dict[tuple[str, str], dict[str, Any]] = {}
    pair_modes: dict[tuple[str, str], set[str]] = defaultdict(set)
    comparisons = 0

    def add_pair(left: dict[str, Any], right: dict[str, Any], evidence: dict[str, Any], mode: str) -> None:
        nonlocal comparisons
        left_key, right_key = sorted((left["source_record_key"], right["source_record_key"]), key=lambda key: refs[key])
        key = (left_key, right_key)
        left_ref, right_ref = refs[left_key], refs[right_key]
        pair_id = _pair_key(left_ref, right_ref)
        item = candidates.setdefault(key, {
            "candidate_pair_key": pair_id, "left_occurrence_ref": left_ref, "right_occurrence_ref": right_ref,
            "left_source": by_key[left_key]["fonte"], "right_source": by_key[right_key]["fonte"],
            "evidence": [], "negative_evidence": [], "suggested_relation": "unresolved", "review_status": "pending",
            "candidate_component_key": _component_key(pair_id), "conflicting_pair_keys": [], "canonical_entity_created": False,
        })
        identity = _evidence_identity(evidence)
        if identity not in {_evidence_identity(existing) for existing in item["evidence"]}:
            item["evidence"].append(evidence)
        pair_modes[key].add(mode)

    cnpj_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    native_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    name_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    coordinates: dict[str, tuple[float, float, str]] = {}
    coordinate_groups: dict[tuple[float, float], list[str]] = defaultdict(list)
    placeholder_count = 0
    for record in ordered:
        if cnpj := _valid_cnpj(record.get("identificadores", {}).get("cnpj")):
            cnpj_groups[cnpj].append(record)
        native_id = record.get("id_fonte")
        if native_id and not record.get("id_fonte_sintetico", False):
            native_groups[(record["fonte"], str(native_id))].append(record)
        name = _normalize(record.get("nome_original"))
        if name in PLACEHOLDER_NAMES:
            placeholder_count += 1
        elif name:
            name_groups[name].append(record)
        if coordinate := _coordinates(record):
            coordinates[record["source_record_key"]] = coordinate
            coordinate_groups[coordinate[:2]].append(record["source_record_key"])

    for label, groups in (("CNPJ", cnpj_groups), ("ID forte", native_groups)):
        for group in groups.values():
            if len(group) > max_strong_group:
                raise GenerationError(f"grupo de {label} acima do limite: {len(group)} > {max_strong_group}")
    for group in cnpj_groups.values():
        for left, right in combinations(group, 2):
            add_pair(left, right, _evidence("exact_cnpj", "promoted_identifier", "source_native", score=1.0), "strong")

    conflicted_native_groups: list[set[str]] = []
    for group in native_groups.values():
        cnpjs = {_valid_cnpj(row.get("identificadores", {}).get("cnpj")) for row in group}
        cnpjs.discard(None)
        if len(cnpjs) > 1:
            conflicted_native_groups.append({row["source_record_key"] for row in group})
        for left, right in combinations(group, 2):
            add_pair(left, right, _evidence("exact_native_id", "source_namespace", "source_native", score=1.0), "strong")

    geographic_homonym_pairs = exact_same_municipality = exact_cross_groups = exact_cross_pairs = 0
    oversized_name_groups = oversized_name_pairs = name_comparisons = 0
    for group in name_groups.values():
        if len(group) < 2:
            continue
        source_counts = Counter(row["fonte"] for row in group)
        cross_pairs = len(group) * (len(group) - 1) // 2 - sum(n * (n - 1) // 2 for n in source_counts.values())
        if cross_pairs:
            exact_cross_groups += 1
            exact_cross_pairs += cross_pairs
        partitions: dict[tuple[str, str] | None, list[dict[str, Any]]] = defaultdict(list)
        for row in group:
            partitions[_municipality_key(row, municipality_index)].append(row)
        for bucket_key, bucket in partitions.items():
            if len(bucket) < 2:
                continue
            if len(bucket) > max_name_bucket:
                oversized_name_groups += 1
                oversized_name_pairs += len(bucket) * (len(bucket) - 1) // 2
                continue
            for left, right in combinations(bucket, 2):
                name_comparisons += 1
                comparisons += 1
                if comparisons > max_pair_comparisons:
                    raise GenerationError("orçamento global de comparações excedido")
                geography, _ = _geography_relation(left, right, municipality_index)
                cross_source = left["fonte"] != right["fonte"]
                if geography == "same":
                    exact_same_municipality += 1
                    add_pair(left, right, _evidence("exact_name", "normalized_name", "declared", score=1.0), "weak")
                elif geography == "unknown" and cross_source:
                    add_pair(left, right, _evidence("exact_name", "normalized_name", "declared", score=1.0), "unresolved")
        if len(group) <= max_name_bucket:
            for left, right in combinations(group, 2):
                if _geography_relation(left, right, municipality_index)[0] == "different":
                    geographic_homonym_pairs += 1

    spatial_buckets: dict[tuple[tuple[str, str], int, int], list[str]] = defaultdict(list)
    for record in ordered:
        key, coordinate = record["source_record_key"], coordinates.get(record["source_record_key"])
        municipality = _municipality_key(record, municipality_index)
        if coordinate and municipality:
            x = EARTH_RADIUS_M * math.radians(coordinate[1]) * math.cos(math.radians(coordinate[0]))
            y = EARTH_RADIUS_M * math.radians(coordinate[0])
            spatial_buckets[(municipality, math.floor(x / CELL_SIZE_M), math.floor(y / CELL_SIZE_M))].append(key)
    oversized_spatial_buckets = sum(len(group) > max_spatial_bucket for group in spatial_buckets.values())
    seen_spatial: set[tuple[str, str]] = set()
    proximity_pairs = spatial_comparisons = 0
    for (municipality, bx, by), left_keys in spatial_buckets.items():
        if len(left_keys) > max_spatial_bucket:
            continue
        nearby: list[str] = []
        skip = False
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                group = spatial_buckets.get((municipality, bx + dx, by + dy), [])
                if len(group) > max_spatial_bucket:
                    skip = True
                nearby.extend(group)
        if skip:
            continue
        for left_key in left_keys:
            for right_key in nearby:
                pair = tuple(sorted((left_key, right_key)))
                if left_key == right_key or pair in seen_spatial:
                    continue
                seen_spatial.add(pair)
                spatial_comparisons += 1
                comparisons += 1
                if comparisons > max_pair_comparisons:
                    raise GenerationError("orçamento global de comparações excedido")
                left, right = by_key[pair[0]], by_key[pair[1]]
                similarity = _jaccard(left.get("nome_original"), right.get("nome_original"))
                if similarity < 0.8:
                    continue
                distance = _distance_m(coordinates[left_key][:2], coordinates[right_key][:2])
                if distance > 500:
                    continue
                proximity_pairs += 1
                authority = "geocoder_auxiliary" if "geocoder_auxiliary" in (coordinates[left_key][2], coordinates[right_key][2]) else "declared"
                add_pair(left, right, _evidence("name_similarity", "normalized_name_tokens", "derived", score=similarity), "weak")
                add_pair(left, right, _evidence("distance", "derived_spatial_grid", authority, distance_bucket=_distance_bucket(distance)), "weak")

    collapsed = {key for group in coordinate_groups.values() if len(group) >= 3 for key in group}
    conflict_keys: dict[str, set[str]] = defaultdict(set)
    for group_keys in conflicted_native_groups:
        group_pair_ids = {item["candidate_pair_key"] for key, item in candidates.items() if set(key) <= group_keys}
        for key in group_keys:
            conflict_keys[key].update(group_pair_ids)

    for key, candidate in candidates.items():
        left, right = by_key[key[0]], by_key[key[1]]
        geography, geography_negatives = _geography_relation(left, right, municipality_index)
        negatives = set(geography_negatives)
        left_cnpj = _valid_cnpj(left.get("identificadores", {}).get("cnpj"))
        right_cnpj = _valid_cnpj(right.get("identificadores", {}).get("cnpj"))
        different_cnpj = bool(left_cnpj and right_cnpj and left_cnpj != right_cnpj)
        strong_conflict = bool(conflict_keys[key[0]] or conflict_keys[key[1]])
        if different_cnpj:
            negatives.add("different_cnpj")
        if strong_conflict:
            negatives.add("strong_id_conflict")
        if key[0] in collapsed and key[1] in collapsed and coordinates.get(key[0], ())[:2] == coordinates.get(key[1], ())[:2]:
            negatives.add("collapsed_coordinate")
        if different_cnpj:
            candidate["suggested_relation"], candidate["review_status"] = "distinct_entities", "rejected"
        elif strong_conflict:
            candidate["suggested_relation"] = "unresolved"
        elif "strong" in pair_modes[key]:
            coordinate_distance = None
            if key[0] in coordinates and key[1] in coordinates:
                coordinate_distance = _distance_m(coordinates[key[0]][:2], coordinates[key[1]][:2])
            positive_same_location = geography == "same" or (coordinate_distance is not None and coordinate_distance <= 500)
            moved = geography == "different" or (coordinate_distance is not None and coordinate_distance > 500)
            candidate["suggested_relation"] = "possible_same_entity_moved" if moved else "same_entity_same_location" if positive_same_location else "possible_same_entity"
            candidate["review_status"] = "auto_linked_strong_id"
        elif "weak" in pair_modes[key]:
            candidate["suggested_relation"] = "possible_same_entity"
        candidate["evidence"].sort(key=lambda item: (item["type"], _evidence_identity(item)))
        candidate["negative_evidence"] = [{"type": item} for item in sorted(negatives)]
        candidate["conflicting_pair_keys"] = sorted((conflict_keys[key[0]] | conflict_keys[key[1]]) - {candidate["candidate_pair_key"]})

    candidate_pairs = sorted(candidates.values(), key=lambda item: item["candidate_pair_key"])
    municipality_name_counts = Counter((_normalize(row.get("nome_original")), _municipality_key(row, municipality_index)) for row in records if _normalize(row.get("nome_original")) not in PLACEHOLDER_NAMES and _municipality_key(row, municipality_index))
    metrics = {
        "occurrences_preserved": len(records), "records_with_name": sum(bool(_normalize(row.get("nome_original"))) for row in records),
        "placeholder_name_records": placeholder_count, "exact_name_groups_overall": sum(len(group) > 1 for group in name_groups.values()),
        "exact_name_cross_source_groups": exact_cross_groups, "exact_name_cross_source_pairs": exact_cross_pairs,
        "exact_name_groups_same_municipality": sum(count > 1 for count in municipality_name_counts.values()),
        "exact_name_pairs_same_municipality": exact_same_municipality, "geographic_homonym_pairs": geographic_homonym_pairs,
        "proximity_name_compatible_pairs": proximity_pairs, "collapsed_coordinate_groups": sum(len(group) >= 3 for group in coordinate_groups.values()),
        "candidate_components": len(candidate_pairs), "candidate_component_records": len(candidate_pairs) * 2,
        "name_pair_comparisons": name_comparisons, "spatial_pair_comparisons": spatial_comparisons,
        "oversized_name_groups": oversized_name_groups, "oversized_name_theoretical_pairs": oversized_name_pairs,
        "oversized_spatial_buckets": oversized_spatial_buckets, "pair_comparison_budget": max_pair_comparisons,
    }
    return {"candidate_pairs": candidate_pairs, "metrics": metrics}


def _legacy_location_key(row: dict[str, Any]) -> tuple[str, str, float, float] | None:
    aliases = {"google places": "google"}
    source = aliases.get(_normalize_legacy(row.get("fonte")), _normalize_legacy(row.get("fonte")))
    latitude, longitude, name = row.get("lat", row.get("latitude")), row.get("lng", row.get("longitude")), row.get("nome")
    if not source or not name or latitude in (None, "") or longitude in (None, ""):
        return None
    return source, _normalize_legacy(name), round(float(latitude), 6), round(float(longitude), 6)


def _original_stable_key(row: dict[str, Any]) -> str:
    from src.audit.legacy_ledgers import build_stable_identity
    return build_stable_identity(row)["stable_key"]


def _reconcile_ledger(records: list[dict[str, Any]], curated_path: Path, original_path: Path) -> tuple[dict[str, str], dict[str, int]]:
    with curated_path.open(encoding="utf-8", newline="") as handle:
        curated = list(csv.DictReader(handle))
    with original_path.open(encoding="utf-8", newline="") as handle:
        original = list(csv.DictReader(handle))
    if len({row["stable_key"] for row in curated}) != len(curated):
        raise GenerationError("stable_key duplicada no ledger curado")
    original_by_stable: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in original:
        original_by_stable[_original_stable_key(row)].append(row)
    by_cnpj: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_location: dict[tuple[str, str, float, float], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if cnpj := _valid_cnpj(record.get("identificadores", {}).get("cnpj")):
            by_cnpj[f"cnpj:{cnpj}"].append(record)
        if location := _legacy_location_key(record.get("dados_originais", {})):
            by_location[location].append(record)
    matched: dict[str, str] = {}
    counts = Counter()
    for row in curated:
        originals = original_by_stable.get(row["stable_key"], [])
        if len(originals) != 1:
            counts["bridge_original_missing" if not originals else "bridge_original_ambiguous"] += 1
            matches = []
        elif row.get("identity_synthetic") == "false":
            matches = by_cnpj.get(row["stable_key"], [])
        else:
            location = _legacy_location_key(originals[0])
            matches = by_location.get(location, []) if location else []
        if len(matches) == 1:
            counts["matched"] += 1
            matched[matches[0]["source_record_key"]] = "curated-exclusion-v3:" + hashlib.sha256(row["stable_key"].encode()).hexdigest()
        elif not matches:
            counts["absent"] += 1
        else:
            counts["ambiguous"] += 1
    counts["rows"] = len(curated)
    for field in ("matched", "absent", "ambiguous", "bridge_original_missing", "bridge_original_ambiguous"):
        counts.setdefault(field, 0)
    if counts["matched"] + counts["absent"] + counts["ambiguous"] != len(curated):
        raise GenerationError("equação do ledger curado não fecha")
    return matched, dict(counts)


def _jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n" for row in rows).encode()


def _validate_rows(rows: list[dict[str, Any]], schema_path: Path, label: str, *, semantic_source_key: bool = False) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    for index, row in enumerate(rows):
        errors = sorted(validator.iter_errors(row), key=lambda error: list(error.path))
        if errors:
            raise GenerationError(f"{label} fora do schema no índice {index}: {errors[0].json_path}")
        if semantic_source_key and row["source_record_key"] != make_source_record_key(row["fonte"], row["id_fonte"]):
            raise GenerationError(f"source-record com chave semântica inválida no índice {index}")


def _load_validated_source(source_path: Path, manifest_path: Path, source_schema_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = manifest.get("jsonl", {})
    if _sha256_file(source_path) != expected.get("sha256") or source_path.stat().st_size != expected.get("bytes"):
        raise GenerationError("hash ou bytes do source_records.jsonl divergentes")
    with source_path.open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle]
    if len(records) != manifest.get("total") or dict(Counter(row.get("fonte") for row in records)) != manifest.get("counts"):
        raise GenerationError("contagens do source_records.jsonl divergentes")
    _validate_rows(records, source_schema_path, "source-record", semantic_source_key=True)
    return records, manifest


def _write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.tmp-{uuid.uuid4().hex}"
    try:
        with temporary.open("xb") as handle:
            handle.write(content); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _publish_release(release_root: Path, pointer_path: Path, release_id: str, files: dict[str, bytes]) -> Path:
    release = release_root / release_id
    if release.exists():
        existing = {path.name: path.read_bytes() for path in release.iterdir() if path.is_file()}
        if existing != files:
            raise GenerationError("release_id existente com conteúdo divergente")
    else:
        temporary = release_root / f".{release_id}.tmp-{uuid.uuid4().hex}"
        temporary.mkdir(parents=True, exist_ok=False)
        try:
            for name, content in files.items():
                path = temporary / name
                with path.open("xb") as handle:
                    handle.write(content); handle.flush(); os.fsync(handle.fileno())
            os.replace(temporary, release)
        finally:
            shutil.rmtree(temporary, ignore_errors=True)
    pointer = (json.dumps({"protocol_version": PROTOCOL, "release_id": release_id, "release_path": str(release.relative_to(pointer_path.parent.parent.parent.parent))}, sort_keys=True, indent=2) + "\n").encode()
    _write_atomic(pointer_path, pointer)
    return release


def _assert_inside(root: Path, path: Path, label: str, *, allow_symlink: bool = False) -> Path:
    root = root.resolve()
    lexical = Path(os.path.abspath(path))
    try:
        lexical.relative_to(root)
    except ValueError as error:
        raise GenerationError(f"{label} fora do root") from error
    if not allow_symlink:
        try:
            lexical.resolve().relative_to(root)
        except ValueError as error:
            raise GenerationError(f"{label} escapa do root por symlink") from error
    return lexical


def build_dedup_candidates(
    *, root: Path, candidate_schema_path: Path, source_path: Path, source_manifest_path: Path,
    curated_ledger_path: Path, original_ledger_path: Path, candidate_output_path: Path, status_output_path: Path,
    summary_output_path: Path, source_schema_path: Path | None = None, status_schema_path: Path | None = None,
    summary_schema_path: Path | None = None, municipality_mapping_path: Path | None = None,
    release_root_path: Path | None = None, pointer_output_path: Path | None = None, allow_input_symlink: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    source_schema_path = source_schema_path or candidate_schema_path.parent / "source-record-v3.schema.json"
    status_schema_path = status_schema_path or candidate_schema_path.parent / "dedup-occurrence-status-v3.schema.json"
    summary_schema_path = summary_schema_path or candidate_schema_path.parent / "dedup-summary-v3.schema.json"
    inputs = [candidate_schema_path, source_schema_path, status_schema_path, summary_schema_path, source_manifest_path, curated_ledger_path, original_ledger_path]
    inputs = [_assert_inside(root, Path(path), "input") for path in inputs]
    source_path = _assert_inside(root, Path(source_path), "source-records", allow_symlink=allow_input_symlink)
    outputs = [_assert_inside(root, Path(path), "output") for path in (candidate_output_path, status_output_path, summary_output_path)]
    if len(set(outputs)) != len(outputs) or any(output in inputs + [source_path] for output in outputs):
        raise GenerationError("destinos duplicados ou sobrepostos a inputs")
    mapping = MunicipalityIndex.empty()
    if municipality_mapping_path is not None:
        mapping_path = _assert_inside(root, Path(municipality_mapping_path), "mapping")
        if mapping_path in outputs:
            raise GenerationError("output sobrepõe mapping")
        mapping = MunicipalityIndex.load(mapping_path)
    records, manifest = _load_validated_source(source_path, Path(source_manifest_path), Path(source_schema_path))
    generated = generate_candidates(records, municipality_index=mapping)
    _validate_rows(generated["candidate_pairs"], Path(candidate_schema_path), "candidato")
    matched, ledger_counts = _reconcile_ledger(records, Path(curated_ledger_path), Path(original_ledger_path))
    statuses = []
    for record in sorted(records, key=lambda row: _occurrence_ref(row["source_record_key"])):
        reference = matched.get(record["source_record_key"])
        statuses.append({"occurrence_ref": _occurrence_ref(record["source_record_key"]), "fonte": record["fonte"], "exclusao_curada": reference is not None, "ledger_refs": [reference] if reference else [], "status": "preserved_curated_exclusion" if reference else "preserved"})
    _validate_rows(statuses, Path(status_schema_path), "status")
    candidate_bytes, status_bytes = _jsonl_bytes(generated["candidate_pairs"]), _jsonl_bytes(statuses)
    relation_counts = Counter(row["suggested_relation"] for row in generated["candidate_pairs"])
    review_counts = Counter(row["review_status"] for row in generated["candidate_pairs"])
    evidence_counts = Counter(item["type"] for row in generated["candidate_pairs"] for item in row["evidence"])
    negative_counts = Counter(item["type"] for row in generated["candidate_pairs"] for item in row["negative_evidence"])
    summary = {
        "protocol_version": PROTOCOL,
        "input": {"sha256": manifest["jsonl"]["sha256"], "bytes": manifest["jsonl"]["bytes"], "occurrences": manifest["total"], "counts_by_source": manifest["counts"]},
        "outputs": {"candidates": {"sha256": _sha256_bytes(candidate_bytes), "bytes": len(candidate_bytes), "lines": len(generated["candidate_pairs"])}, "occurrence_status": {"sha256": _sha256_bytes(status_bytes), "bytes": len(status_bytes), "lines": len(statuses)}},
        "candidate_counts": {"total": len(generated["candidate_pairs"]), "by_relation": dict(sorted(relation_counts.items())), "by_review_status": dict(sorted(review_counts.items())), "by_evidence": dict(sorted(evidence_counts.items())), "by_negative_evidence": dict(sorted(negative_counts.items()))},
        "metrics": generated["metrics"], "curated_exclusions": ledger_counts,
        "equations": {"occurrences_preserved": f"{len(statuses)} = {len(records)}", "curated_ledger": f"{ledger_counts['matched']} + {ledger_counts['absent']} + {ledger_counts['ambiguous']} = {ledger_counts['rows']}", "candidate_relations": f"{sum(relation_counts.values())} = {len(generated['candidate_pairs'])}"},
        "canonical_entities_created": 0,
        "privacy": {"occurrence_ref_protocol": "sha256(occurrence-ref-v1\\0source_record_key)", "source_record_key_published": False},
        "metric_change": {
            "candidate_pairs_before_d2": 567,
            "candidate_pairs_without_siafi_bridge": 352,
            "historical_geographic_homonym_pairs": 1193,
            "historical_incomparable_ibge_text_pairs": 39,
            "description": "Os 567 pares anteriores usavam a semântica pré-D2. O resultado intermediário de 352 pares já harmonizava IBGE e texto, mas interpretava o código municipal de quatro dígitos do CNPJ como IBGE e deixava essa geografia desconhecida. A ponte oficial SIAFI→IBGE restaura as comparações municipais válidas; os demais controles D2 continuam ativos.",
        },
    }
    _validate_rows([summary], Path(summary_schema_path), "summary")
    summary_bytes = (json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    if release_root_path is not None and pointer_output_path is not None:
        release_root = _assert_inside(root, Path(release_root_path), "release root")
        pointer = _assert_inside(root, Path(pointer_output_path), "pointer")
        release_id = hashlib.sha256(candidate_bytes + status_bytes + summary_bytes).hexdigest()[:20]
        release = _publish_release(release_root, pointer, release_id, {"dedup_candidates.jsonl": candidate_bytes, "dedup_occurrence_status.jsonl": status_bytes, "dedup_summary.json": summary_bytes})
        _write_atomic(Path(summary_output_path), summary_bytes)
        summary["release"] = {"release_id": release_id, "path": str(release)}
    else:
        for path, content in zip(outputs, (candidate_bytes, status_bytes, summary_bytes)):
            _write_atomic(path, content)
    return summary


def _parser(root: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument("--source-records", type=Path)
    parser.add_argument("--allow-input-symlink", action="store_true")
    return parser


def _resolve_cli_paths(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    if args.source_records is not None and (args.source_records.is_absolute() or ".." in args.source_records.parts):
        raise GenerationError("--source-records deve ser relativo e sem '..'")
    source = root / (args.source_records or Path("data/processed/v3/source_records.jsonl"))
    return {
        "root": root, "candidate_schema_path": root / "schemas/dedup-candidate-v3.schema.json",
        "source_schema_path": root / "schemas/source-record-v3.schema.json", "status_schema_path": root / "schemas/dedup-occurrence-status-v3.schema.json",
        "summary_schema_path": root / "schemas/dedup-summary-v3.schema.json", "municipality_mapping_path": root / "config/ibge_municipios_2024.csv",
        "source_path": source, "source_manifest_path": root / "data/processed/v3/source_records.manifest.json",
        "curated_ledger_path": root / "data/audit/v3/exclusoes_curadas_v3.csv", "original_ledger_path": root / "data/exclusoes_curadas.csv",
        "candidate_output_path": root / "data/processed/v3/dedup_candidates.jsonl", "status_output_path": root / "data/processed/v3/dedup_occurrence_status.jsonl",
        "summary_output_path": root / "data/audit/v3/dedup_candidates_summary.json", "release_root_path": root / "data/processed/v3/dedup_releases",
        "pointer_output_path": root / "data/processed/v3/dedup_current.json", "allow_input_symlink": args.allow_input_symlink,
    }


def main() -> int:
    args = _parser(Path(__file__).resolve().parents[2]).parse_args()
    summary = build_dedup_candidates(**_resolve_cli_paths(args))
    print(f"ocorrências preservadas: {summary['input']['occurrences']}")
    print(f"candidatos: {summary['candidate_counts']['total']}")
    print(f"componentes: {summary['metrics']['candidate_components']}")
    print(f"relações: {json.dumps(summary['candidate_counts']['by_relation'], sort_keys=True)}")
    print(f"status: {json.dumps(summary['candidate_counts']['by_review_status'], sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
