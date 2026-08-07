import csv
import io
import json
from pathlib import Path

import pytest

from scripts.v3.inventory_source_variables import (
    EXPECTED_LOGICAL_COUNTS,
    build_coverage_document,
    build_inventory,
    flatten_record,
    infer_type,
    is_filled,
    separate_bahia_sources,
    validate_logical_counts,
    write_outputs,
)


def test_flatten_nested_e_arrays_e_deterministico():
    record = {
        "z": [{"b": 1, "a": "x"}, {"a": "y"}],
        "obj": {"inside": True},
    }

    first = flatten_record(record)
    second = flatten_record({"obj": {"inside": True}, "z": record["z"]})

    assert list(first) == ["obj", "obj.inside", "z", "z[]", "z[].a", "z[].b"]
    assert first == second
    assert first["z"] == [record["z"]]
    assert first["z[]"] == record["z"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "null"),
        (True, "bool"),
        (1, "int"),
        (1.5, "float"),
        ("texto", "string"),
        ([], "list"),
        ({}, "object"),
    ],
)
def test_infer_type_distingue_tipos(value, expected):
    assert infer_type(value) == expected


def test_inventario_ignora_null_e_vazios_em_preenchidos_e_tipos():
    records = [
        {"campo": None, "texto": "", "lista": [], "objeto": {}},
        {"campo": 2, "texto": "  ", "lista": [1], "objeto": {"x": False}},
    ]

    rows = build_inventory("fonte_teste", records)
    by_field = {row["campo_original"]: row for row in rows}

    assert by_field["campo"]["tipos_observados"] == "int"
    assert by_field["campo"]["preenchidos"] == 1
    assert by_field["campo"]["cobertura_percentual"] == "50.000000"
    assert by_field["texto"]["tipos_observados"] == ""
    assert by_field["texto"]["preenchidos"] == 0
    assert by_field["lista"]["tipos_observados"] == "list"
    assert by_field["lista"]["preenchidos"] == 1
    assert by_field["objeto"]["tipos_observados"] == "object"
    assert by_field["objeto"]["preenchidos"] == 1
    assert by_field["objeto.x"]["tipos_observados"] == "bool"


@pytest.mark.parametrize(
    "value",
    [None, "", "  ", [], [None, " ", {}], {}, {"x": None}, {"x": [" ", {}]}],
)
def test_is_filled_rejeita_vazios_recursivos(value):
    assert is_filled(value) is False


@pytest.mark.parametrize(
    "value",
    [False, 0, [None, 0], {"x": False}, {"x": [{"y": "valor"}]}],
)
def test_is_filled_aceita_valor_real_aninhado(value):
    assert is_filled(value) is True


def test_geocodificacao_nao_vira_atributo_da_entidade():
    cnpj = {row["campo_original"]: row for row in build_inventory("cnpj", [{"lat": 0, "lng": 0, "precision": "x", "query_used": "x"}])}
    nominatim = {
        row["campo_original"]: row
        for row in build_inventory(
            "mapeando_axe",
            [{
                "nominatim_lat": 0,
                "nominatim_lng": 0,
                "nominatim_osm_id": 0,
                "nominatim_osm_type": "node",
                "nominatim_display_name": "x",
            }],
        )
    }

    assert cnpj["lat"]["campo_nacional"] == "geocodificacao.resultado.latitude"
    assert cnpj["lng"]["campo_nacional"] == "geocodificacao.resultado.longitude"
    assert cnpj["lat"]["regra_harmonizacao"] == "inferido_geocodificacao"
    assert cnpj["precision"]["campo_nacional"] == "geocodificacao.precisao"
    assert cnpj["query_used"]["campo_nacional"] == "geocodificacao.consulta"
    assert nominatim["nominatim_lat"]["campo_nacional"] == "geocodificacao.resultado.latitude"
    assert nominatim["nominatim_lng"]["campo_nacional"] == "geocodificacao.resultado.longitude"
    assert nominatim["nominatim_osm_id"]["campo_nacional"] == "geocodificacao.resultado.osm_id"
    assert nominatim["nominatim_osm_type"]["campo_nacional"] == "geocodificacao.resultado.osm_tipo"
    assert nominatim["nominatim_display_name"]["campo_nacional"] == "geocodificacao.resultado.endereco"
    assert all(row["regra_harmonizacao"] == "inferido_geocodificacao" for row in nominatim.values())


