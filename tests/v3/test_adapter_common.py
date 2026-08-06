import pytest

from scripts.v3.adapters.common import (
    build_base_source_record,
    empty_audit_flags,
    make_source_record_key,
    normalize_source_id,
    synthetic_source_id,
    valid_cnpj,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(" 00123 ", "00123"), (123, "123"), (False, "False"), ("ação", "ação")],
)
def test_normalize_source_id_converte_escalar_e_preserva_significado(value, expected):
    assert normalize_source_id(value) == expected


@pytest.mark.parametrize("value", [None, "", "   ", [], {}, ["id"], {"id"}])
def test_normalize_source_id_rejeita_ausente_vazio_e_estrutural(value):
    with pytest.raises((TypeError, ValueError)):
        normalize_source_id(value)


def test_make_source_record_key_preserva_zeros_a_esquerda():
    assert make_source_record_key("ceao", " 00123 ") == "ceao:00123"


def test_make_source_record_key_codifica_separadores_sem_colisao():
    ids = ["a:b", "a%3Ab", "ação:100%"]
    keys = [make_source_record_key("ceao", value) for value in ids]

    assert len(set(keys)) == len(ids)
    assert keys == [make_source_record_key("ceao", value) for value in ids]
    assert keys[0] == "ceao:a%3Ab"
    assert keys[1] == "ceao:a%253Ab"
    assert keys[2] == "ceao:a%C3%A7%C3%A3o%3A100%25"


def test_make_source_record_key_rejeita_fonte_fora_do_contrato():
    with pytest.raises(ValueError, match="fonte"):
        make_source_record_key("outra", "123")


def test_synthetic_source_id_e_deterministico_e_separa_fronteiras():
    first = synthetic_source_id("osm", "ab", "c")
    second = synthetic_source_id("osm", "a", "bc")

    assert first != second
    assert first == synthetic_source_id("osm", "ab", "c")
    assert first.startswith("synthetic:")
    assert len(first) == len("synthetic:") + 64


@pytest.mark.parametrize("parts", [(), (None,), ("",), ("   ",), ({"a": 1},)])
def test_synthetic_source_id_rejeita_partes_ausentes_vazias_ou_estruturais(parts):
    with pytest.raises((TypeError, ValueError)):
        synthetic_source_id("ceao", *parts)


@pytest.mark.parametrize(
    "value",
    ["04.858.642/0001-87", "05419205000120", "10.344.860/0001-04"],
)
def test_valid_cnpj_aceita_os_tres_cnpjs_validos_atuais(value):
    assert valid_cnpj(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "11.111.111/1111-11",
        "04.858.642/0001-88",
        "054192050001209",
        "123",
        "",
        None,
        4858642000187,
        ["04.858.642/0001-87"],
        {"cnpj": "04.858.642/0001-87"},
    ],
)
def test_valid_cnpj_rejeita_invalidos_repetidos_e_tipos_estruturais(value):
    assert valid_cnpj(value) is False


def test_empty_audit_flags_retorna_dicionarios_independentes():
    first = empty_audit_flags()
    second = empty_audit_flags()

    assert first == {
        "baseline_atual": False,
        "exclusao_curada": False,
        "remocao_heuristica_legada": False,
        "ambiguo_pendente": False,
        "dedup_legado_recuperado": False,
    }
    first["baseline_atual"] = True
    assert second["baseline_atual"] is False


def test_build_base_source_record_monta_estrutura_sem_inferir_religiao():
    payload = {"NOME": "Registro sintético", "campo_livre": {"valor": 1}}

    record = build_base_source_record(
        fonte="ceao",
        id_fonte=" 00123 ",
        id_fonte_sintetico=False,
        nome_original="Registro sintético",
        dados_originais=payload,
        latitude=-12.9,
        longitude=-38.5,
        endereco="Rua sintética",
        municipio="Salvador",
        uf="BA",
        cep=None,
        precisao="endereco",
        fonte_coordenada="ceao",
        coordenadas_alternativas=[],
        cnpj=None,
        ceao_id="00123",
        osm_id=None,
        google_place_id=None,
        url=None,
        data_coleta=None,
    )

    assert record["source_record_key"] == "ceao:00123"
    assert record["id_fonte"] == "00123"
    assert record["identidade_religiosa_original"] == {
        "tradicao": None,
        "nacao": None,
        "denominacao": None,
    }
    assert record["dados_originais"] == payload
    assert record["flags_auditoria"] == empty_audit_flags()


def test_build_base_source_record_preserva_identidade_religiosa_fornecida():
    record = build_base_source_record(
        fonte="osm",
        id_fonte="node/1",
        id_fonte_sintetico=False,
        nome_original=None,
        dados_originais={"id": 1},
        tradicao="Umbanda",
        nacao=None,
        denominacao="Centro de Umbanda",
    )

    assert record["identidade_religiosa_original"] == {
        "tradicao": "Umbanda",
        "nacao": None,
        "denominacao": "Centro de Umbanda",
    }
    assert record["localizacao_original"]["latitude"] is None
    assert record["localizacao_original"]["longitude"] is None
