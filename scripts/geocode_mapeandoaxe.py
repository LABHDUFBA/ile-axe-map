#!/usr/bin/env python3
"""Geocodifica a coleta Mapeando o Axé sem enviar dados pessoais."""

import json
import re
import time
import unicodedata
from difflib import SequenceMatcher
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    return re.sub(r"[^a-z0-9]", "", value.encode("ascii", "ignore").decode().lower())


def build_query(record: dict) -> str:
    fields = [
        record.get("address_raw", ""),
        record.get("city", ""),
        record.get("state", ""),
        record.get("postcode", ""),
        "Brasil",
    ]
    return ", ".join(value.strip() for value in fields if value and value.strip())


def build_simplified_query(record: dict) -> str:
    parts = [part.strip() for part in record.get("address_raw", "").split(",") if part.strip()]
    street = parts[0] if parts else ""
    number = ""
    if len(parts) > 1 and not re.match(r"^(qd|quadra|lote)\b", parts[1], re.I):
        match = re.search(r"(?<!\d)(\d{1,6})(?!\d)", parts[1])
        if match:
            number = match.group(1)
    fields = [street, number, record.get("city", ""), record.get("state", ""), "Brasil"]
    return ", ".join(value.strip() for value in fields if value and value.strip())


def candidate_precision(record: dict, candidate: dict) -> str:
    parts = [part.strip() for part in record.get("address_raw", "").split(",") if part.strip()]
    source_street = normalize(parts[0] if parts else "")
    address = candidate.get("address", {})
    returned_street = normalize(address.get("road") or address.get("pedestrian") or "")
    street_match = bool(returned_street and SequenceMatcher(None, source_street, returned_street).ratio() >= 0.75)
    if not street_match:
        return "city"
    source_number = ""
    if len(parts) > 1 and not re.match(r"^(qd|quadra|lote)\b", parts[1], re.I):
        match = re.search(r"(?<!\d)(\d{1,6})(?!\d)", parts[1])
        if match:
            source_number = match.group(1)
    returned_number = re.sub(r"\D", "", str(address.get("house_number", "")))
    if source_number and returned_number == source_number:
        return "house_number"
    return "street"


def evaluate_candidate(record: dict, candidate: dict) -> dict:
    address = candidate.get("address", {})
    returned_city = next(
        (address.get(key, "") for key in ("city", "municipality", "town", "village") if address.get(key)),
        "",
    )
    iso = address.get("ISO3166-2-lvl4", "")
    returned_state = iso.rsplit("-", 1)[-1] if iso.startswith("BR-") else ""
    city_match = normalize(record.get("city", "")) == normalize(returned_city)
    state_match = record.get("state", "").upper() == returned_state.upper()
    postcode_match = normalize(record.get("postcode", "")) == normalize(address.get("postcode", ""))
    country_match = address.get("country_code", "").lower() == "br"
    confidence = (
        (0.4 if city_match else 0)
        + (0.35 if state_match else 0)
        + (0.2 if postcode_match else 0)
        + min(float(candidate.get("importance", 0) or 0), 0.05)
    )
    return {
        "accepted": bool(country_match and state_match and city_match),
        "confidence": round(confidence, 3),
        "city_match": city_match,
        "state_match": state_match,
        "postcode_match": postcode_match,
    }


def geocode_record(record: dict, search) -> dict:
    query = build_query(record)
    evaluated = []
    for candidate in search(query):
        assessment = evaluate_candidate(record, candidate)
        if assessment["accepted"]:
            evaluated.append((assessment["confidence"], candidate, assessment))
    if not evaluated:
        return {
            "source_record_id": record["source_record_id"],
            "query": query,
            "status": "no_match",
        }
    _, candidate, assessment = max(evaluated, key=lambda item: item[0])
    return {
        "source_record_id": record["source_record_id"],
        "query": query,
        "status": "matched",
        "latitude": float(candidate["lat"]),
        "longitude": float(candidate["lon"]),
        "display_name": candidate.get("display_name", ""),
        "osm_type": candidate.get("osm_type", ""),
        "osm_id": candidate.get("osm_id"),
        **assessment,
    }


def geocode_record_v2(record: dict, search) -> dict:
    query = build_simplified_query(record)
    evaluated = []
    rank = {"house_number": 2, "street": 1, "city": 0}
    for candidate in search(query):
        assessment = evaluate_candidate(record, candidate)
        precision = candidate_precision(record, candidate)
        if assessment["accepted"] and precision != "city":
            evaluated.append((rank[precision], assessment["confidence"], candidate, assessment, precision))
    if not evaluated:
        return {"source_record_id": record["source_record_id"], "query": query, "status": "no_match"}
    _, _, candidate, assessment, precision = max(evaluated, key=lambda item: (item[0], item[1]))
    return {
        "source_record_id": record["source_record_id"],
        "query": query,
        "status": "matched",
        "precision": precision,
        "latitude": float(candidate["lat"]),
        "longitude": float(candidate["lon"]),
        "display_name": candidate.get("display_name", ""),
        "osm_type": candidate.get("osm_type", ""),
        "osm_id": candidate.get("osm_id"),
        "nominatim_type": candidate.get("type", ""),
        "addresstype": candidate.get("addresstype", ""),
        **assessment,
    }


def nominatim_search(query: str, opener=urlopen) -> list[dict]:
    params = urlencode({
        "q": query,
        "format": "jsonv2",
        "addressdetails": 1,
        "countrycodes": "br",
        "limit": 5,
    })
    request = Request(
        f"https://nominatim.openstreetmap.org/search?{params}",
        headers={"User-Agent": "IleAxeMap/1.0 (https://leofn.com; academic research)"},
    )
    with opener(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def run_batch(records: list[dict], cache_path, search, delay: float = 1.1, geocode_fn=geocode_record) -> dict:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cached_ids = set()
    if cache_path.exists():
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                cached_ids.add(str(json.loads(line)["source_record_id"]))
    pending = [record for record in records if str(record["source_record_id"]) not in cached_ids]
    processed = 0
    matched = 0
    errors = 0
    with cache_path.open("a", encoding="utf-8") as handle:
        for index, record in enumerate(pending):
            try:
                result = geocode_fn(record, search)
            except Exception:
                errors += 1
            else:
                handle.write(json.dumps(result, ensure_ascii=False) + "\n")
                handle.flush()
                processed += 1
                matched += result["status"] == "matched"
            if index + 1 < len(pending) and delay:
                time.sleep(delay)
    return {"processed": processed, "matched": matched, "errors": errors, "cached": len(cached_ids)}