def test_coordenadas_do_agregado_bahia_continuam_da_entidade():
    rows = {row["campo_original"]: row for row in build_inventory("ceao", [{"lat": 0, "lng": 0}])}

    assert rows["lat"]["campo_nacional"] == "localizacao.latitude"
    assert rows["lng"]["campo_nacional"] == "localizacao.longitude"
    assert rows["lat"]["regra_harmonizacao"] == "coordenada"


def test_campos_cadastrais_e_nacao_ambigua_ficam_pendentes():
    cnpj = {row["campo_original"]: row for row in build_inventory("cnpj", [{"codigo_municipio": 1, "data_inicio": "x"}])}
    ceao = {row["campo_original"]: row for row in build_inventory("ceao", [{"nacao": "x", "nacao_original": "x"}])}

    assert cnpj["codigo_municipio"]["campo_nacional"] == "localizacao.codigo_municipio_declarado"
    assert cnpj["codigo_municipio"]["incluir_formato_nacional"] == "revisar"
    assert cnpj["data_inicio"]["campo_nacional"] == "organizacao.data_inicio_cadastral_declarada"
    assert cnpj["data_inicio"]["incluir_formato_nacional"] == "revisar"
    assert ceao["nacao"]["campo_nacional"] == "identidade_religiosa.nacao_declarada"
    assert ceao["nacao"]["incluir_formato_nacional"] == "revisar"
    assert ceao["nacao_original"]["incluir_formato_nacional"] == "revisar"


def test_separacao_bahia_nao_duplica_nem_omite():
    records = [
        {"fonte": "ceao", "id": "a"},
        {"fonte": "google", "id": "b"},
        {"fonte": "osm", "id": "c"},
        {"fonte": "sefaz", "id": "d"},
    ]

    separated = separate_bahia_sources(records, expected_total=4)

    assert list(separated) == ["bahia_google", "ceao", "osm", "sefaz"]
    assert {name: len(rows) for name, rows in separated.items()} == {
        "bahia_google": 1,
        "ceao": 1,
        "osm": 1,
        "sefaz": 1,
    }
    assert sum(map(len, separated.values())) == 4


def test_separacao_bahia_rejeita_fonte_desconhecida_e_contagem_divergente():
    with pytest.raises(ValueError, match="fonte Bahia desconhecida"):
        separate_bahia_sources([{"fonte": "surpresa"}], expected_total=1)
    with pytest.raises(ValueError, match="contagem Bahia"):
        separate_bahia_sources([{"fonte": "osm"}], expected_total=2)


def test_contagens_logicas_rejeitam_divergencia():
    counts = dict(EXPECTED_LOGICAL_COUNTS)
    counts["osm"] += 1

    with pytest.raises(ValueError, match="contagens lógicas"):
        validate_logical_counts(counts)


def test_matriz_ordenada_e_outputs_reprodutiveis_sem_valores(tmp_path):
    sources = {
        "osm": [{"nome": "SEGREDO_FIXTURE", "nested": {"telefone": "NAO_VAZAR"}}],
        "ceao": [{"nome": "OUTRO_SEGREDO", "nested": {"telefone": None}}],
    }
    rows = [row for source in sorted(sources) for row in build_inventory(source, sources[source])]
    coverage = build_coverage_document(
        rows,
        {source: len(records) for source, records in sources.items()},
        input_metadata=[{"name": "sintetico", "path": "fixture.json", "sha256": "a" * 64, "count": 2}],
        total_records=2,
    )

    first_csv = tmp_path / "first.csv"
    first_json = tmp_path / "first.json"
    second_csv = tmp_path / "second.csv"
    second_json = tmp_path / "second.json"
    write_outputs(rows, coverage, first_csv, first_json)
    write_outputs(list(reversed(rows)), coverage, second_csv, second_json)

    assert first_csv.read_bytes() == second_csv.read_bytes()
    assert first_json.read_bytes() == second_json.read_bytes()
    parsed = list(csv.DictReader(io.StringIO(first_csv.read_text(encoding="utf-8"))))
    assert [(row["fonte"], row["campo_original"]) for row in parsed] == sorted(
        (row["fonte"], row["campo_original"]) for row in parsed
    )
    combined = first_csv.read_text(encoding="utf-8") + first_json.read_text(encoding="utf-8")
    assert "SEGREDO_FIXTURE" not in combined
    assert "NAO_VAZAR" not in combined
    assert "OUTRO_SEGREDO" not in combined
    assert "examples" not in combined
    assert "valores_exemplo" not in combined


