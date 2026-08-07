import json
import math
from pathlib import Path

import jsonschema
import pytest

from scripts.v3.adapters.common import (
    build_base_source_record,
    empty_audit_flags,
    make_source_record_key,
    normalize_source_id,
    synthetic_source_id,
    valid_cnpj,
)


ROOT = Path(__file__).resolve().parents[2]

PORTAS_VALIDAS = (
    "0",
    "1",
    "80",
    "443",
    "9999",
    "10000",
    "59999",
    "60000",
    "64999",
    "65000",
    "65499",
    "65500",
    "65529",
    "65530",
    "65535",
)
PORTAS_INVALIDAS = ("", "-1", "+80", "01", "65536", "70000", "abc")
IPV6_VALIDOS = (
    "::",
    "::1",
    "2001:db8::1",
    "2001:db8:0:1:2:3:4:5",
    "::ffff:192.0.2.128",
    "::192.0.2.1",
    "1:2:3:4:5:6:192.0.2.1",
)
IPV6_INVALIDOS = (
    "",
    ":::",
    "12345::1",
    "1:2:3:4:5:6:7:8:9",
    "gggg::1",
    "::ffff:256.0.0.1",
    "::ffff:192.0.2",
    "::ffff::192.0.2.1",
    "1:2:3:4:5:6:7:192.0.2.1",
)


