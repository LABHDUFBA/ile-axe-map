import copy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/terreiro-v3.schema.json"
CATALOG_PATH = ROOT / "config/national_fields_v3.json"

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


def entidade_sintetica_completa():
    return {
        "entity_id": "trr_sintetico_001",
        "identificadores": {
            "cnpj": None,
            "ceao_id": "sintetico-001",
            "osm_id": None,
            "google_place_id": None,
            "sefaz_codigo": None,
            "id_nativo": None,
        },
        "nome": {
            "preferido": "Casa Sintética de Teste",
            "declarado": "Casa Sintética de Teste",
            "juridico_declarado": None,
            "aliases": [],
            "normalizado_match": "casa sintetica de teste",
        },
        "identificacao": {"descricao_declarada": None},
        "localizacao": {
            "latitude": None,
            "longitude": None,
            "fonte_coordenada": None,
            "precisao": None,
            "uf": "BA",
            "municipio": "Município Sintético",
            "codigo_ibge_municipio": "2900000",
            "bairro": None,
            "cep": None,
            "endereco_original": None,
            "endereco_declarado": None,
            "logradouro_declarado": None,
            "numero_declarado": None,
            "complemento_declarado": None,
            "bairro_declarado": None,
            "municipio_declarado": "Município Sintético",
            "uf_declarada": "BA",
            "codigo_municipio_declarado": None,
            "cep_declarado": None,
            "status_territorial": "sem_coordenada",
        },
        "geocodificacao": {
            "resultado": {
                "latitude": None,
                "longitude": None,
                "osm_id": None,
                "osm_tipo": None,
                "endereco": None,
            },
            "consulta": None,
            "status": None,
            "precisao": None,
            "confianca": None,
            "tipo_endereco": None,
        },
        "identidade_religiosa": {
            "tradicao_declarada": None,
            "nacao_declarada": None,
            "denominacao_declarada": None,
            "linhagem_declarada": None,
            "categoria_declarada": None,
            "componentes": [],
            "nacao_normalizada": None,
            "categoria_normalizada": None,
            "categoria_analitica": None,
            "metodo": "ausente",
            "revisao_humana": "nao_aplicavel",
        },
        "organizacao": {
            "lideranca_declarada": None,
            "regente_declarado": None,
            "data_inicio_cadastral_declarada": None,
            "ano_fundacao_declarado": None,
            "situacao_cadastral": None,
        },
        "patrimonio": {
            "tombamento": None,
            "cadastro_reconhecimento": None,
            "protecao": None,
            "orgao": None,
            "ato_data": None,
        },
        "contato": {
            "telefone_declarado": None,
            "email_declarado": None,
            "site_declarado": None,
        },
        "midia": {"imagem_principal_url": None, "miniatura_url": None},
        "publicacao": {
            "permitir_contato": None,
            "permitir_lideranca": None,
            "permitir_localizacao_precisa": None,
            "permitir_midia": None,
        },
        "fontes": [
            {
                "fonte": "fonte_sintetica_a",
                "id_fonte": "registro-001",
                "url": None,
                "campos_contribuidos": ["nome.preferido"],
                "data_coleta": "2026-08-06",
            }
        ],
        "proveniencia": {
            "fonte": "fonte_sintetica_a",
            "id_fonte": "registro-001",
            "url_registro": None,
            "descricao_fonte": None,
            "data_coleta": "2026-08-06",
            "metodo_recuperacao": None,
            "fontes_relacionadas": [],
        },
        "qualidade": {
            "status_validacao_geografica": "inconclusivo",
            "confianca": 0.5,
            "flags": [],
            "grupo_reconciliacao": None,
            "status_geografico": None,
            "metodo_classificacao": None,
            "avaliacao_fonte": None,
            "quantidade_avaliacoes_fonte": None,
        },
        "contribuicoes_campos": [],
        "valores_originais": [
            {
                "fonte": "fonte_sintetica_a",
                "id_fonte": "registro-001",
                "dados": {"NOME": "Casa Sintética de Teste"},
            }
        ],
        "revisao": {
            "status": None,
            "responsavel": None,
            "data": None,
            "observacoes": None,
        },
    }


@pytest.fixture
def entidade_minima():
    return entidade_sintetica_completa()


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


GRUPOS_NACIONAIS = [
    "identificadores",
    "nome",
    "identificacao",
    "localizacao",
    "geocodificacao",
    "identidade_religiosa",
    "organizacao",
    "patrimonio",
    "contato",
    "midia",
    "publicacao",
    "fontes",
    "proveniencia",
    "qualidade",
    "contribuicoes_campos",
    "valores_originais",
    "revisao",
]


@pytest.mark.parametrize("grupo", GRUPOS_NACIONAIS)
def test_todos_os_grupos_nacionais_sao_obrigatorios(schema, entidade_minima, grupo):
    entidade = copy.deepcopy(entidade_minima)
    del entidade[grupo]

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


@pytest.mark.parametrize(
    ("grupo", "campo"),
    [
        (grupo, campo)
        for grupo in [
            "identificadores",
            "nome",
            "identificacao",
            "localizacao",
            "identidade_religiosa",
            "organizacao",
            "patrimonio",
            "contato",
            "midia",
            "publicacao",
            "proveniencia",
            "qualidade",
            "revisao",
        ]
        for campo in entidade_sintetica_completa()[grupo]
    ]
    + [
        ("geocodificacao", campo)
        for campo in entidade_sintetica_completa()["geocodificacao"]
    ],
)
def test_todos_os_campos_nacionais_sao_obrigatorios(
    schema, entidade_minima, grupo, campo
):
    entidade = copy.deepcopy(entidade_minima)
    del entidade[grupo][campo]

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


