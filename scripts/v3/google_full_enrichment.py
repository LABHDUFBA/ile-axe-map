#!/usr/bin/env python3
"""Google Places enrichment — full scale with quota cap.

Uses Text Search (legacy) + Place Details.
Prioritizes entities WITH coordinates (distance validation possible).
Stops at --max-calls to respect monthly quota.
Resumable: skips entity_ids already in cache.
"""

import json, sys, os, time, math, argparse
from pathlib import Path
from datetime import datetime, timezone

WORKTREE = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = WORKTREE / "data" / "processed" / "v3"
SAMPLE_FILE = CACHE_DIR / "google_national_remaining_v3.jsonl"
CACHE_FILE = CACHE_DIR / "google_full_results_v3.jsonl"

API_KEY = os.environ.get("GOOGLE_API_KEY") or ""
if not API_KEY:
    env_path = Path.home() / ".hermes" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("GOOGLE_API_KEY=") and not line.startswith("#"):
                API_KEY = line.split("=", 1)[1].strip()
                break

if not API_KEY:
    print("ERROR: GOOGLE_API_KEY not found", file=sys.stderr)
    sys.exit(1)

import urllib.request, urllib.parse

def google_text_search(query, timeout=10):
    base = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = urllib.parse.urlencode({"query": query, "key": API_KEY})
    url = f"{base}?{params}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"status": "ERROR", "error_message": str(e)}

def google_place_details(place_id, fields, timeout=10):
    base = "https://maps.googleapis.com/maps/api/place/details/json"
    params = urllib.parse.urlencode({
        "place_id": place_id,
        "fields": fields,
        "key": API_KEY,
    })
    url = f"{base}?{params}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"status": "ERROR", "error_message": str(e)}

def haversine(lat1, lng1, lat2, lng2):
    if None in (lat1, lng1, lat2, lng2):
        return None
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def load_cache():
    cache = {}
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            for line in f:
                rec = json.loads(line)
                cache[rec["entity_id"]] = rec
    return cache

def build_query(name, municipio, uf):
    parts = [name]
    if municipio and municipio not in ("?", "—"):
        parts.append(municipio)
    uf_clean = str(uf).strip()
    if uf_clean and len(uf_clean) == 2 and uf_clean.isalpha():
        parts.append(uf_clean)
    parts.append("Brasil")
    return " ".join(parts)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-calls", type=int, default=3500,
                        help="Max API calls (default 3500)")
    parser.add_argument("--delay", type=float, default=0.25,
                        help="Delay between entities in seconds")
    args = parser.parse_args()

    sample = []
    with open(SAMPLE_FILE) as f:
        for line in f:
            sample.append(json.loads(line))

    # Sort: entities with coords first (can validate distance), then by name length desc
    sample.sort(key=lambda x: (
        0 if x.get("coords") else 1,
        -len(x.get("name", "")),
    ))

    cache = load_cache()
    print(f"Sample: {len(sample)} entities")
    print(f"Cache: {len(cache)} existing")
    print(f"Max API calls: {args.max_calls}")

    DETAIL_FIELDS = "name,formatted_address,geometry,place_id,rating,user_ratings_total,formatted_phone_number,international_phone_number,website,opening_hours,business_status,address_components"

    api_calls = 0
    processed = 0
    found = 0
    false_pos = 0
    not_found = 0
    errors = 0
    stopped = False

    for item in sample:
        if api_calls >= args.max_calls:
            stopped = True
            break

        eid = item["entity_id"]
        if eid in cache:
            continue

        name = item.get("name", "")
        mun = item.get("municipio", "")
        uf = item.get("uf", "")
        coords = item.get("coords")

        if not name or name == "—":
            result = {
                "entity_id": eid,
                "query": "",
                "status": "no_name",
                "enriched_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(CACHE_FILE, "a") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
            cache[eid] = result
            not_found += 1
            processed += 1
            continue

        query = build_query(name, mun, uf)

        ts = google_text_search(query)
        api_calls += 1

        if ts.get("status") != "OK":
            result = {
                "entity_id": eid,
                "query": query,
                "status": "search_failed",
                "search_status": ts.get("status", "UNKNOWN"),
                "enriched_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(CACHE_FILE, "a") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
            cache[eid] = result
            errors += 1
            processed += 1
            continue

        results_list = ts.get("results", [])
        if not results_list:
            result = {
                "entity_id": eid,
                "query": query,
                "status": "zero_results",
                "enriched_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(CACHE_FILE, "a") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
            cache[eid] = result
            not_found += 1
            processed += 1
            continue

        top = results_list[0]
        place_id = top.get("place_id")
        g_name = top.get("name", "")
        g_addr = top.get("formatted_address", "")
        gloc = top.get("geometry", {}).get("location", {})
        g_lat = gloc.get("lat")
        g_lng = gloc.get("lng")

        dist = None
        if coords and g_lat and g_lng:
            dist = haversine(coords[0], coords[1], g_lat, g_lng)

        # Filter: if distance > 50km, it's likely a false positive
        match_quality = "valid"
        if dist and dist > 50000:
            match_quality = "false_positive"

        # Only call Place Details for valid matches (save quota)
        if match_quality == "valid" and api_calls < args.max_calls:
            pd = google_place_details(place_id, DETAIL_FIELDS)
            api_calls += 1
            pd_result = pd.get("result", {})
        else:
            pd_result = {}

        result = {
            "entity_id": eid,
            "query": query,
            "status": "found" if match_quality == "valid" else "false_positive",
            "match_quality": match_quality,
            "search_status": "OK",
            "place_id": place_id,
            "google_name": g_name,
            "google_address": g_addr,
            "google_lat": g_lat,
            "google_lng": g_lng,
            "distance_m": round(dist, 1) if dist else None,
            "rating": pd_result.get("rating"),
            "user_ratings_total": pd_result.get("user_ratings_total"),
            "phone": pd_result.get("formatted_phone_number"),
            "international_phone": pd_result.get("international_phone_number"),
            "website": pd_result.get("website"),
            "business_status": pd_result.get("business_status"),
            "original_name": name,
            "original_uf": uf,
            "original_municipio": mun,
            "original_coords": coords,
            "stratum": item.get("stratum"),
            "enriched_at": datetime.now(timezone.utc).isoformat(),
        }

        with open(CACHE_FILE, "a") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
        cache[eid] = result

        if match_quality == "valid":
            found += 1
        else:
            false_pos += 1

        processed += 1

        if processed % 50 == 0:
            print(f"  [{processed}] calls={api_calls} found={found} fp={false_pos} nf={not_found} err={errors}")

        time.sleep(args.delay)

    print(f"\n=== BATCH COMPLETE ===")
    print(f"Processed: {processed}")
    print(f"  Found (valid): {found}")
    print(f"  False positive (>50km): {false_pos}")
    print(f"  Not found: {not_found}")
    print(f"  Errors: {errors}")
    print(f"  API calls: {api_calls}")
    print(f"  Cache total: {len(cache)}")
    if stopped:
        remaining = len(sample) - len(cache)
        print(f"  STOPPED at quota cap — {remaining} entities remaining")
    print(f"  Results: {CACHE_FILE}")

if __name__ == "__main__":
    main()