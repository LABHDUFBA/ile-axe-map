import copy
import csv
import json
from pathlib import Path

import jsonschema
import pytest

from scripts.v3.adapters.ceao import adapt_record as adapt_ceao
from scripts.v3.adapters.ceao import adapt_records as adapt_ceao_records
from scripts.v3.adapters.google_bahia import adapt_record as adapt_google
from scripts.v3.adapters.google_bahia import adapt_records as adapt_google_records
from scripts.v3.adapters.osm import adapt_record as adapt_osm
from scripts.v3.adapters.osm import adapt_records as adapt_osm_records
from scripts.v3.adapters.sefaz import adapt_record as adapt_sefaz
from scripts.v3.adapters.sefaz import adapt_records as adapt_sefaz_records
from scripts.v3.adapters.common import synthetic_source_id


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def validator():
    schema = json.loads(
        (ROOT / "schemas/source-record-v3.schema.json").read_text(encoding="utf-8")
    )
    return jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )


def test_ceao_mapeia_id_coordenadas_e_campos_declarados_sem_classificar_nacao(validator):
    payload = {
        "ceao_id": "ceao-sintetico/001",
        "nome": "Ilê Sintético",
        "lat": -12.3,
        "lng": -38.4,
        "endereco": "Rua de Teste, 1",
        "cep": "00000-000",
        "nacao": "Texto pendente",
        "nacao_original": "Outro texto pendente",
        "extra": {"lista": [1]},
    }

    output = adapt_ceao(payload)

    assert output["id_fonte"] == "ceao-sintetico/001"
    assert output["id_fonte_sintetico"] is False
    assert output["nome_original"] == "Ilê Sintético"
    assert output["localizacao_original"] == {
        "latitude": -12.3,
        "longitude": -38.4,
        "endereco": "Rua de Teste, 1",
        "municipio": None,
        "uf": None,
        "cep": "00000-000",
        "precisao": None,
        "fonte_coordenada": None,
        "coordenadas_alternativas": [],
    }
    assert output["identificadores"]["ceao_id"] == "ceao-sintetico/001"
    assert output["identidade_religiosa_original"] == {
        "tradicao": None,
        "nacao": None,
        "denominacao": None,
    }
    assert output["dados_originais"] == payload
    validator.validate(output)


def test_ceao_faz_copia_profunda():
    payload = {"ceao_id": "sintetico", "extra": {"lista": [1]}}
    output = adapt_ceao(payload)

    payload["extra"]["lista"].append(2)

    assert output["dados_originais"]["extra"] == {"lista": [1]}


@pytest.mark.parametrize("coordinates", [{"lat": -12.0}, {"lng": -38.0}])
def test_ceao_rejeita_meia_coordenada(coordinates):
    with pytest.raises(ValueError, match="ceao.*índice 0.*coordenadas"):
        adapt_ceao({"ceao_id": "sintetico", **coordinates})


@pytest.mark.parametrize("invalid_id", [None, "", "   ", True, 1.2, [], {}])
def test_ceao_erro_indica_fonte_e_indice_sem_payload(invalid_id):
    segredo = "NAO_VAZAR_CEAO"
    with pytest.raises((TypeError, ValueError)) as caught:
        adapt_ceao_records([
            {"ceao_id": "ok"},
            {"ceao_id": invalid_id, "segredo": segredo},
        ])

    message = str(caught.value)
    assert "ceao" in message
    assert "índice 1" in message
    assert segredo not in message


def test_ceao_lote_preserva_ordem_e_cardinalidade():
    outputs = adapt_ceao_records(iter([
        {"ceao_id": "segundo"},
        {"ceao_id": "primeiro"},
    ]))

    assert [item["id_fonte"] for item in outputs] == ["segundo", "primeiro"]


