import copy
import csv
import json
from pathlib import Path

import jsonschema
import pytest

from scripts.v3.adapters.cnpj import adapt_record as adapt_cnpj
from scripts.v3.adapters.cnpj import adapt_records as adapt_cnpj_records
from scripts.v3.adapters.mapeando_axe import adapt_record as adapt_mapeando_axe
from scripts.v3.adapters.mapeando_axe import adapt_records as adapt_mapeando_axe_records
from scripts.v3.adapters.terreiros_brasil import adapt_record as adapt_terreiros_brasil
from scripts.v3.adapters.terreiros_brasil import (
    adapt_records as adapt_terreiros_brasil_records,
)


ROOT = Path(__file__).resolve().parents[2]


def _synthetic_cnpj(base="999999990001"):
    def digit(prefix, weights):
        remainder = (
            sum(int(value) * weight for value, weight in zip(prefix, weights)) % 11
        )
        return "0" if remainder < 2 else str(11 - remainder)

    first = digit(base, (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
    return base + first + digit(
        base + first, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    )


@pytest.fixture(scope="module")
def validator():
    schema = json.loads(
        (ROOT / "schemas/source-record-v3.schema.json").read_text(encoding="utf-8")
    )
    return jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )


def test_mapeando_axe_preserva_bruto_e_nao_promove_geocodificacao(validator):
    payload = {
        "source_record_id": "map:sintetico/001",
        "name": "Ilê Sintético",
        "address_raw": "Rua de Teste, 1",
        "city": "Cidade Teste",
        "state": "TS",
        "postcode": "00000-000",
        "nominatim_lat": -12.3,
        "nominatim_lng": -45.6,
        "nominatim_osm_id": 987,
        "nominatim_osm_type": "node",
        "nominatim_display_name": "Resultado auxiliar",
        "nominatim_query": "Consulta auxiliar",
        "nominatim_status": "success",
        "nominatim_precision": "building",
        "nominatim_confidence": 0.8,
        "nominatim_addresstype": "place_of_worship",
    }

    output = adapt_mapeando_axe(payload)

    assert output["id_fonte"] == "map:sintetico/001"
    assert output["nome_original"] == "Ilê Sintético"
    assert output["localizacao_original"] == {
        "latitude": None,
        "longitude": None,
        "endereco": "Rua de Teste, 1",
        "municipio": "Cidade Teste",
        "uf": "TS",
        "cep": "00000-000",
        "precisao": None,
        "fonte_coordenada": None,
        "coordenadas_alternativas": [],
    }
    assert output["identificadores"]["osm_id"] is None
    assert output["dados_originais"] == payload
    validator.validate(output)


def test_mapeando_axe_aceita_nome_ausente_nulo_ou_vazio():
    base = {"source_record_id": "sintetico"}

    assert adapt_mapeando_axe(base)["nome_original"] is None
    assert adapt_mapeando_axe({**base, "name": None})["nome_original"] is None
    assert adapt_mapeando_axe({**base, "name": ""})["nome_original"] is None
    assert adapt_mapeando_axe({**base, "name": "   "})["nome_original"] is None


def test_mapeando_axe_faz_copia_profunda():
    payload = {
        "source_record_id": "sintetico",
        "name": "Nome",
        "extra": {"lista": [1]},
    }
    esperado = copy.deepcopy(payload)

    output = adapt_mapeando_axe(payload)
    payload["extra"]["lista"].append(2)

    assert output["dados_originais"] == esperado


def test_mapeando_axe_lote_preserva_ordem_e_cardinalidade():
    payloads = [
        {"source_record_id": "primeiro", "name": "A"},
        {"source_record_id": "segundo", "name": "B"},
    ]

    outputs = adapt_mapeando_axe_records(iter(payloads))

    assert [item["id_fonte"] for item in outputs] == ["primeiro", "segundo"]
    assert len(outputs) == len(payloads)


@pytest.mark.parametrize("invalid_id", [None, "", "   ", True, 1.2, [], {}])
def test_mapeando_axe_erro_indica_fonte_e_indice_sem_payload(invalid_id):
    segredo = "NAO_VAZAR_PAYLOAD"

    with pytest.raises((TypeError, ValueError)) as caught:
        adapt_mapeando_axe_records([
            {"source_record_id": "ok"},
            {"source_record_id": invalid_id, "segredo": segredo},
        ])

    message = str(caught.value)
    assert "mapeando_axe" in message
    assert "índice 1" in message
    assert segredo not in message


def test_cnpj_usa_nome_fantasia_e_nao_promove_geocodificacao(validator):
    cnpj = _synthetic_cnpj()
    payload = {
        "cnpj": cnpj,
        "nome_fantasia": "Nome Fantasia Sintético",
        "razao_social": "Razão Social Sintética",
        "logradouro": "Rua Cadastral",
        "numero": "10",
        "bairro": "Bairro Cadastral",
        "codigo_municipio": "COD-SINTETICO",
        "uf": "TS",
        "cep": "00000-000",
        "data_inicio": "2001-02-03",
        "lat": -10.1,
        "lng": -40.2,
        "precision": "building",
        "query_used": "Consulta auxiliar",
        "source": "fixture",
    }

    output = adapt_cnpj(payload)

    assert output["id_fonte"] == cnpj
    assert output["identificadores"]["cnpj"] == cnpj
    assert output["nome_original"] == "Nome Fantasia Sintético"
    assert output["localizacao_original"] == {
        "latitude": None,
        "longitude": None,
        "endereco": None,
        "municipio": None,
        "uf": "TS",
        "cep": "00000-000",
        "precisao": None,
        "fonte_coordenada": None,
        "coordenadas_alternativas": [],
    }
    assert output["dados_originais"] == payload
    validator.validate(output)


@pytest.mark.parametrize(
    ("fantasia", "razao", "expected"),
    [
        (None, "Razão", "Razão"),
        ("", "Razão", "Razão"),
        ("   ", "Razão", "Razão"),
        (None, None, None),
        (None, "", None),
    ],
)
def test_cnpj_fallback_de_nome_sem_alterar_originais(fantasia, razao, expected):
    payload = {
        "cnpj": _synthetic_cnpj(),
        "nome_fantasia": fantasia,
        "razao_social": razao,
    }

    output = adapt_cnpj(payload)

    assert output["nome_original"] == expected
    assert output["dados_originais"] == payload


def test_cnpj_faz_copia_profunda():
    payload = {"cnpj": _synthetic_cnpj(), "extra": {"lista": [1]}}
    output = adapt_cnpj(payload)

    payload["extra"]["lista"].append(2)

    assert output["dados_originais"]["extra"] == {"lista": [1]}


@pytest.mark.parametrize(
    "invalid_cnpj", [None, "", "123", "11.111.111/1111-11", 123, True]
)
def test_cnpj_rejeita_id_invalido_com_fonte_indice_e_sem_payload(invalid_cnpj):
    segredo = "NAO_VAZAR_CNPJ"

    with pytest.raises((TypeError, ValueError)) as caught:
        adapt_cnpj_records([
            {"cnpj": _synthetic_cnpj()},
            {"cnpj": invalid_cnpj, "segredo": segredo},
        ])

    message = str(caught.value)
    assert "cnpj" in message
    assert "índice 1" in message
    assert segredo not in message


def test_cnpj_lote_preserva_ordem_e_cardinalidade():
    first = _synthetic_cnpj("888888880001")
    second = _synthetic_cnpj("777777770001")

    outputs = adapt_cnpj_records(iter([{"cnpj": first}, {"cnpj": second}]))

    assert [item["id_fonte"] for item in outputs] == [first, second]


def test_terreiros_brasil_mapeia_coordenadas_originais_sem_classificar_nacao(validator):
    payload = {
        "id": 101,
        "nome": "Terreiro Sintético",
        "lat": -11.2,
        "lng": -41.3,
        "endereco": "Rua Sintética, 2",
        "cidade": "Cidade Teste",
        "uf": "TS",
        "precision": "point",
        "nacao": "Texto pendente",
        "categoria_raw": "Categoria pendente",
        "descricao": "Descrição sintética",
        "link": "https://example.invalid/registro/101",
        "source": "fixture",
        "recovery_method": "fixture",
    }

    output = adapt_terreiros_brasil(payload)

    assert output["id_fonte"] == "101"
    assert output["nome_original"] == "Terreiro Sintético"
    assert output["localizacao_original"] == {
        "latitude": -11.2,
        "longitude": -41.3,
        "endereco": "Rua Sintética, 2",
        "municipio": "Cidade Teste",
        "uf": "TS",
        "cep": None,
        "precisao": "point",
        "fonte_coordenada": None,
        "coordenadas_alternativas": [],
    }
    assert output["identidade_religiosa_original"] == {
        "tradicao": None,
        "nacao": None,
        "denominacao": None,
    }
    assert output["identificadores"]["url"] == payload["link"]
    assert output["dados_originais"] == payload
    validator.validate(output)


@pytest.mark.parametrize("coordinates", [{}, {"lat": None, "lng": None}])
def test_terreiros_brasil_aceita_par_de_coordenadas_nulas(coordinates):
    output = adapt_terreiros_brasil({"id": 1, **coordinates})

    assert output["localizacao_original"]["latitude"] is None
    assert output["localizacao_original"]["longitude"] is None


@pytest.mark.parametrize(
    "coordinates",
    [
        {"lat": -10.0},
        {"lng": -40.0},
        {"lat": None, "lng": -40.0},
        {"lat": -10.0, "lng": None},
    ],
)
def test_terreiros_brasil_rejeita_meia_coordenada(coordinates):
    with pytest.raises(ValueError, match="terreiros_brasil.*índice 0.*coordenadas"):
        adapt_terreiros_brasil({"id": 1, **coordinates})


@pytest.mark.parametrize("nome", [None, "", "   "])
def test_terreiros_brasil_aceita_nome_ausente_nulo_ou_vazio(nome):
    assert adapt_terreiros_brasil({"id": 1, "nome": nome})["nome_original"] is None


def test_terreiros_brasil_link_vazio_nao_e_promovido():
    output = adapt_terreiros_brasil({"id": 1, "link": ""})

    assert output["identificadores"]["url"] is None
    assert output["dados_originais"]["link"] == ""


def test_terreiros_brasil_faz_copia_profunda():
    payload = {"id": 1, "extra": {"lista": [1]}}
    output = adapt_terreiros_brasil(payload)

    payload["extra"]["lista"].append(2)

    assert output["dados_originais"]["extra"] == {"lista": [1]}


@pytest.mark.parametrize("invalid_id", [None, "", "   ", True, 1.2, [], {}])
def test_terreiros_brasil_erro_indica_fonte_e_indice_sem_payload(invalid_id):
    segredo = "NAO_VAZAR_TDB"

    with pytest.raises((TypeError, ValueError)) as caught:
        adapt_terreiros_brasil_records(
            [{"id": 1}, {"id": invalid_id, "segredo": segredo}]
        )

    message = str(caught.value)
    assert "terreiros_brasil" in message
    assert "índice 1" in message
    assert segredo not in message


def test_terreiros_brasil_lote_preserva_ordem_e_cardinalidade():
    outputs = adapt_terreiros_brasil_records(iter([{"id": 2}, {"id": 1}]))

    assert [item["id_fonte"] for item in outputs] == ["2", "1"]


def test_adapters_preservam_seus_45_caminhos_da_matriz_sem_perda(validator):
    with (ROOT / "data/audit/v3/source_variable_matrix.csv").open(
        encoding="utf-8", newline=""
    ) as matrix_file:
        matrix = list(csv.DictReader(matrix_file))
    sources = {"mapeando_axe", "cnpj", "terreiros_brasil"}
    fields = {
        source: {
            row["campo_original"]
            for row in matrix
            if row["fonte"] == source
        }
        for source in sources
    }
    assert len(matrix) == 129
    assert sum(map(len, fields.values())) == 45

    payloads: dict[str, dict[str, object]] = {
        source: {field: None for field in source_fields}
        for source, source_fields in fields.items()
    }
    payloads["mapeando_axe"]["source_record_id"] = "sintetico"
    payloads["cnpj"]["cnpj"] = _synthetic_cnpj()
    payloads["terreiros_brasil"]["id"] = 1
    adapters = {
        "mapeando_axe": adapt_mapeando_axe,
        "cnpj": adapt_cnpj,
        "terreiros_brasil": adapt_terreiros_brasil,
    }

    for source in sorted(sources):
        output = adapters[source](payloads[source])
        assert output["dados_originais"] == payloads[source]
        assert set(output["dados_originais"]) == fields[source]
        validator.validate(output)
