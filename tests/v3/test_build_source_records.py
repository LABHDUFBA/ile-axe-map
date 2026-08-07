import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.v3 import build_source_records as builder
from scripts.v3.adapters.common import build_base_source_record


SOURCES = (
    "mapeando_axe",
    "cnpj",
    "terreiros_brasil",
    "ceao",
    "bahia_google",
    "osm",
    "sefaz",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def synthetic_build(tmp_path):
    inputs = tmp_path / "inputs"
    payloads = {
        "mapeando_axe": [{"id": "map-2"}, {"id": "map-1"}],
        "cnpj": [{"id": "cnpj-sintético"}],
        "terreiros_brasil": [{"id": "tdb-1"}],
        "bahia_v2": {
            "terreiros": [
                {"id": "ceao-1", "fonte": "ceao"},
                {"id": "google-2", "fonte": "google"},
                {"id": "osm-1", "fonte": "osm"},
                {"id": "google-1", "fonte": "google"},
                {"id": "sefaz-1", "fonte": "sefaz"},
            ]
        },
    }
    paths = {
        "mapeando_axe": inputs / "map.json",
        "cnpj": inputs / "cnpj.json",
        "terreiros_brasil": inputs / "tdb.json",
        "bahia_v2": inputs / "bahia.json",
    }
    for name, path in paths.items():
        _write_json(path, payloads[name])

    manifest = {
        "version": 3,
        "inputs": [
            {
                "name": name,
                "path": str(path.relative_to(tmp_path)),
                "sha256": _sha256(path),
                "count": (
                    len(payloads[name])
                    if name != "bahia_v2"
                    else len(payloads[name]["terreiros"])
                ),
            }
            for name, path in paths.items()
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    _write_json(manifest_path, manifest)
    schema_path = Path(__file__).resolve().parents[2] / "schemas/source-record-v3.schema.json"
    output_path = tmp_path / "out" / "source_records.jsonl"
    output_manifest_path = tmp_path / "out" / "source_records.manifest.json"
    expected_counts = {
        "mapeando_axe": 2,
        "cnpj": 1,
        "terreiros_brasil": 1,
        "ceao": 1,
        "bahia_google": 2,
        "osm": 1,
        "sefaz": 1,
    }

    def make_adapter(source):
        def adapt(records):
            return [
                build_base_source_record(
                    fonte=source,
                    id_fonte=row["id"],
                    id_fonte_sintetico=False,
                    nome_original=None,
                    dados_originais=row,
                )
                for row in records
            ]

        return adapt

    adapters = {source: make_adapter(source) for source in SOURCES}
    return {
        "root": tmp_path,
        "manifest_path": manifest_path,
        "schema_path": schema_path,
        "output_path": output_path,
        "output_manifest_path": output_manifest_path,
        "expected_counts": expected_counts,
        "adapters": adapters,
        "paths": paths,
    }


def _build(config):
    return builder.build_source_records(
        root=config["root"],
        manifest_path=config["manifest_path"],
        schema_path=config["schema_path"],
        output_path=config["output_path"],
        output_manifest_path=config["output_manifest_path"],
        expected_counts=config["expected_counts"],
        adapters=config["adapters"],
    )


def test_cli_pode_ser_executada_diretamente():
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/v3/build_source_records.py", "--help"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--output-manifest" in result.stdout


def test_cli_resolve_defaults_a_partir_do_root_informado(tmp_path):
    args = builder._parser(Path("/root/original")).parse_args(
        ["--root", str(tmp_path)]
    )

    paths = builder._resolve_cli_paths(args)

    assert paths["manifest_path"] == tmp_path / "config/source_manifests_v3.json"
    assert paths["schema_path"] == tmp_path / "schemas/source-record-v3.schema.json"
    assert paths["output_path"] == tmp_path / "data/processed/v3/source_records.jsonl"


def test_build_preserva_ordem_e_produz_jsonl_deterministico(synthetic_build):
    first_manifest = _build(synthetic_build)
    first_bytes = synthetic_build["output_path"].read_bytes()
    second_manifest = _build(synthetic_build)

    records = [
        json.loads(line)
        for line in synthetic_build["output_path"].read_text(encoding="utf-8").splitlines()
    ]
    assert [(record["fonte"], record["id_fonte"]) for record in records] == [
        ("mapeando_axe", "map-2"),
        ("mapeando_axe", "map-1"),
        ("cnpj", "cnpj-sintético"),
        ("terreiros_brasil", "tdb-1"),
        ("ceao", "ceao-1"),
        ("bahia_google", "google-2"),
        ("bahia_google", "google-1"),
        ("osm", "osm-1"),
        ("sefaz", "sefaz-1"),
    ]
    assert synthetic_build["output_path"].read_bytes() == first_bytes
    assert first_manifest["jsonl"]["sha256"] == second_manifest["jsonl"]["sha256"]
    assert first_manifest["jsonl"]["bytes"] == len(first_bytes)
    assert first_manifest["total"] == 9
    assert first_manifest["source_order"] == list(SOURCES)
    assert first_manifest["counts"] == synthetic_build["expected_counts"]
    assert set(first_manifest["input_hashes"]) == {
        "mapeando_axe",
        "cnpj",
        "terreiros_brasil",
        "bahia_v2",
    }
    assert first_bytes.endswith(b"\n")
    assert b'"dados_originais":{"id":"map-2"}' in first_bytes


def test_hash_incorreto_falha_antes_de_adaptar(synthetic_build):
    calls = []
    synthetic_build["adapters"] = {
        source: (lambda records, source=source: calls.append(source) or [])
        for source in SOURCES
    }
    synthetic_build["paths"]["cnpj"].write_bytes(b"[]")

    with pytest.raises(builder.BuildError, match="hash.*cnpj"):
        _build(synthetic_build)

    assert calls == []
    assert not synthetic_build["output_path"].exists()


def test_contagem_incorreta_falha_antes_de_adaptar(synthetic_build):
    manifest = json.loads(synthetic_build["manifest_path"].read_text(encoding="utf-8"))
    manifest["inputs"][0]["count"] += 1
    _write_json(synthetic_build["manifest_path"], manifest)
    calls = []
    synthetic_build["adapters"] = {
        source: (lambda records, source=source: calls.append(source) or [])
        for source in SOURCES
    }

    with pytest.raises(builder.BuildError, match="contagem.*mapeando_axe"):
        _build(synthetic_build)

    assert calls == []


def test_rejeita_source_record_key_duplicada(synthetic_build):
    original = synthetic_build["adapters"]["bahia_google"]

    def duplicate(records):
        outputs = original(records)
        outputs[1]["source_record_key"] = outputs[0]["source_record_key"]
        return outputs

    synthetic_build["adapters"]["bahia_google"] = duplicate

    with pytest.raises(builder.BuildError, match="source_record_key duplicada"):
        _build(synthetic_build)

    assert not synthetic_build["output_path"].exists()
    assert not synthetic_build["output_manifest_path"].exists()


def test_rejeita_saida_invalida_pelo_schema_com_formats(synthetic_build):
    original = synthetic_build["adapters"]["osm"]

    def invalid(records):
        outputs = original(records)
        outputs[0]["data_coleta"] = "2025-02-30"
        return outputs

    synthetic_build["adapters"]["osm"] = invalid

    with pytest.raises(builder.BuildError, match="schema.*osm"):
        _build(synthetic_build)


def test_fonte_da_saida_deve_corresponder_ao_bloco(synthetic_build):
    original = synthetic_build["adapters"]["sefaz"]

    def wrong_source(records):
        outputs = original(records)
        outputs[0]["fonte"] = "osm"
        return outputs

    synthetic_build["adapters"]["sefaz"] = wrong_source

    with pytest.raises(builder.BuildError, match="fonte.*bloco sefaz"):
        _build(synthetic_build)


def test_falha_na_publicacao_do_par_restaura_artefatos_anteriores(
    synthetic_build, monkeypatch
):
    output = synthetic_build["output_path"]
    output_manifest = synthetic_build["output_manifest_path"]
    output.parent.mkdir(parents=True)
    output.write_bytes(b"JSONL ANTERIOR\n")
    output_manifest.write_bytes(b'{"manifesto":"anterior"}\n')
    previous_output = output.read_bytes()
    previous_manifest = output_manifest.read_bytes()
    real_replace = os.replace
    failed = False

    def fail_second_publication(source, destination):
        nonlocal failed
        source_path = Path(source)
        destination_path = Path(destination)
        if (
            not failed
            and destination_path == output_manifest
            and ".tmp-" in source_path.name
        ):
            failed = True
            raise OSError("falha sintética na segunda publicação")
        return real_replace(source, destination)

    monkeypatch.setattr(builder.os, "replace", fail_second_publication)

    with pytest.raises(OSError, match="falha sintética"):
        _build(synthetic_build)

    assert output.read_bytes() == previous_output
    assert output_manifest.read_bytes() == previous_manifest
    assert not list(output.parent.glob(".*.tmp-*"))
    assert not list(output.parent.glob(".*.bak-*"))
