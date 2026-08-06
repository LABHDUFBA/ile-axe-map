import copy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/terreiro-v3.schema.json"

CAMPOS_CANONICOS_CONTRIBUIVEIS = [
    "entity_id",
    "nome.preferido",
    "nome.aliases",
    "nome.normalizado_match",
    "localizacao.latitude",
    "localizacao.longitude",
    "localizacao.fonte_coordenada",
    "localizacao.precisao",
    "localizacao.uf",
    "localizacao.municipio",
    "localizacao.codigo_ibge_municipio",
    "localizacao.bairro",
    "localizacao.cep",
    "localizacao.endereco_original",
    "localizacao.status_territorial",
    "identidade_religiosa.tradicao_declarada",
    "identidade_religiosa.nacao_declarada",
    "identidade_religiosa.componentes",
    "identidade_religiosa.categoria_analitica",
    "identidade_religiosa.metodo",
    "identidade_religiosa.revisao_humana",
    "identificadores.cnpj",
    "identificadores.ceao_id",
    "identificadores.osm_id",
    "identificadores.google_place_id",
    "qualidade.status_validacao_geografica",
    "qualidade.confianca",
    "qualidade.flags",
    "qualidade.grupo_reconciliacao",
]


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def validator(schema):
    return jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )


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
        "valores_originais": [
            {
                "fonte": "ceao",
                "id_fonte": "123",
                "dados": {"NOME": "Ilê Axé Exemplo"},
            }
        ],
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


@pytest.mark.parametrize("campo", ["latitude", "longitude"])
def test_sem_coordenada_exige_ambas_coordenadas_nulas(
    schema, entidade_minima, campo
):
    entidade = copy.deepcopy(entidade_minima)
    entidade["localizacao"][campo] = -12.9 if campo == "latitude" else -38.5

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


@pytest.mark.parametrize("status", ["intersecao_ibge", "fora_poligono"])
@pytest.mark.parametrize("campo", ["latitude", "longitude"])
def test_status_com_coordenada_exige_ambas_coordenadas_numericas(
    schema, entidade_minima, status, campo
):
    entidade = copy.deepcopy(entidade_minima)
    entidade["localizacao"].update(
        {
            "latitude": -12.9,
            "longitude": -38.5,
            "status_territorial": status,
        }
    )
    entidade["localizacao"][campo] = None

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("uf", None),
        ("uf", ""),
        ("uf", "Ba"),
        ("municipio", None),
        ("municipio", ""),
        ("codigo_ibge_municipio", None),
        ("codigo_ibge_municipio", ""),
        ("codigo_ibge_municipio", "292740"),
    ],
)
def test_intersecao_ibge_exige_identificacao_territorial_valida(
    schema, entidade_minima, campo, valor
):
    entidade = copy.deepcopy(entidade_minima)
    entidade["localizacao"].update(
        {
            "latitude": -12.9,
            "longitude": -38.5,
            "status_territorial": "intersecao_ibge",
        }
    )
    entidade["localizacao"][campo] = valor

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


@pytest.mark.parametrize("status", ["confirmado", "provavel"])
def test_sem_coordenada_exige_validacao_geografica_inconclusiva(
    schema, entidade_minima, status
):
    entidade = copy.deepcopy(entidade_minima)
    entidade["qualidade"]["status_validacao_geografica"] = status

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


def test_validacao_geografica_confirmada_exige_coordenadas(
    schema, entidade_minima
):
    entidade = copy.deepcopy(entidade_minima)
    entidade["qualidade"]["status_validacao_geografica"] = "confirmado"

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("tradicao_declarada", "Candomblé"),
        ("nacao_declarada", "Ketu"),
        ("categoria_analitica", "candomble_ketu"),
        ("componentes", ["Ketu"]),
        ("revisao_humana", "pendente"),
    ],
)
def test_metodo_ausente_exige_identidade_sem_classificacao(
    schema, entidade_minima, campo, valor
):
    entidade = copy.deepcopy(entidade_minima)
    entidade["identidade_religiosa"][campo] = valor

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("categoria_analitica", None),
        ("categoria_analitica", ""),
        ("revisao_humana", "nao_aplicavel"),
    ],
)
def test_metodo_inferido_nome_exige_categoria_e_revisao_humana(
    schema, entidade_minima, campo, valor
):
    entidade = copy.deepcopy(entidade_minima)
    entidade["identidade_religiosa"].update(
        {
            "categoria_analitica": "candomble_ketu",
            "metodo": "inferido_nome",
            "revisao_humana": "pendente",
        }
    )
    entidade["identidade_religiosa"][campo] = valor

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


