#!/usr/bin/env python3
"""Testes unitários para google_places_validation.py"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from google_places_validation import (
    normalize_name,
    name_similarity,
    haversine_m,
    check_city_match,
    evaluate_google_result,
    classify_record,
    build_query,
)


class TestNormalizeName:
    def test_removes_accents(self):
        assert normalize_name("Ilê Axé") == "ile axe"

    def test_synonyms_abassa(self):
        assert "abassa" in normalize_name("Abassá de Oyá")

    def test_synonyms_ile_axe(self):
        result = normalize_name("Ilê Axé Oyá Adênejji")
        assert "ile axe" in result
        assert "oy" in result or "oya" in result

    def test_removes_articles(self):
        result = normalize_name("Casa de Oxum")
        assert "de" not in result.split()

    def test_empty(self):
        assert normalize_name("") == ""
        assert normalize_name(None) == ""

    def test_case_insensitive(self):
        assert normalize_name("ILÊ AXÉ") == normalize_name("ilê axé")


class TestNameSimilarity:
    def test_identical_names(self):
        assert name_similarity("Ilê Axé Oyá", "Ilê Axé Oyá") > 0.9

    def test_completely_different(self):
        assert name_similarity("Casa de Oxum", "Restaurante São João") < 0.4

    def test_synonym_equivalence(self):
        # Abassá e Abaça são a mesma coisa normalizada
        sim = name_similarity("Abassá de Oyá", "Abaça Oyá Togum")
        assert sim > 0.4  # devem ter similaridade razoável

    def test_similar_names(self):
        sim = name_similarity(
            "Abassá Afro-Brasileiro Ogun-Já",
            "Abassá Afro Brasileiro Ogun Ja"
        )
        assert sim > 0.8

    def test_completely_unrelated_returns_low(self):
        sim = name_similarity("Terreiro de Oxum", "Padaria Central")
        assert sim < 0.25


class TestHaversine:
    def test_same_point(self):
        assert haversine_m(-8.0, -35.0, -8.0, -35.0) == 0

    def test_short_distance(self):
        # ~100m em Recife
        d = haversine_m(-8.04, -34.90, -8.04, -34.901)
        assert 80 < d < 120

    def test_known_distance(self):
        # Salvador to Feira de Santana ~100km
        d = haversine_m(-12.97, -38.50, -12.27, -38.95)
        assert 90000 < d < 110000


class TestCheckCityMatch:
    def test_exact_city(self):
        cm, sm = check_city_match("R. das Flores, 123 - Centro, Salvador - BA", "Salvador", "BA")
        assert cm is True
        assert sm is True

    def test_city_with_accent(self):
        cm, sm = check_city_match("R. X, 1 - São Tomé, Belém - PA", "Belém", "PA")
        assert cm is True
        assert sm is True

    def test_wrong_city(self):
        cm, sm = check_city_match("R. X, 1 - Centro, Salvador - BA", "Recife", "PE")
        assert cm is False

    def test_state_only(self):
        cm, sm = check_city_match("R. X, 1 - Centro, Bahia", "Cachoeira", "BA")
        # "Cachoeira" não está no endereço mas "BA"/"Bahia" sim
        assert sm is True

    def test_empty_address(self):
        cm, sm = check_city_match("", "Salvador", "BA")
        assert cm is False
        assert sm is False


class TestEvaluateGoogleResult:
    def test_good_match(self):
        record = {
            "name": "Ilê Axé Oyá Adênejji",
            "city": "Salvador",
            "state": "BA",
            "nominatim_lat": -12.82,
            "nominatim_lng": -38.47,
        }
        google = {
            "name": "Ilê Axé Oyá Adênejji",
            "formatted_address": "R. Lílian Marilis, 54 - São Tomé, Salvador - BA, Brasil",
            "geometry": {"location": {"lat": -12.821, "lng": -38.474}},
            "place_id": "test123",
        }
        ev = evaluate_google_result(google, record)
        assert ev["name_similarity"] > 0.8
        assert ev["city_match"] is True
        assert ev["score"] > 0.7

    def test_wrong_city_penalty(self):
        record = {
            "name": "Abassá Axé Ogum",
            "city": "Recife",
            "state": "PE",
            "nominatim_lat": -8.12,
            "nominatim_lng": -34.95,
        }
        google = {
            "name": "Axé Abassá de Ogum",
            "formatted_address": "Travessa X, 17 - Itapuã, Salvador - BA, Brasil",
            "geometry": {"location": {"lat": -12.93, "lng": -38.35}},
            "place_id": "test456",
        }
        ev = evaluate_google_result(google, record)
        assert ev["city_match"] is False
        assert ev["distance_to_nominatim_m"] > 500000  # >500km
        assert ev["score"] < 0.4  # penalizado


class TestClassifyRecord:
    def test_confirmado(self):
        record = {"nominatim_lat": -8.0, "nominatim_lng": -35.0, "name": "Casa de Oxum"}
        best = {
            "name_similarity": 0.85,
            "city_match": True,
            "state_match": True,
            "distance_to_nominatim_m": 50,
        }
        assert classify_record(record, best, [best]) == "confirmado"

    def test_google_melhor_nome_compativel_cidade_certa(self):
        record = {"nominatim_lat": -8.0, "nominatim_lng": -35.0, "name": "Abassá de Oyá"}
        best = {
            "name_similarity": 0.7,
            "city_match": True,
            "state_match": True,
            "distance_to_nominatim_m": 5000,  # 5km de diferença
        }
        # Nome compatível + cidade certa → google_melhor (endereço atualizado)
        assert classify_record(record, best, [best]) == "google_melhor"

    def test_nominatim_melhor_nome_diferente_cidade_errada(self):
        record = {"nominatim_lat": -8.0, "nominatim_lng": -35.0, "name": "Casa de Oxum"}
        best = {
            "name_similarity": 0.15,
            "city_match": False,
            "state_match": False,
            "distance_to_nominatim_m": 600000,  # 600km
        }
        assert classify_record(record, best, [best]) == "nominatim_melhor"

    def test_novo_google(self):
        record = {"nominatim_lat": None, "nominatim_lng": None, "name": "Abassá de Ogum"}
        best = {
            "name_similarity": 0.7,
            "city_match": True,
            "state_match": True,
            "distance_to_nominatim_m": None,
        }
        assert classify_record(record, best, [best]) == "novo_google"

    def test_nao_encontrado(self):
        record = {"nominatim_lat": None, "nominatim_lng": None, "name": "X"}
        assert classify_record(record, None, []) == "nao_encontrado"

    def test_match_ruim_sem_nominatim(self):
        record = {"nominatim_lat": None, "nominatim_lng": None, "name": "Casa de Oxum"}
        best = {
            "name_similarity": 0.1,
            "city_match": False,
            "state_match": False,
            "distance_to_nominatim_m": None,
        }
        assert classify_record(record, best, [best]) == "match_ruim"


class TestBuildQuery:
    def test_with_name_and_city(self):
        q = build_query({"name": "Ilê Axé", "city": "Salvador", "state": "BA"})
        assert "Ilê Axé" in q
        assert "Salvador" in q
        assert "Bahia" in q

    def test_state_full_name(self):
        q = build_query({"name": "Teste", "city": "Recife", "state": "PE"})
        assert "Pernambuco" in q

    def test_no_name(self):
        q = build_query({"name": "", "city": "Salvador", "state": "BA"})
        assert "terreiro candomblé" in q

    def test_no_data(self):
        q = build_query({"name": "", "city": "", "state": ""})
        assert q is None