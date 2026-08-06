import copy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/source-record-v3.schema.json"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def validator(schema):
    return jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )


@pytest.fixture
def registro_completo():
    return {
        "source_record_key": "ceao:00123",
        "fonte": "ceao",
        "id_fonte": "00123",
        "id_fonte_sintetico": False,
        "nome_original": "Ilê Axé Sintético",
        "localizacao_original": {
            "latitude": -12.9714,
            "longitude": -38.5014,
            "endereco": "Rua de Teste, 10",
            "municipio": "Salvador",
            "uf": "BA",
            "cep": "40000-000",
            "precisao": "endereco",
            "fonte_coordenada": "fonte sintética",
            "coordenadas_alternativas": [
                {
                    "latitude": -12.97,
                    "longitude": -38.5,
                    "fonte": "geocodificador sintético",
                    "precisao": None,
                }
            ],
        },
        "identidade_religiosa_original": {
            "tradicao": "Candomblé",
            "nacao": "Ketu",
            "denominacao": None,
        },
        "identificadores": {
            "cnpj": "04.858.642/0001-87",
            "ceao_id": "00123",
            "osm_id": None,
            "google_place_id": None,
            "url": "https://example.invalid/registro/00123",
        },
        "data_coleta": "2026-08-07",
        "flags_auditoria": {
            "baseline_atual": False,
            "exclusao_curada": False,
            "remocao_heuristica_legada": False,
            "ambiguo_pendente": False,
            "dedup_legado_recuperado": False,
        },
        "dados_originais": {
            "CAMPO LIVRE": "valor",
            "objeto": {"lista": [1, True, None]},
        },
    }


def test_schema_aceita_registro_completo(validator, registro_completo):
    validator.validate(registro_completo)


def test_schema_aceita_registro_sem_coordenada(validator, registro_completo):
    registro = copy.deepcopy(registro_completo)
    registro["localizacao_original"]["latitude"] = None
    registro["localizacao_original"]["longitude"] = None

    validator.validate(registro)


@pytest.mark.parametrize("campo", ["latitude", "longitude"])
def test_schema_rejeita_meia_coordenada(validator, registro_completo, campo):
    registro = copy.deepcopy(registro_completo)
    registro["localizacao_original"][campo] = None

    with pytest.raises(jsonschema.ValidationError):
        validator.validate(registro)


def test_schema_rejeita_fonte_invalida(validator, registro_completo):
    registro = copy.deepcopy(registro_completo)
    registro["fonte"] = "fonte_desconhecida"

    with pytest.raises(jsonschema.ValidationError):
        validator.validate(registro)


def test_schema_rejeita_chave_ausente(validator, registro_completo):
    registro = copy.deepcopy(registro_completo)
    del registro["source_record_key"]

    with pytest.raises(jsonschema.ValidationError):
        validator.validate(registro)


def test_schema_rejeita_chave_vazia_ou_em_branco(validator, registro_completo):
    registro = copy.deepcopy(registro_completo)
    registro["source_record_key"] = "ceao:   "

    with pytest.raises(jsonschema.ValidationError):
        validator.validate(registro)


def test_schema_rejeita_id_vazio(validator, registro_completo):
    registro = copy.deepcopy(registro_completo)
    registro["id_fonte"] = ""

    with pytest.raises(jsonschema.ValidationError):
        validator.validate(registro)


def test_schema_rejeita_url_invalida(validator, registro_completo):
    registro = copy.deepcopy(registro_completo)
    registro["identificadores"]["url"] = "não é uma URI"

    with pytest.raises(jsonschema.ValidationError):
        validator.validate(registro)


def test_schema_rejeita_data_invalida(validator, registro_completo):
    registro = copy.deepcopy(registro_completo)
    registro["data_coleta"] = "2026-02-31"

    with pytest.raises(jsonschema.ValidationError):
        validator.validate(registro)


def test_schema_rejeita_flag_ausente(validator, registro_completo):
    registro = copy.deepcopy(registro_completo)
    del registro["flags_auditoria"]["ambiguo_pendente"]

    with pytest.raises(jsonschema.ValidationError):
        validator.validate(registro)


@pytest.mark.parametrize(
    ("objeto", "propriedade"),
    [
        (None, "extra_topo"),
        ("localizacao_original", "bairro"),
        ("identidade_religiosa_original", "extra_identidade"),
        ("identificadores", "extra_identificador"),
        ("flags_auditoria", "extra_flag"),
    ],
)
def test_schema_rejeita_propriedade_estrutural_extra(
    validator, registro_completo, objeto, propriedade
):
    registro = copy.deepcopy(registro_completo)
    destino = registro if objeto is None else registro[objeto]
    destino[propriedade] = "valor"

    with pytest.raises(jsonschema.ValidationError):
        validator.validate(registro)


def test_schema_rejeita_propriedade_extra_em_coordenada_alternativa(
    validator, registro_completo
):
    registro = copy.deepcopy(registro_completo)
    registro["localizacao_original"]["coordenadas_alternativas"][0]["extra"] = True

    with pytest.raises(jsonschema.ValidationError):
        validator.validate(registro)


def test_schema_rejeita_coordenada_alternativa_fora_do_limite(
    validator, registro_completo
):
    registro = copy.deepcopy(registro_completo)
    registro["localizacao_original"]["coordenadas_alternativas"][0][
        "latitude"
    ] = 90.1

    with pytest.raises(jsonschema.ValidationError):
        validator.validate(registro)


def test_schema_aceita_dados_originais_arbitrarios(validator, registro_completo):
    registro = copy.deepcopy(registro_completo)
    registro["dados_originais"] = {
        "qualquer_nome": {"aninhado": [{"x": 1}, "texto", None]},
        "outro": False,
    }

    validator.validate(registro)
