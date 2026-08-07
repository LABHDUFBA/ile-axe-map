#!/usr/bin/env python3
"""Google Places enrichment pilot — 100 stratified entities.

Uses Text Search (legacy) to find place_id, then Place Details for metadata.
FieldMask via `fields` parameter. Does NOT download photos.
Saves place_id, address, coordinates, rating, status, distance to original.

Cache: append-only JSONL, resume by entity_id.
Budget: ~200 API calls (100 text search + 100 place details).
"""

import json, sys, os, time, hashlib, math
from pathlib import Path
from datetime import datetime, timezone

WORKTREE = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = WORKTREE / "data" / "processed" / "v3"
SAMPLE_FILE = CACHE_DIR / "google_pilot_sample_v3.jsonl"
CACHE_FILE = CACHE_DIR / "google_pilot_results_v3.jsonl"

API_KEY = os.environ.get("GOOGLE_API_KEY") or ""
if not API_KEY:
    # Read from .env without sourcing
    env_path = Path.home() / ".hermes" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("GOOGLE_API_KEY=") and not line.startswith("#"):
                API_KEY = line.split("=", 1)[1].strip()
                break

if not API_KEY:
    print("ERROR: GOOGLE_API_KEY not found", file=sys.stderr)
    sys.exit(1)

import urllib.request, urllib.parse, urllib.error

def google_text_search(query, timeout=10):
    """Text Search (legacy) — returns list of results."""
    base = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = urllib.parse.urlencode({"query": query, "key": API_KEY})
    url = f"{base}?{params}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return data
    except Exception as e:
        return {"status": "ERROR", "error_message": str(e)}

def google_place_details(place_id, fields, timeout=10):
    """Place Details with FieldMask."""
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
            data = json.loads(resp.read())
            return data
    except Exception as e:
        return {"status": "ERROR", "error_message": str(e)}

def haversine(lat1, lng1, lat2, lng2):
    """Distance in meters."""
    if None in (lat1, lng1, lat2, lng2):
        return None
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def load_cache():
    """Load existing results by entity_id."""
    cache = {}
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            for line in f:
                rec = json.loads(line)
                cache[rec["entity_id"]] = rec
    return cache

def build_query(name, municipio, uf):
    """Build search query from entity info."""
    parts = [name]
    if municipio and municipio not in ("?", "—"):
        parts.append(municipio)
    # Normalize UF
    uf_clean = str(uf).strip()
    if uf_clean and len(uf_clean) == 2 and uf_clean.isalpha():
        parts.append(uf_clean)
    elif uf_clean and uf_clean not in ("?", "—"):
        # It's a code, not a UF — try to resolve via IBGE mapping
        # For now, skip it
        pass
    parts.append("Brasil")
    return " ".join(parts)

def main():
    # Load sample
    sample = []
    with open(SAMPLE_FILE) as f:
        for line in f:
            sample.append(json.loads(line))
    
    print(f"Pilot sample: {len(sample)} entities")
    
    # Load cache
    cache = load_cache()
    print(f"Cache: {len(cache)} existing results")
    
    # Fields for Place Details (FieldMask)
    DETAIL_FIELDS = "name,formatted_address,geometry,place_id,rating,user_ratings_total,formatted_phone_number,international_phone_number,website,opening_hours,business_status,address_components"
    
    api_calls = 0
    processed = 0
    found = 0
    not_found = 0
    errors = 0
    
    for item in sample:
        eid = item["entity_id"]
        if eid in cache:
            continue  # resume
        
        name = item.get("name", "")
        mun = item.get("municipio", "")
        uf = item.get("uf", "")
        coords = item.get("coords")
        
        if not name or name == "—":
            # No name to search with — skip
            result = {
                "entity_id": eid,
                "query": "",
                "status": "no_name",
                "search_status": "SKIPPED",
                "place_id": None,
                "google_name": None,
                "google_address": None,
                "google_lat": None,
                "google_lng": None,
                "distance_m": None,
                "rating": None,
                "user_ratings_total": None,
                "phone": None,
                "website": None,
                "business_status": None,
                "enriched_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(CACHE_FILE, "a") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
            cache[eid] = result
            not_found += 1
            continue
        
        query = build_query(name, mun, uf)
        
        # Text Search
        ts = google_text_search(query)
        api_calls += 1
        
        if ts.get("status") != "OK":
            result = {
                "entity_id": eid,
                "query": query,
                "status": "search_failed",
                "search_status": ts.get("status", "UNKNOWN"),
                "error": ts.get("error_message", ""),
                "place_id": None,
                "enriched_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(CACHE_FILE, "a") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
            cache[eid] = result
            errors += 1
            processed += 1
            print(f"  [{processed}/{len(sample)}] {eid}: SEARCH FAILED ({ts.get('status')})")
            continue
        
        results = ts.get("results", [])
        if not results:
            result = {
                "entity_id": eid,
                "query": query,
                "status": "zero_results",
                "search_status": "ZERO_RESULTS",
                "place_id": None,
                "enriched_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(CACHE_FILE, "a") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
            cache[eid] = result
            not_found += 1
            processed += 1
            print(f"  [{processed}/{len(sample)}] {eid}: ZERO RESULTS")
            continue
        
        # Take first result
        top = results[0]
        place_id = top.get("place_id")
        google_name = top.get("name", "")
        google_address = top.get("formatted_address", "")
        gloc = top.get("geometry", {}).get("location", {})
        g_lat = gloc.get("lat")
        g_lng = gloc.get("lng")
        
        # Calculate distance to original coords
        dist = None
        if coords and g_lat and g_lng:
            dist = haversine(coords[0], coords[1], g_lat, g_lng)
        
        # Place Details
        pd = google_place_details(place_id, DETAIL_FIELDS)
        api_calls += 1
        
        result = {
            "entity_id": eid,
            "query": query,
            "status": "found",
            "search_status": "OK",
            "place_id": place_id,
            "google_name": google_name,
            "google_address": google_address,
            "google_lat": g_lat,
            "google_lng": g_lng,
            "distance_m": round(dist, 1) if dist else None,
            "rating": pd.get("result", {}).get("rating"),
            "user_ratings_total": pd.get("result", {}).get("user_ratings_total"),
            "phone": pd.get("result", {}).get("formatted_phone_number"),
            "international_phone": pd.get("result", {}).get("international_phone_number"),
            "website": pd.get("result", {}).get("website"),
            "business_status": pd.get("result", {}).get("business_status"),
            "details_status": pd.get("status"),
            "stratum": item.get("stratum"),
            "original_name": name,
            "original_uf": uf,
            "original_municipio": mun,
            "original_coords": coords,
            "enriched_at": datetime.now(timezone.utc).isoformat(),
        }
        
        with open(CACHE_FILE, "a") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
        cache[eid] = result
        found += 1
        processed += 1
        
        dist_str = f"{dist:.0f}m" if dist else "?"
        print(f"  [{processed}/{len(sample)}] {eid}: FOUND — {google_name[:40]} ({dist_str})")
        
        # Rate limiting: ~10 req/s is safe, but we do 2 calls per entity
        time.sleep(0.3)
    
    print(f"\n=== PILOT COMPLETE ===")
    print(f"Processed: {processed}/{len(sample)}")
    print(f"  Found: {found}")
    print(f"  Not found: {not_found}")
    print(f"  Errors: {errors}")
    print(f"  API calls: {api_calls}")
    print(f"  Cache total: {len(cache)}")
    print(f"  Results file: {CACHE_FILE}")

if __name__ == "__main__":
    main()