import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/terreiro-v3.schema.json"
CATALOG_PATH = ROOT / "config/national_fields_v3.json"
COVERAGE_PATH = ROOT / "data/audit/v3/source_variable_coverage.json"
MATRIX_PATH = ROOT / "data/audit/v3/source_variable_matrix.csv"

GRUPOS_CATALOGADOS = {
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
    "proveniencia",
    "qualidade",
    "revisao",
}


def _carregar(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _folhas(schema_fragmento, prefixo):
    tipo = schema_fragmento.get("type")
    if tipo == "object" and "properties" in schema_fragmento:
        resultado = set()
        for nome, filho in schema_fragmento["properties"].items():
            resultado |= _folhas(filho, f"{prefixo}.{nome}" if prefixo else nome)
        return resultado
    if tipo == ["array", "null"] and "items" in schema_fragmento:
        itens = schema_fragmento["items"]
        if itens.get("type") == "object":
            return _folhas(itens, f"{prefixo}[]")
    return {prefixo}


def test_catalogo_cobre_exatamente_folhas_nacionais_do_schema():
    schema = _carregar(SCHEMA_PATH)
    catalogo = _carregar(CATALOG_PATH)
    caminhos_schema = set()
    caminhos_schema.add("entity_id")
    for grupo in GRUPOS_CATALOGADOS:
        caminhos_schema |= _folhas(schema["properties"][grupo], grupo)
    caminhos_catalogo = [campo["caminho"] for campo in catalogo["campos"]]

    assert caminhos_catalogo == sorted(caminhos_catalogo)
    assert len(caminhos_catalogo) == len(set(caminhos_catalogo))
    assert set(caminhos_catalogo) == caminhos_schema
    assert catalogo["metacampos_tecnicos_fora_do_catalogo"] == [
        "fontes[]",
        "contribuicoes_campos[]",
        "valores_originais[]",
    ]


def test_catalogo_tem_metadados_obrigatorios_sem_valores_reais():
    catalogo = _carregar(CATALOG_PATH)
    chaves = {
        "caminho",
        "grupo",
        "tipo_logico",
        "nullable",
        "status",
        "sensibilidade_publicacao",
        "descricao",
        "fontes_contribuintes_aprovadas",
        "fontes_contribuintes_pendentes",
    }
    for campo in catalogo["campos"]:
        assert set(campo) == chaves
        assert campo["nullable"] is (campo["caminho"] != "entity_id")
        assert campo["status"] in {"aprovado", "revisar", "reservado_sem_fonte"}
        assert campo["sensibilidade_publicacao"] in {
            "publico",
            "interno",
            "controlado",
        }
        assert campo["descricao"].strip()
        for contribuicao in (
            campo["fontes_contribuintes_aprovadas"]
            + campo["fontes_contribuintes_pendentes"]
        ):
            assert set(contribuicao) == {"fonte", "campo_original"}
            assert contribuicao["fonte"].strip()
            assert contribuicao["campo_original"].strip()


def test_catalogo_reproduz_status_e_fontes_da_cobertura():
    catalogo = {campo["caminho"]: campo for campo in _carregar(CATALOG_PATH)["campos"]}
    cobertura = _carregar(COVERAGE_PATH)["campos_nacionais_propostos"]

    for caminho, esperado in cobertura.items():
        campo = catalogo[caminho]
        aprovadas = [
            {"fonte": item["fonte"], "campo_original": item["campo_original"]}
            for item in esperado["contribuicoes_aprovadas"]
        ]
        pendentes = [
            {"fonte": item["fonte"], "campo_original": item["campo_original"]}
            for item in esperado["contribuicoes_pendentes"]
        ]
        assert campo["fontes_contribuintes_aprovadas"] == aprovadas
        assert campo["fontes_contribuintes_pendentes"] == pendentes
        assert campo["status"] == ("revisar" if pendentes else "aprovado")

    with MATRIX_PATH.open(encoding="utf-8", newline="") as arquivo:
        linhas_revisar = [
            linha
            for linha in csv.DictReader(arquivo)
            if linha["incluir_formato_nacional"] == "revisar"
        ]
    pendencias_catalogadas = sum(
        len(campo["fontes_contribuintes_pendentes"]) for campo in catalogo.values()
    )
    assert len(linhas_revisar) == pendencias_catalogadas


def test_slots_sem_fonte_estao_reservados():
    catalogo = {campo["caminho"]: campo for campo in _carregar(CATALOG_PATH)["campos"]}
    reservados = {
        "identidade_religiosa.tradicao_declarada",
        "identidade_religiosa.denominacao_declarada",
        "identidade_religiosa.linhagem_declarada",
        "localizacao.complemento_declarado",
        "localizacao.codigo_ibge_municipio",
        "contato.email_declarado",
        "contato.site_declarado",
        "organizacao.situacao_cadastral",
        "patrimonio.tombamento",
        "patrimonio.cadastro_reconhecimento",
        "patrimonio.protecao",
        "patrimonio.orgao",
        "patrimonio.ato_data",
        "publicacao.permitir_contato",
        "publicacao.permitir_lideranca",
        "publicacao.permitir_localizacao_precisa",
        "publicacao.permitir_midia",
    }
    assert all(catalogo[caminho]["status"] == "reservado_sem_fonte" for caminho in reservados)


def test_catalogo_marca_campos_sensiveis_e_geocodificacao_auxiliar():
    catalogo = {campo["caminho"]: campo for campo in _carregar(CATALOG_PATH)["campos"]}
    assert catalogo["contato.telefone_declarado"]["sensibilidade_publicacao"] == "interno"
    assert catalogo["organizacao.lideranca_declarada"]["sensibilidade_publicacao"] == "interno"
    assert catalogo["organizacao.regente_declarado"]["sensibilidade_publicacao"] == "interno"
    assert catalogo["localizacao.latitude"]["sensibilidade_publicacao"] == "controlado"
    assert catalogo["localizacao.longitude"]["sensibilidade_publicacao"] == "controlado"
    assert catalogo["geocodificacao.consulta"]["sensibilidade_publicacao"] == "interno"
    assert catalogo["midia.imagem_principal_url"]["sensibilidade_publicacao"] == "controlado"
    assert "nominatim_osm_id" not in catalogo
    assert catalogo["geocodificacao.resultado.osm_id"]["grupo"] == "geocodificacao"
    assert catalogo["identificadores.osm_id"]["grupo"] == "identificadores"


def test_campos_de_contribuicao_referenciam_catalogo():
    schema = _carregar(SCHEMA_PATH)
    catalogo = {campo["caminho"] for campo in _carregar(CATALOG_PATH)["campos"]}
    enum_contribuicao = set(
        schema["properties"]["contribuicoes_campos"]["items"]["properties"]
        ["campo_nacional"]["enum"]
    )
    enum_fontes = set(
        schema["properties"]["fontes"]["items"]["properties"]
        ["campos_contribuidos"]["items"]["enum"]
    )
    assert enum_contribuicao == catalogo
    assert enum_fontes == catalogo