def _gerar_cnpj_sintetico(base: str) -> str:
    """Gera dígitos verificadores para uma base explicitamente fictícia."""
    assert len(base) == 12 and base.isdigit()

    def digito(prefixo, pesos):
        resto = sum(int(valor) * peso for valor, peso in zip(prefixo, pesos)) % 11
        return "0" if resto < 2 else str(11 - resto)

    primeiro = digito(base, (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
    segundo = digito(base + primeiro, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
    return base + primeiro + segundo


def _mascarar_cnpj(cnpj: str) -> str:
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


CNPJS_SINTETICOS = tuple(
    _gerar_cnpj_sintetico(base)
    for base in ("999999990001", "888888880001", "777777770001")
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(" 00123 ", "00123"), (0, "0"), (123, "123"), ("ação", "ação")],
)
def test_normalize_source_id_aceita_texto_e_inteiro_nao_booleano(value, expected):
    assert normalize_source_id(value) == expected


@pytest.mark.parametrize(
    "value",
    [None, True, False, 1.0, math.nan, math.inf, -math.inf, "", "   ", [], {}],
)
def test_normalize_source_id_rejeita_tipos_ambiguos_ausentes_e_vazios(value):
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


def test_synthetic_source_id_preserva_tipos_das_partes():
    ids = {
        synthetic_source_id("osm", value)
        for value in (1, "1", 1.0, True, "True", None)
    }

    assert len(ids) == 6


def test_synthetic_source_id_preserva_texto_exatamente():
    assert synthetic_source_id("osm", " x ") != synthetic_source_id("osm", "x")


@pytest.mark.parametrize(
    "parts",
    [(), ("",), ("   ",), (math.nan,), (math.inf,), (-math.inf,), ([],), ({},)],
)
def test_synthetic_source_id_rejeita_partes_fracas_nao_finitas_ou_estruturais(parts):
    with pytest.raises((TypeError, ValueError)):
        synthetic_source_id("ceao", *parts)


@pytest.mark.parametrize(
    "value",
    [
        _mascarar_cnpj(CNPJS_SINTETICOS[0]),
        CNPJS_SINTETICOS[1],
        _mascarar_cnpj(CNPJS_SINTETICOS[2]),
    ],
)
def test_valid_cnpj_aceita_cnpjs_sinteticos_validos_com_e_sem_mascara(value):
    assert valid_cnpj(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "11.111.111/1111-11",
        CNPJS_SINTETICOS[0][:-1] + ("0" if CNPJS_SINTETICOS[0][-1] != "0" else "1"),
        CNPJS_SINTETICOS[1] + "9",
        "123",
        "",
        None,
        int(CNPJS_SINTETICOS[0]),
        [_mascarar_cnpj(CNPJS_SINTETICOS[1])],
        {"cnpj": CNPJS_SINTETICOS[2]},
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


def test_build_base_source_record_faz_copia_profunda_dos_mutaveis():
    payload = {"objeto": {"lista": [1]}}
    alternativa = {
        "latitude": -12.9,
        "longitude": -38.5,
        "fonte": "geocodificador",
        "precisao": None,
    }
    flags = {"baseline_atual": True}

    record = build_base_source_record(
        fonte="ceao",
        id_fonte="1",
        id_fonte_sintetico=False,
        nome_original="Teste",
        dados_originais=payload,
        coordenadas_alternativas=[alternativa],
        flags_auditoria=flags,
    )
    payload["objeto"]["lista"].append(2)
    alternativa["latitude"] = 0
    flags["baseline_atual"] = False

    assert record["dados_originais"] == {"objeto": {"lista": [1]}}
    assert record["localizacao_original"]["coordenadas_alternativas"][0][
        "latitude"
    ] == -12.9
    assert record["flags_auditoria"]["baseline_atual"] is True


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (None, -38.5),
        (-12.9, None),
        (True, -38.5),
        (-12.9, False),
        (math.nan, -38.5),
        (-12.9, math.inf),
        (-90.1, -38.5),
        (-12.9, 180.1),
    ],
)
def test_build_base_source_record_rejeita_coordenadas_principais_invalidas(
    latitude, longitude
):
    with pytest.raises((TypeError, ValueError), match="coordenada|latitude|longitude"):
        build_base_source_record(
            fonte="osm",
            id_fonte="1",
            id_fonte_sintetico=False,
            nome_original=None,
            dados_originais={},
            latitude=latitude,
            longitude=longitude,
        )


def test_build_base_source_record_mescla_flags_parciais_com_defaults():
    record = build_base_source_record(
        fonte="osm",
        id_fonte="1",
        id_fonte_sintetico=False,
        nome_original=None,
        dados_originais={},
        flags_auditoria={"ambiguo_pendente": True},
    )

    assert record["flags_auditoria"] == {
        "baseline_atual": False,
        "exclusao_curada": False,
        "remocao_heuristica_legada": False,
        "ambiguo_pendente": True,
        "dedup_legado_recuperado": False,
    }


@pytest.mark.parametrize(
    "flags", [{"desconhecida": True}, {"baseline_atual": 1}, {"baseline_atual": "sim"}]
)
def test_build_base_source_record_rejeita_flags_invalidas(flags):
    with pytest.raises((TypeError, ValueError), match="flag"):
        build_base_source_record(
            fonte="osm",
            id_fonte="1",
            id_fonte_sintetico=False,
            nome_original=None,
            dados_originais={},
            flags_auditoria=flags,
        )


@pytest.mark.parametrize(
    "alternativa",
    [
        {"latitude": -12.9, "longitude": -38.5, "fonte": "geo"},
        {
            "latitude": True,
            "longitude": -38.5,
            "fonte": "geo",
            "precisao": None,
        },
        {
            "latitude": -12.9,
            "longitude": 181,
            "fonte": "geo",
            "precisao": None,
        },
        {
            "latitude": -12.9,
            "longitude": -38.5,
            "fonte": " ",
            "precisao": None,
        },
    ],
)
def test_build_base_source_record_rejeita_coordenada_alternativa_invalida(alternativa):
    with pytest.raises((TypeError, ValueError), match="alternativa"):
        build_base_source_record(
            fonte="osm",
            id_fonte="1",
            id_fonte_sintetico=False,
            nome_original=None,
            dados_originais={},
            coordenadas_alternativas=[alternativa],
        )


@pytest.mark.parametrize("alternativas", [False, {}, ()])
def test_build_base_source_record_rejeita_colecao_de_alternativas_que_nao_e_lista(
    alternativas,
):
    with pytest.raises(TypeError, match="alternativas"):
        build_base_source_record(
            fonte="osm",
            id_fonte="1",
            id_fonte_sintetico=False,
            nome_original=None,
            dados_originais={},
            coordenadas_alternativas=alternativas,
        )


@pytest.mark.parametrize("nome", ["", "   ", 123, False, [], {}])
def test_build_base_source_record_rejeita_nome_original_invalido(nome):
    with pytest.raises((TypeError, ValueError), match="nome_original"):
        build_base_source_record(
            fonte="osm",
            id_fonte="1",
            id_fonte_sintetico=False,
            nome_original=nome,
            dados_originais={},
        )


def test_build_base_source_record_preserva_nome_original_valido():
    record = build_base_source_record(
        fonte="osm",
        id_fonte="1",
        id_fonte_sintetico=False,
        nome_original="  Ilê Axé  ",
        dados_originais={},
    )

    assert record["nome_original"] == "  Ilê Axé  "


@pytest.mark.parametrize(
    "data_coleta",
    ["2026-02-31", "2026-2-01", "01-02-2026", "2026-01-01T00:00:00", "", 20260807],
)
def test_build_base_source_record_rejeita_data_coleta_invalida(data_coleta):
    with pytest.raises((TypeError, ValueError), match="data_coleta"):
        build_base_source_record(
            fonte="osm",
            id_fonte="1",
            id_fonte_sintetico=False,
            nome_original=None,
            dados_originais={},
            data_coleta=data_coleta,
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://",
        "https://",
        "https://@",
        "https://@example.org",
        "https://user@",
        "https://user@:443/x",
        "https://user@@example.org/x",
        "https://@@example.org/x",
        "/relativa",
        "ftp://example.org/a",
        "https://exa mple.org",
        "https://example.org:abc/a",
        "https://example.org:70000/a",
        123,
    ],
)
def test_build_base_source_record_rejeita_url_invalida(url):
    with pytest.raises((TypeError, ValueError), match="url"):
        build_base_source_record(
            fonte="osm",
            id_fonte="1",
            id_fonte_sintetico=False,
            nome_original=None,
            dados_originais={},
            url=url,
        )