def test_todos_os_campos_do_resultado_geocodificacao_sao_obrigatorios(
    schema, entidade_minima
):
    for campo in list(entidade_minima["geocodificacao"]["resultado"]):
        entidade = copy.deepcopy(entidade_minima)
        del entidade["geocodificacao"]["resultado"][campo]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(entidade, schema)


@pytest.mark.parametrize(
    ("grupo", "campo"),
    [
        ("nome", "preferido"),
        ("nome", "aliases"),
        ("localizacao", "complemento_declarado"),
        ("identidade_religiosa", "tradicao_declarada"),
        ("organizacao", "situacao_cadastral"),
        ("contato", "email_declarado"),
        ("publicacao", "permitir_contato"),
        ("midia", "imagem_principal_url"),
    ],
)
def test_variavel_nacional_nao_coletada_e_null_e_valida(
    schema, entidade_minima, grupo, campo
):
    entidade = copy.deepcopy(entidade_minima)
    entidade[grupo][campo] = None
    jsonschema.validate(entidade, schema)


@pytest.mark.parametrize(
    ("grupo", "campo"),
    [
        ("nome", "preferido"),
        ("contato", "email_declarado"),
        ("contato", "site_declarado"),
        ("organizacao", "data_inicio_cadastral_declarada"),
    ],
)
def test_string_vazia_nao_substitui_null(schema, entidade_minima, grupo, campo):
    entidade = copy.deepcopy(entidade_minima)
    entidade[grupo][campo] = ""
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


@pytest.mark.parametrize("valor", [None, []])
def test_array_distingue_nao_coletado_de_coletado_sem_itens(
    schema, entidade_minima, valor
):
    entidade = copy.deepcopy(entidade_minima)
    entidade["nome"]["aliases"] = valor
    jsonschema.validate(entidade, schema)


def test_geocodificacao_nao_preenche_identificador_osm_da_entidade(
    schema, entidade_minima
):
    entidade = copy.deepcopy(entidade_minima)
    entidade["geocodificacao"]["resultado"]["osm_id"] = "objeto-auxiliar-99"
    entidade["identificadores"]["osm_id"] = None
    jsonschema.validate(entidade, schema)

    entidade["identificadores"]["nominatim_osm_id"] = "objeto-auxiliar-99"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


def test_data_cadastral_e_fundacao_sao_slots_distintos(schema, entidade_minima):
    entidade = copy.deepcopy(entidade_minima)
    entidade["organizacao"]["data_inicio_cadastral_declarada"] = "2001-02-03"
    entidade["organizacao"]["ano_fundacao_declarado"] = "1984"
    jsonschema.validate(entidade, schema)


def test_contribuicoes_concorrentes_nao_sao_sobrescritas(schema, entidade_minima):
    base = {
        "campo_nacional": "nome.declarado",
        "campo_original": "nome",
        "metodo": None,
        "versao": None,
        "data_coleta": None,
        "qualidade": None,
        "status": None,
        "publicavel": True,
    }
    entidade = copy.deepcopy(entidade_minima)
    entidade["contribuicoes_campos"] = [
        {
            **base,
            "fonte": "fonte_sintetica_a",
            "id_fonte": "registro-001",
            "estado": "declarado",
            "valor": "Casa Sintética A",
        },
        {
            **base,
            "fonte": "fonte_sintetica_b",
            "id_fonte": "registro-002",
            "estado": "normalizado",
            "valor": "Casa Sintética B",
        },
        {
            **base,
            "fonte": "processo_sintetico",
            "id_fonte": "execucao-001",
            "estado": "inferido",
            "valor": "Casa Sintética C",
            "metodo": "classificador_teste",
            "versao": "1.0",
        },
    ]
    jsonschema.validate(entidade, schema)
    assert [item["valor"] for item in entidade["contribuicoes_campos"]] == [
        "Casa Sintética A",
        "Casa Sintética B",
        "Casa Sintética C",
    ]


def test_contribuicao_rejeita_valor_null(schema, entidade_minima):
    entidade = copy.deepcopy(entidade_minima)
    entidade["contribuicoes_campos"] = [
        {
            "campo_nacional": "nome.declarado",
            "fonte": "fonte_sintetica_a",
            "id_fonte": "registro-001",
            "campo_original": "nome",
            "estado": "declarado",
            "valor": None,
            "metodo": None,
            "versao": None,
            "data_coleta": None,
            "qualidade": None,
            "status": None,
            "publicavel": False,
        }
    ]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


@pytest.mark.parametrize("grupo", ["geocodificacao", "organizacao", "publicacao", "revisao"])
def test_novos_grupos_rejeitam_propriedade_extra(schema, entidade_minima, grupo):
    entidade = copy.deepcopy(entidade_minima)
    entidade[grupo]["campo_extra"] = None
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(entidade, schema)


@pytest.mark.parametrize("valor", [None, True, False])
def test_controle_publicacao_e_nullable_boolean(schema, entidade_minima, valor):
    entidade = copy.deepcopy(entidade_minima)
    entidade["publicacao"]["permitir_localizacao_precisa"] = valor
    jsonschema.validate(entidade, schema)


def test_schema_e_metavalidado_no_draft_2020_12(schema):
    jsonschema.Draft202012Validator.check_schema(schema)
