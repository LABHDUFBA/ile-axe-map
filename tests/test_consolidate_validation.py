import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.consolidate_validation import select_coordinates


def test_google_melhor_usa_google():
    coords = select_coordinates(
        "google_melhor",
        original_lat=-8.0,
        original_lng=-34.0,
        google_lat=-8.1,
        google_lng=-34.1,
    )
    assert coords == (-8.1, -34.1, "google")


def test_nominatim_melhor_preserva_original():
    coords = select_coordinates(
        "nominatim_melhor",
        original_lat=-8.0,
        original_lng=-34.0,
        google_lat=-8.1,
        google_lng=-34.1,
    )
    assert coords == (-8.0, -34.0, "original")


def test_novo_google_sem_original_usa_google():
    coords = select_coordinates(
        "novo_google",
        original_lat=None,
        original_lng=None,
        google_lat=-8.1,
        google_lng=-34.1,
    )
    assert coords == (-8.1, -34.1, "google")


def test_novo_google_possivel_sem_original_marca_incerteza():
    coords = select_coordinates(
        "novo_google_possivel",
        original_lat=None,
        original_lng=None,
        google_lat=-8.1,
        google_lng=-34.1,
    )
    assert coords == (-8.1, -34.1, "google_possivel")


def test_match_ruim_sem_original_nao_e_mapeado():
    coords = select_coordinates(
        "match_ruim",
        original_lat=None,
        original_lng=None,
        google_lat=-8.1,
        google_lng=-34.1,
    )
    assert coords is None