def test_build_base_source_record_aceita_url_ipv6_bracketed():
    url = "https://[2001:db8::1]:8443/a?b=c"
    record = build_base_source_record(
        fonte="osm",
        id_fonte="1",
        id_fonte_sintetico=False,
        nome_original=None,
        dados_originais={},
        url=url,
    )

    assert record["identificadores"]["url"] == url


@pytest.mark.parametrize(
    ("url", "aceita"),
    [
        *((f"https://example.org:{porta}/x", True) for porta in PORTAS_VALIDAS),
        *((f"https://example.org:{porta}/x", False) for porta in PORTAS_INVALIDAS),
        *((f"https://[{host}]:443/x", True) for host in IPV6_VALIDOS),
        *((f"https://[{host}]/x", False) for host in IPV6_INVALIDOS),
        ("https://user%40dominio@example.org/x", True),
        ("https://user@@example.org/x", False),
        ("https://@@example.org/x", False),
    ],
)
def test_builder_e_schema_concordam_na_matriz_de_urls(url, aceita):
    schema = json.loads(
        (ROOT / "schemas/source-record-v3.schema.json").read_text(encoding="utf-8")
    )
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    arguments = {
        "fonte": "osm",
        "id_fonte": "1",
        "id_fonte_sintetico": False,
        "nome_original": None,
        "dados_originais": {},
        "url": url,
    }

    if aceita:
        record = build_base_source_record(**arguments)
        assert list(validator.iter_errors(record)) == []
    else:
        with pytest.raises(ValueError, match="url"):
            build_base_source_record(**arguments)
        registro = build_base_source_record(**{**arguments, "url": None})
        registro["identificadores"]["url"] = url
        assert list(validator.iter_errors(registro))


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("ceao_id", 123),
        ("osm_id", False),
        ("google_place_id", []),
        ("cnpj", int(CNPJS_SINTETICOS[0])),
    ],
)
def test_build_base_source_record_rejeita_identificador_nao_textual(campo, valor):
    with pytest.raises(TypeError, match=campo):
        build_base_source_record(
            fonte="osm",
            id_fonte="1",
            id_fonte_sintetico=False,
            nome_original=None,
            dados_originais={},
            **{campo: valor},
        )


def test_build_base_source_record_rejeita_identificador_desconhecido():
    arguments = {
        "fonte": "osm",
        "id_fonte": "1",
        "id_fonte_sintetico": False,
        "nome_original": None,
        "dados_originais": {},
        "identificador_desconhecido": "valor",
    }

    with pytest.raises(TypeError, match="identificador_desconhecido"):
        build_base_source_record(**arguments)


@pytest.mark.parametrize(
    "cnpj",
    [
        CNPJS_SINTETICOS[0][:-1] + ("0" if CNPJS_SINTETICOS[0][-1] != "0" else "1"),
        "11.111.111/1111-11",
        "123",
    ],
)
def test_build_base_source_record_rejeita_cnpj_invalido(cnpj):
    with pytest.raises(ValueError, match="cnpj"):
        build_base_source_record(
            fonte="cnpj",
            id_fonte=cnpj,
            id_fonte_sintetico=False,
            nome_original=None,
            dados_originais={},
            cnpj=cnpj,
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {"nome_original": "  Ilê Axé  ", "data_coleta": "2024-02-29"},
        {
            "latitude": -12.9,
            "longitude": -38.5,
            "url": "https://example.org:8443/registro?id=1#fonte",
            "ceao_id": "00123",
        },
        {"url": "http://127.0.0.1:8080/caminho?x=1"},
        {"url": "http://localhost:8000/registro"},
        {"url": "https://usuario:senha@example.org:8443/a?b=c#d"},
        {
            "url": "https://[2001:db8::1]:8443/a?b=c",
            "cnpj": _mascarar_cnpj(CNPJS_SINTETICOS[0]),
        },
    ],
)
def test_build_base_source_record_retorna_registro_valido_no_schema(overrides):
    schema = json.loads(
        (ROOT / "schemas/source-record-v3.schema.json").read_text(encoding="utf-8")
    )
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    arguments = {
        "fonte": "osm",
        "id_fonte": "1",
        "id_fonte_sintetico": False,
        "nome_original": None,
        "dados_originais": {},
    }
    arguments.update(overrides)

    record = build_base_source_record(**arguments)

    assert list(validator.iter_errors(record)) == []