@pytest.mark.parametrize("revisao", ["pendente", "aprovado"])
def test_metodo_inferido_nome_aceita_revisoes_previstas(
    schema, entidade_minima, revisao
):
    entidade = copy.deepcopy(entidade_minima)
    entidade["identidade_religiosa"].update(
        {
            "categoria_analitica": "candomble_ketu",
            "metodo": "inferido_nome",
            "revisao_humana": revisao,
        }
    )

    jsonschema.validate(entidade, schema)


@pytest.mark.parametrize("campo", ["fonte", "id_fonte"])
def test_fonte_exige_nome_e_id_nao_vazios(schema, entidade_minima, campo):
    entidade = copy.deepcopy(entidade_minima)
    entidade["fontes"][0][campo] = ""

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


def test_data_coleta_aceita_null_para_fonte_legada(validator, entidade_minima):
    entidade = copy.deepcopy(entidade_minima)
    entidade["fontes"][0]["data_coleta"] = None

    validator.validate(entidade)


def test_data_coleta_rejeita_data_calendario_invalida(validator, entidade_minima):
    entidade = copy.deepcopy(entidade_minima)
    entidade["fontes"][0]["data_coleta"] = "2026-02-31"

    with pytest.raises(jsonschema.ValidationError):
        validator.validate(entidade)


@pytest.mark.parametrize(
    "caminho", ["nome", "nome.inexistente", "fontes[].fonte", "campo_arbitrario"]
)
def test_campos_contribuidos_rejeitam_caminhos_nao_canonicos(
    schema, entidade_minima, caminho
):
    entidade = copy.deepcopy(entidade_minima)
    entidade["fontes"][0]["campos_contribuidos"] = [caminho]

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


@pytest.mark.parametrize("caminho", CAMPOS_CANONICOS_CONTRIBUIVEIS)
def test_campos_contribuidos_aceitam_campos_folha_canonicos(
    schema, entidade_minima, caminho
):
    entidade = copy.deepcopy(entidade_minima)
    entidade["fontes"][0]["campos_contribuidos"] = [caminho]

    jsonschema.validate(entidade, schema)


def test_entidade_exige_ao_menos_uma_fonte(schema, entidade_minima):
    entidade = copy.deepcopy(entidade_minima)
    entidade["fontes"] = []

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


def test_formato_antigo_de_valores_originais_e_rejeitado(schema, entidade_minima):
    entidade = copy.deepcopy(entidade_minima)
    entidade["valores_originais"] = {
        "ceao": {"NOME": "Ilê Axé Exemplo"},
    }

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


def test_valores_originais_aceitam_lista_minima_valida(schema, entidade_minima):
    jsonschema.validate(entidade_minima, schema)


def test_valores_originais_aceitam_dois_registros_da_mesma_fonte(
    schema, entidade_minima
):
    entidade = copy.deepcopy(entidade_minima)
    entidade["valores_originais"].append(
        {
            "fonte": "ceao",
            "id_fonte": "456",
            "dados": {"NOME": "Outro registro da mesma fonte"},
        }
    )

    jsonschema.validate(entidade, schema)


@pytest.mark.parametrize("campo", ["fonte", "id_fonte"])
def test_valores_originais_rejeitam_fonte_e_id_vazios(
    schema, entidade_minima, campo
):
    entidade = copy.deepcopy(entidade_minima)
    entidade["valores_originais"][0][campo] = ""

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


def test_valores_originais_rejeitam_campos_extras_no_item(
    schema, entidade_minima
):
    entidade = copy.deepcopy(entidade_minima)
    entidade["valores_originais"][0]["campo_extra"] = "valor"

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


def test_valores_originais_preservam_payload_json_arbitrario(
    schema, entidade_minima
):
    entidade = copy.deepcopy(entidade_minima)
    entidade["valores_originais"][0]["dados"] = {
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


def test_valores_originais_exigem_ao_menos_um_registro(schema, entidade_minima):
    entidade = copy.deepcopy(entidade_minima)
    entidade["valores_originais"] = []

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)