def test_campo_nacional_ausente_permanece_null_sem_imputacao():
    rows = build_inventory("osm", [{"nome": "Registro sintético"}])
    coverage = build_coverage_document(
        rows,
        {"osm": 1},
        input_metadata=[],
        total_records=1,
    )

    policy = coverage["politica_ausencia"]
    assert policy["valor_para_variavel_nao_coletada"] is None
    assert policy["imputacao_silenciosa_permitida"] is False
    assert policy["inferencia_exige_marcacao_explicita"] is True


def test_agregacao_separa_contribuicoes_aprovadas_e_pendentes():
    records = [{
        "nome": "x",
        "codigo_municipio": 1,
        "data_inicio": "x",
        "nacao": "x",
        "nacao_categoria": "x",
        "nominatim_lat": 0,
    }]
    rows = build_inventory("cnpj", records)
    coverage = build_coverage_document(rows, {"cnpj": 1}, [], 1)
    proposed = coverage["campos_nacionais_propostos"]

    assert proposed["nome.declarado"]["contribuicoes_aprovadas"] == [{
        "campo_original": "nome",
        "fonte": "cnpj",
        "incluir_formato_nacional": "sim",
        "regra_harmonizacao": "copiar_declarado",
    }]
    for field in (
        "localizacao.codigo_municipio_declarado",
        "organizacao.data_inicio_cadastral_declarada",
        "identidade_religiosa.nacao_declarada",
        "identidade_religiosa.categoria_normalizada",
    ):
        assert proposed[field]["contribuicoes_aprovadas"] == []
        assert proposed[field]["contribuicoes_pendentes"]
        assert all(item["incluir_formato_nacional"] == "revisar" for item in proposed[field]["contribuicoes_pendentes"])
    assert "geocodificacao.resultado.latitude" in proposed
    assert "localizacao.latitude" not in proposed


def test_execucao_real_fecha_8815_e_sete_fontes():
    root = Path(__file__).resolve().parents[2]
    coverage_path = root / "data/audit/v3/source_variable_coverage.json"
    if not coverage_path.exists():
        pytest.skip("output real ainda não gerado")

    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    assert coverage["metadados"]["total_registros"] == 8815
    assert coverage["metadados"]["contagens_fontes"] == EXPECTED_LOGICAL_COUNTS
    assert len(coverage["fontes"]) == 7
    assert {
        source: details["quantidade_campos"]
        for source, details in coverage["fontes"].items()
    } == {
        "bahia_google": 20,
        "ceao": 28,
        "cnpj": 15,
        "mapeando_axe": 16,
        "osm": 20,
        "sefaz": 16,
        "terreiros_brasil": 14,
    }


def test_outputs_reais_preservam_semantica_e_status_t2b():
    root = Path(__file__).resolve().parents[2]
    matrix = list(csv.DictReader((root / "data/audit/v3/source_variable_matrix.csv").open(encoding="utf-8")))
    coverage = json.loads((root / "data/audit/v3/source_variable_coverage.json").read_text(encoding="utf-8"))
    rows = {(row["fonte"], row["campo_original"]): row for row in matrix}

    assert rows[("cnpj", "lat")]["campo_nacional"] == "geocodificacao.resultado.latitude"
    assert rows[("mapeando_axe", "nominatim_osm_id")]["campo_nacional"] == "geocodificacao.resultado.osm_id"
    assert rows[("ceao", "lat")]["campo_nacional"] == "localizacao.latitude"
    for key in (
        ("cnpj", "codigo_municipio"),
        ("cnpj", "data_inicio"),
        ("ceao", "nacao"),
        ("ceao", "nacao_original"),
        ("ceao", "nacao_categoria"),
    ):
        assert rows[key]["incluir_formato_nacional"] == "revisar"

    proposed = coverage["campos_nacionais_propostos"]
    assert "identificadores.osm_id" not in proposed
    for field in (
        "localizacao.codigo_municipio_declarado",
        "organizacao.data_inicio_cadastral_declarada",
        "identidade_religiosa.nacao_declarada",
        "identidade_religiosa.categoria_normalizada",
    ):
        assert proposed[field]["contribuicoes_pendentes"]
    assert proposed["geocodificacao.resultado.osm_id"]["contribuicoes_aprovadas"]
