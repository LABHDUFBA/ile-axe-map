import copy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/source-record-v3.schema.json"

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


CNPJ_SINTETICO = _gerar_cnpj_sintetico("999999990001")


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
            "cnpj": _mascarar_cnpj(CNPJ_SINTETICO),
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


@pytest.mark.parametrize(
    "url",
    [
        "não é uma URI",
        "http://",
        "https://",
        "https://@",
        "https://user@",
        "https://user@:443/x",
        "https://user@@example.org/x",
        "https://@@example.org/x",
        "https://:443/caminho",
        "/caminho/relativo",
        "https://exa mple.org",
    ],
)
def test_schema_rejeita_url_invalida(validator, registro_completo, url):
    registro = copy.deepcopy(registro_completo)
    registro["identificadores"]["url"] = url

    with pytest.raises(jsonschema.ValidationError):
        validator.validate(registro)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.org/registro?id=1#detalhes",
        "http://127.0.0.1:8080/caminho?x=1",
        "http://localhost:8000/registro",
        "https://usuario:senha@example.org:8443/a?b=c#d",
        "https://user%40dominio@example.org/x",
        "https://[2001:db8::1]:8443/a?b=c",
    ],
)
def test_schema_aceita_url_http_absoluta_com_host(validator, registro_completo, url):
    registro = copy.deepcopy(registro_completo)
    registro["identificadores"]["url"] = url

    validator.validate(registro)


@pytest.mark.parametrize("porta", PORTAS_VALIDAS)
def test_schema_aceita_porta_decimal_canonica_na_faixa(
    validator, registro_completo, porta
):
    registro = copy.deepcopy(registro_completo)
    registro["identificadores"]["url"] = f"https://example.org:{porta}/x"

    validator.validate(registro)


@pytest.mark.parametrize("porta", PORTAS_INVALIDAS)
def test_schema_rejeita_porta_nao_canonica_ou_fora_da_faixa(
    validator, registro_completo, porta
):
    registro = copy.deepcopy(registro_completo)
    registro["identificadores"]["url"] = f"https://example.org:{porta}/x"

    with pytest.raises(jsonschema.ValidationError):
        validator.validate(registro)


@pytest.mark.parametrize("host", IPV6_VALIDOS)
def test_schema_aceita_ipv6_bracketed_valido(validator, registro_completo, host):
    registro = copy.deepcopy(registro_completo)
    registro["identificadores"]["url"] = f"https://[{host}]:443/x"

    validator.validate(registro)


@pytest.mark.parametrize("host", IPV6_INVALIDOS)
def test_schema_rejeita_ipv6_bracketed_malformado(validator, registro_completo, host):
    registro = copy.deepcopy(registro_completo)
    registro["identificadores"]["url"] = f"https://[{host}]/x"

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
