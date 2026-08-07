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
