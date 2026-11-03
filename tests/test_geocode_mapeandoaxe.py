import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "geocode_mapeandoaxe.py"


def load_module():
    spec = importlib.util.spec_from_file_location("geocode_mapeandoaxe", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_query_uses_only_location_fields():
    module = load_module()
    record = {
        "address_raw": "Rua Um, 10, Centro",
        "city": "Belém",
        "state": "PA",
        "postcode": "66000-000",
        "leadership": "Nome privado",
        "email": "privado@example.org",
    }

    query = module.build_query(record)

    assert query == "Rua Um, 10, Centro, Belém, PA, 66000-000, Brasil"
    assert "privado" not in query


def test_build_simplified_query_removes_neighborhood_landmarks_and_postcode():
    module = load_module()
    record = {
        "address_raw": "Rua Cacique, 103, Próximo à Avenida Júlio César, Sacramenta",
        "city": "Belém",
        "state": "PA",
        "postcode": "66123-180",
    }

    query = module.build_simplified_query(record)

    assert query == "Rua Cacique, 103, Belém, PA, Brasil"
    assert "Próximo" not in query
    assert "66123" not in query


def test_candidate_precision_requires_matching_house_number_for_exact():
    module = load_module()
    record = {"address_raw": "Rua Cacique, 103, Sacramenta"}
    exact = {"address": {"house_number": "103", "road": "Rua Cacique"}}
    street = {"address": {"road": "Rua Cacique"}}

    assert module.candidate_precision(record, exact) == "house_number"
    assert module.candidate_precision(record, street) == "street"


def test_geocode_record_v2_returns_precision_and_candidate_type():
    module = load_module()
    record = {"source_record_id": "7", "address_raw": "Rua Cacique, 103, Sacramenta", "city": "Belém", "state": "PA", "postcode": "66123-180"}
    candidate = {
        "lat": "-1.4", "lon": "-48.4", "display_name": "103, Rua Cacique, Belém",
        "osm_type": "node", "osm_id": 7, "type": "house", "addresstype": "place",
        "importance": 0.2,
        "address": {"house_number": "103", "road": "Rua Cacique", "city": "Belém", "ISO3166-2-lvl4": "BR-PA", "country_code": "br"},
    }

    result = module.geocode_record_v2(record, lambda _query: [candidate])

    assert result["status"] == "matched"
    assert result["precision"] == "house_number"
    assert result["nominatim_type"] == "house"
    assert result["query"] == "Rua Cacique, 103, Belém, PA, Brasil"


def test_evaluate_candidate_accepts_matching_city_state_and_postcode():
    module = load_module()
    record = {"city": "Belém", "state": "PA", "postcode": "66000-000"}
    candidate = {
        "lat": "-1.45",
        "lon": "-48.49",
        "importance": 0.4,
        "address": {
            "city": "Belém",
            "state": "Pará",
            "ISO3166-2-lvl4": "BR-PA",
            "postcode": "66000-000",
            "country_code": "br",
        },
    }

    result = module.evaluate_candidate(record, candidate)

    assert result["accepted"] is True
    assert result["confidence"] >= 0.9


def test_evaluate_candidate_rejects_postcode_centroid_without_city_match():
    module = load_module()
    record = {"city": "Recife", "state": "PE", "postcode": "52091-200"}
    candidate = {
        "importance": 0.5,
        "address": {
            "city": "Olinda",
            "ISO3166-2-lvl4": "BR-PE",
            "postcode": "52091-200",
            "country_code": "br",
        },
    }

    result = module.evaluate_candidate(record, candidate)

    assert result["accepted"] is False


def test_geocode_record_returns_best_accepted_candidate():
    module = load_module()
    record = {
        "source_record_id": "7",
        "address_raw": "Rua Um, 10",
        "city": "Belém",
        "state": "PA",
        "postcode": "66000-000",
    }
    candidates = [{
        "lat": "-1.45",
        "lon": "-48.49",
        "display_name": "Rua Um, Belém, Pará, Brasil",
        "osm_type": "way",
        "osm_id": 123,
        "importance": 0.4,
        "address": {
            "city": "Belém",
            "ISO3166-2-lvl4": "BR-PA",
            "postcode": "66000-000",
            "country_code": "br",
        },
    }]

    result = module.geocode_record(record, lambda query: candidates)

    assert result["status"] == "matched"
    assert result["latitude"] == -1.45
    assert result["longitude"] == -48.49
    assert result["source_record_id"] == "7"


def test_run_batch_resumes_from_jsonl_cache(tmp_path):
    module = load_module()
    records = [
        {"source_record_id": "1", "address_raw": "Rua Um", "city": "Belém", "state": "PA", "postcode": "66000-000"},
        {"source_record_id": "2", "address_raw": "Rua Dois", "city": "Belém", "state": "PA", "postcode": "66000-001"},
    ]
    calls = []

    def search(query):
        calls.append(query)
        return []

    cache_path = tmp_path / "cache.jsonl"
    first = module.run_batch(records, cache_path, search, delay=0)
    second = module.run_batch(records, cache_path, search, delay=0)

    assert first["processed"] == 2
    assert second["processed"] == 0
    assert len(calls) == 2
    assert len(cache_path.read_text().splitlines()) == 2


def test_nominatim_search_requests_brazil_with_address_details():
    module = load_module()
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return b'[{"lat":"-1.45","lon":"-48.49"}]'

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["user_agent"] = request.headers["User-agent"]
        captured["timeout"] = timeout
        return Response()

    results = module.nominatim_search("Rua Um, Belém, PA, Brasil", opener=opener)

    assert results[0]["lat"] == "-1.45"
    assert "countrycodes=br" in captured["url"]
    assert "addressdetails=1" in captured["url"]
    assert "IleAxeMap" in captured["user_agent"]


def test_run_batch_keeps_failed_requests_pending(tmp_path):
    module = load_module()
    records = [
        {"source_record_id": "1", "address_raw": "Rua Um", "city": "Belém", "state": "PA", "postcode": ""},
        {"source_record_id": "2", "address_raw": "Rua Dois", "city": "Belém", "state": "PA", "postcode": ""},
    ]
    calls = 0

    def search(_query):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("temporário")
        return []

    cache_path = tmp_path / "cache.jsonl"
    result = module.run_batch(records, cache_path, search, delay=0)

    assert result["processed"] == 1
    assert result["errors"] == 1
    assert '"source_record_id": "1"' not in cache_path.read_text()
    assert '"source_record_id": "2"' in cache_path.read_text()
