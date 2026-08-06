import copy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/terreiro-v3.schema.json"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def entidade_minima():
    return {
        "entity_id": "trr_ceao_123",
        "nome": {
            "preferido": "Ilê Axé Exemplo",
            "aliases": [],
            "normalizado_match": "ile axe exemplo",
        },
        "localizacao": {
            "latitude": None,
            "longitude": None,
            "fonte_coordenada": None,
            "precisao": None,
            "uf": "BA",
            "municipio": "Salvador",
            "codigo_ibge_municipio": "2927408",
            "bairro": None,
            "cep": None,
            "endereco_original": None,
            "status_territorial": "sem_coordenada",
        },
        "identidade_religiosa": {
            "tradicao_declarada": None,
            "nacao_declarada": None,
            "componentes": [],
            "categoria_analitica": None,
            "metodo": "ausente",
            "revisao_humana": "nao_aplicavel",
        },
        "identificadores": {
            "cnpj": None,
            "ceao_id": "123",
            "osm_id": None,
            "google_place_id": None,
        },
        "fontes": [
            {
                "fonte": "ceao",
                "id_fonte": "123",
                "url": None,
                "campos_contribuidos": ["nome.preferido"],
                "data_coleta": "2026-08-06",
            }
        ],
        "qualidade": {
            "status_validacao_geografica": "inconclusivo",
            "confianca": 0.5,
            "flags": [],
            "grupo_reconciliacao": None,
        },
        "valores_originais": {
            "ceao": {"NOME": "Ilê Axé Exemplo"},
        },
    }


def test_entidade_minima_e_valida(schema, entidade_minima):
    jsonschema.validate(entidade_minima, schema)


def test_entidade_sem_id_e_invalida(schema, entidade_minima):
    entidade = copy.deepcopy(entidade_minima)
    del entidade["entity_id"]

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


@pytest.mark.parametrize("entity_id", ["ceao_123", "trr_", "trr id"])
def test_entity_id_deve_usar_prefixo_e_identificador_estavel(
    schema, entidade_minima, entity_id
):
    entidade = copy.deepcopy(entidade_minima)
    entidade["entity_id"] = entity_id

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


@pytest.mark.parametrize(
    ("secao", "campo"),
    [
        ("localizacao", "status_territorial"),
        ("identidade_religiosa", "metodo"),
        ("identidade_religiosa", "revisao_humana"),
        ("qualidade", "status_validacao_geografica"),
    ],
)
def test_enums_rejeitam_valores_desconhecidos(
    schema, entidade_minima, secao, campo
):
    entidade = copy.deepcopy(entidade_minima)
    entidade[secao][campo] = "valor_desconhecido"

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


@pytest.mark.parametrize(
    ("campo", "valor"),
    [("uf", "Ba"), ("codigo_ibge_municipio", "292740")],
)
def test_uf_e_codigo_ibge_rejeitam_formatos_invalidos(
    schema, entidade_minima, campo, valor
):
    entidade = copy.deepcopy(entidade_minima)
    entidade["localizacao"][campo] = valor

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("latitude", 90.1),
        ("latitude", -90.1),
        ("longitude", 180.1),
        ("longitude", -180.1),
    ],
)
def test_coordenadas_rejeitam_valores_fora_dos_limites_globais(
    schema, entidade_minima, campo, valor
):
    entidade = copy.deepcopy(entidade_minima)
    entidade["localizacao"][campo] = valor

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


@pytest.mark.parametrize("valor", [-0.01, 1.01])
def test_confianca_deve_ficar_entre_zero_e_um(schema, entidade_minima, valor):
    entidade = copy.deepcopy(entidade_minima)
    entidade["qualidade"]["confianca"] = valor

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


@pytest.mark.parametrize("campo", ["fonte", "id_fonte"])
def test_fonte_exige_nome_e_id_nao_vazios(schema, entidade_minima, campo):
    entidade = copy.deepcopy(entidade_minima)
    entidade["fontes"][0][campo] = ""

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


def test_entidade_exige_ao_menos_uma_fonte(schema, entidade_minima):
    entidade = copy.deepcopy(entidade_minima)
    entidade["fontes"] = []

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


def test_valores_originais_preservam_estruturas_json(schema, entidade_minima):
    entidade = copy.deepcopy(entidade_minima)
    entidade["valores_originais"]["google"] = {
        "types": ["place_of_worship", "establishment"],
        "geometry": {"location": {"lat": -12.9, "lng": -38.5}},
        "campo_nulo": None,
    }

    jsonschema.validate(entidade, schema)


@pytest.mark.parametrize("secao", [None, "localizacao"])
def test_campos_arbitrarios_fora_de_valores_originais_sao_rejeitados(
    schema, entidade_minima, secao
):
    entidade = copy.deepcopy(entidade_minima)
    destino = entidade if secao is None else entidade[secao]
    destino["campo_legado"] = "valor"

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


def test_valores_originais_sao_organizados_por_fonte(schema, entidade_minima):
    entidade = copy.deepcopy(entidade_minima)
    entidade["valores_originais"] = {"ceao": "registro sem estrutura"}

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)