def test_google_gera_id_sintetico_e_nao_inventa_place_id(validator):
    payload = {
        "nome": "Ilê Google Sintético",
        "lat": -12.4,
        "lng": -38.5,
        "endereco": "Rua Google, 2",
        "bairro": "Bairro Teste",
        "rating": 4.5,
        "reviews": 3,
        "fontes": [{"fonte": "google", "id": None}],
        "nacao_categoria": "Classificação derivada",
    }

    output = adapt_google(payload)

    assert output["fonte"] == "bahia_google"
    assert output["id_fonte"] == synthetic_source_id(
        "bahia_google", payload["nome"], payload["lat"], payload["lng"]
    )
    assert output["id_fonte_sintetico"] is True
    assert output["nome_original"] == payload["nome"]
    assert output["localizacao_original"]["latitude"] == payload["lat"]
    assert output["localizacao_original"]["longitude"] == payload["lng"]
    assert output["localizacao_original"]["endereco"] == payload["endereco"]
    assert output["identificadores"]["google_place_id"] is None
    assert output["identidade_religiosa_original"]["nacao"] is None
    assert output["dados_originais"] == payload
    validator.validate(output)


def test_google_id_sintetico_e_deterministico_e_sensivel_as_partes():
    first = {"nome": "A", "lat": -12.0, "lng": -38.0}
    second = {"nome": "A", "lat": -12.0, "lng": -38.1}

    assert adapt_google(first)["id_fonte"] == adapt_google(copy.deepcopy(first))["id_fonte"]
    assert adapt_google(first)["id_fonte"] != adapt_google(second)["id_fonte"]


def test_google_rejeita_meia_coordenada_com_fonte_e_indice_sem_payload():
    segredo = "NAO_VAZAR_GOOGLE"
    with pytest.raises(ValueError) as caught:
        adapt_google_records([
            {"nome": "ok", "lat": -12.0, "lng": -38.0},
            {"nome": "erro", "lat": -12.0, "segredo": segredo},
        ])

    message = str(caught.value)
    assert "bahia_google" in message
    assert "índice 1" in message
    assert segredo not in message


def test_google_lote_preserva_ordem_cardinalidade_e_deep_copy():
    payloads = [
        {"nome": "A", "lat": -12.0, "lng": -38.0, "extra": {"lista": [1]}},
        {"nome": "B", "lat": -13.0, "lng": -39.0},
    ]
    outputs = adapt_google_records(iter(payloads))
    expected_ids = [
        synthetic_source_id("bahia_google", row["nome"], row["lat"], row["lng"])
        for row in payloads
    ]
    payloads[0]["extra"]["lista"].append(2)

    assert [item["id_fonte"] for item in outputs] == expected_ids
    assert len(outputs) == 2
    assert outputs[0]["dados_originais"]["extra"] == {"lista": [1]}


def test_osm_gera_id_sintetico_e_nao_inventa_osm_id(validator):
    payload = {
        "nome": "Ilê OSM Sintético",
        "lat": -13.2,
        "lng": -39.3,
        "endereco": "",
        "fontes": [{"fonte": "osm", "id": None}],
        "nacao_categoria": "Classificação derivada",
    }

    output = adapt_osm(payload)

    assert output["id_fonte"] == synthetic_source_id(
        "osm", payload["nome"], payload["lat"], payload["lng"]
    )
    assert output["id_fonte_sintetico"] is True
    assert output["nome_original"] == payload["nome"]
    assert output["localizacao_original"]["latitude"] == payload["lat"]
    assert output["localizacao_original"]["longitude"] == payload["lng"]
    assert output["localizacao_original"]["endereco"] == ""
    assert output["identificadores"]["osm_id"] is None
    assert output["identidade_religiosa_original"]["nacao"] is None
    assert output["dados_originais"] == payload
    validator.validate(output)


def test_osm_rejeita_meia_coordenada_com_fonte_e_indice_sem_payload():
    segredo = "NAO_VAZAR_OSM"
    with pytest.raises(ValueError) as caught:
        adapt_osm_records([
            {"nome": "ok", "lat": -12.0, "lng": -38.0},
            {"nome": "erro", "lng": -38.0, "segredo": segredo},
        ])

    message = str(caught.value)
    assert "osm" in message
    assert "índice 1" in message
    assert segredo not in message


def test_osm_lote_preserva_ordem_cardinalidade_determinismo_e_deep_copy():
    payloads = [
        {"nome": "A", "lat": -12.0, "lng": -38.0, "extra": {"lista": [1]}},
        {"nome": "B", "lat": -13.0, "lng": -39.0},
    ]
    outputs = adapt_osm_records(iter(payloads))
    expected_ids = [
        synthetic_source_id("osm", row["nome"], row["lat"], row["lng"])
        for row in payloads
    ]
    payloads[0]["extra"]["lista"].append(2)

    assert [item["id_fonte"] for item in outputs] == expected_ids
    assert adapt_osm({"nome": "A", "lat": -12.0, "lng": -38.0})["id_fonte"] == expected_ids[0]
    assert len(outputs) == 2
    assert outputs[0]["dados_originais"]["extra"] == {"lista": [1]}


def test_sefaz_usa_fallback_sintetico_do_codigo_sem_inventar_identificador(validator):
    payload = {
        "sefaz_codigo": 900001,
        "nome": "Ilê SEFAZ Sintético",
        "lat": None,
        "lng": None,
        "fontes": [{"fonte": "sefaz", "id": 900001}],
        "nacao_categoria": "Classificação derivada",
        "extra": {"lista": [1]},
    }

    output = adapt_sefaz(payload)

    assert output["id_fonte"] == synthetic_source_id("sefaz", payload["sefaz_codigo"])
    assert output["id_fonte_sintetico"] is True
    assert output["nome_original"] == payload["nome"]
    assert output["localizacao_original"]["latitude"] is None
    assert output["localizacao_original"]["longitude"] is None
    assert all(value is None for value in output["identificadores"].values())
    assert output["identidade_religiosa_original"]["nacao"] is None
    assert output["dados_originais"] == payload
    validator.validate(output)


@pytest.mark.parametrize("invalid_code", [None, "", "   ", True, 1.2, [], {}])
def test_sefaz_rejeita_codigo_invalido_com_fonte_indice_e_sem_payload(invalid_code):
    segredo = "NAO_VAZAR_SEFAZ"
    with pytest.raises((TypeError, ValueError)) as caught:
        adapt_sefaz_records([
            {"sefaz_codigo": 900001},
            {"sefaz_codigo": invalid_code, "segredo": segredo},
        ])

    message = str(caught.value)
    assert "sefaz" in message
    assert "índice 1" in message
    assert segredo not in message


def test_sefaz_lote_preserva_ordem_cardinalidade_determinismo_e_deep_copy():
    payloads = [
        {"sefaz_codigo": 900002, "extra": {"lista": [1]}},
        {"sefaz_codigo": 900001},
    ]
    outputs = adapt_sefaz_records(iter(payloads))
    expected_ids = [synthetic_source_id("sefaz", row["sefaz_codigo"]) for row in payloads]
    payloads[0]["extra"]["lista"].append(2)

    assert [item["id_fonte"] for item in outputs] == expected_ids
    assert adapt_sefaz({"sefaz_codigo": 900002})["id_fonte"] == expected_ids[0]
    assert len(outputs) == 2
    assert outputs[0]["dados_originais"]["extra"] == {"lista": [1]}


def test_adapters_bahia_preservam_seus_84_caminhos_da_matriz_sem_perda(validator):
    with (ROOT / "data/audit/v3/source_variable_matrix.csv").open(
        encoding="utf-8", newline=""
    ) as matrix_file:
        matrix = list(csv.DictReader(matrix_file))
    sources = {"ceao", "bahia_google", "osm", "sefaz"}
    fields = {
        source: {
            row["campo_original"]
            for row in matrix
            if row["fonte"] == source
        }
        for source in sources
    }
    assert len(matrix) == 129
    assert sum(map(len, fields.values())) == 84

    payloads: dict[str, dict[str, object]] = {
        source: {field: None for field in source_fields}
        for source, source_fields in fields.items()
    }
    payloads["ceao"]["ceao_id"] = "sintetico"
    payloads["bahia_google"].update({"nome": "Google", "lat": -12.0, "lng": -38.0})
    payloads["osm"].update({"nome": "OSM", "lat": -13.0, "lng": -39.0})
    payloads["sefaz"]["sefaz_codigo"] = 900001
    adapters = {
        "ceao": adapt_ceao,
        "bahia_google": adapt_google,
        "osm": adapt_osm,
        "sefaz": adapt_sefaz,
    }

    for source in sorted(sources):
        output = adapters[source](payloads[source])
        assert output["dados_originais"] == payloads[source]
        assert set(output["dados_originais"]) == fields[source]
        validator.validate(output)
