import csv
import json
from pathlib import Path
import subprocess
import sys

import pytest

from src.audit.legacy_ledgers import (
    build_stable_identity,
    normalize_curated_ledger,
    sha256_file,
    summarize_bahia,
    summarize_national,
    validate_manifest,
)


ROOT = Path(__file__).resolve().parents[1]


def test_cnpj_e_a_chave_forte_da_exclusao():
    row = {
        "nome": "ASSEMBLEIA DE DEUS",
        "fonte": "CNPJ/Receita",
        "latitude": "-4.4506556",
        "longitude": "-49.1123534",
        "motivo": "CNPJ 05.419.205/0001-20; organização evangélica",
    }

    identity = build_stable_identity(row)

    assert identity == {
        "stable_key": "cnpj:05419205000120",
        "identity_synthetic": False,
    }


def test_cnpj_invalido_no_motivo_falha_em_vez_de_virar_identidade_forte():
    row = {
        "nome": "Registro inválido",
        "fonte": "CNPJ/Receita",
        "latitude": "-4.0",
        "longitude": "-49.0",
        "motivo": "CNPJ 11.111.111/1111-11",
    }

    with pytest.raises(ValueError, match="CNPJ inválido.*11.111.111/1111-11"):
        build_stable_identity(row)


def test_fallback_sintetico_e_deterministico_sem_id_nativo():
    row = {
        "nome": "  Ilê   Axé Àṣẹ  ",
        "fonte": "Google Places",
        "latitude": "-12.12345649",
        "longitude": "-38.12345651",
        "motivo": "sem identificador nativo",
    }

    first = build_stable_identity(row)
    second = build_stable_identity(dict(row))

    assert first == second
    assert first["stable_key"].startswith("synthetic:")
    assert first["identity_synthetic"] is True


def test_ids_cnpj_fortes_na_mesma_coordenada_nao_colidem():
    common = {
        "nome": "Nome igual",
        "fonte": "CNPJ/Receita",
        "latitude": "-1.0",
        "longitude": "-2.0",
    }

    first = build_stable_identity({**common, "motivo": "CNPJ 05.419.205/0001-20"})
    second = build_stable_identity({**common, "motivo": "CNPJ 04.858.642/0001-87"})

    assert first["stable_key"] != second["stable_key"]


def test_normalizacao_preserva_linhas_e_nao_usa_fuzzy(tmp_path):
    source = tmp_path / "ledger.csv"
    output = tmp_path / "ledger_v3.csv"
    fieldnames = [
        "nome",
        "municipio",
        "endereco",
        "fonte",
        "latitude",
        "longitude",
        "motivo",
        "status",
    ]
    rows = [
        {
            "nome": "Casa de Axé",
            "municipio": "Salvador",
            "endereco": "",
            "fonte": "Google Places",
            "latitude": "-12.9",
            "longitude": "-38.5",
            "motivo": "revisão humana",
            "status": "excluída",
        },
        {
            "nome": "Casa de Axe",
            "municipio": "Salvador",
            "endereco": "",
            "fonte": "Google Places",
            "latitude": "-12.900001",
            "longitude": "-38.500001",
            "motivo": "revisão humana",
            "status": "excluída",
        },
    ]
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    result = normalize_curated_ledger(source, output)

    with output.open(encoding="utf-8", newline="") as handle:
        normalized = list(csv.DictReader(handle))
    assert result["row_count"] == 2
    assert len(normalized) == 2
    assert normalized[0]["stable_key"] != normalized[1]["stable_key"]
    assert all(row["identity_synthetic"] == "true" for row in normalized)
    assert list(normalized[0]) == ["stable_key", "identity_synthetic", "status"]
    assert b"\r\n" not in output.read_bytes()


def test_normalizacao_rejeita_colisao_de_chave_com_linhas_diagnosticadas(tmp_path):
    source = tmp_path / "ledger.csv"
    output = tmp_path / "ledger_v3.csv"
    rows = [
        {
            "nome": "Ilê Axé",
            "fonte": "Google Places",
            "latitude": "-12.9",
            "longitude": "-38.5",
            "motivo": "revisão 1",
            "status": "excluída",
        },
        {
            "nome": "  Ile Axe ",
            "fonte": "google places",
            "latitude": "-12.9000001",
            "longitude": "-38.5000001",
            "motivo": "revisão 2",
            "status": "excluída",
        },
    ]
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    stable_key = build_stable_identity(rows[0])["stable_key"]
    with pytest.raises(
        ValueError, match=rf"{stable_key}.*linhas 2 e 3"
    ):
        normalize_curated_ledger(source, output)

    assert not output.exists()


def test_resumo_nacional_fecha_equacoes_contabeis():
    mapeando = [
        {"nominatim_lat": -12.0, "nominatim_lng": -38.0},
        {"nominatim_lat": None, "nominatim_lng": None},
    ]
    cnpj = [{"lat": -13.0, "lng": -39.0}]
    terreiros_brasil = [
        {"lat": -14.0, "lng": -40.0},
        {"lat": -5.7841695, "lng": -35.1999708},
    ]
    dedup = {
        "total_bruto": 3,
        "mantidos": 2,
        "duplicatas": 1,
        "duplicates": [
            {
                "removed_source": "mapeando_axe",
                "kept_source": "receita_federal_cnpj",
            }
        ],
    }

    summary = summarize_national(mapeando, cnpj, terreiros_brasil, dedup)

    assert summary["brutos"] == 5
    assert summary["admitidos"] == 3
    assert summary["mantidos"] + summary["removidos"] == summary["admitidos"]
    assert summary["removidos_por_fonte"] == {
        "cnpj": 0,
        "mapeando_axe": 1,
        "terreirosdobrasil": 0,
    }
    assert summary["pares_mapeando"] == {
        "mapeando_axe->mapeando_axe": 0,
        "mapeando_axe->cnpj": 1,
    }
    assert summary["limiar_efetivo_legado"] == 0.5


def _national_inputs():
    return (
        [{"nominatim_lat": -12.0, "nominatim_lng": -38.0}],
        [{"lat": -13.0, "lng": -39.0}],
        [{"lat": -14.0, "lng": -40.0}],
        {
            "total_bruto": 3,
            "mantidos": 2,
            "duplicatas": 1,
            "duplicates": [
                {
                    "removed_source": "mapeando_axe",
                    "kept_source": "receita_federal_cnpj",
                }
            ],
        },
    )


def test_resumo_nacional_rejeita_contagem_de_duplicatas_divergente():
    mapeando, cnpj, terreiros, dedup = _national_inputs()
    dedup["duplicatas"] = 2

    with pytest.raises(ValueError, match="duplicatas.*esperado 2.*encontrado 1"):
        summarize_national(mapeando, cnpj, terreiros, dedup)


@pytest.mark.parametrize(
    ("field", "value"),
    [("mantidos", 1), ("total_bruto", 4)],
)
def test_resumo_nacional_rejeita_equacao_contabil_divergente(field, value):
    mapeando, cnpj, terreiros, dedup = _national_inputs()
    dedup[field] = value

    with pytest.raises(ValueError, match="equação contábil"):
        summarize_national(mapeando, cnpj, terreiros, dedup)


def test_resumo_nacional_rejeita_fonte_desconhecida_no_breakdown():
    mapeando, cnpj, terreiros, dedup = _national_inputs()
    dedup["duplicates"][0]["removed_source"] = "fonte_surpresa"

    with pytest.raises(ValueError, match="fonte desconhecida.*fonte_surpresa"):
        summarize_national(mapeando, cnpj, terreiros, dedup)


def test_resumo_bahia_reconcilia_apenas_por_chaves_exatas():
    historical = [
        {"fonte": "google", "nome": "Removido", "lat": -12.0, "lng": -38.0}
    ]
    removals = [{"fonte": "google", "nome": "Removido"}]
    false_positives = [
        {"fonte": "google", "nome": "Removido", "lat": -12.0, "lng": -38.0}
    ]
    ambiguous = [
        {"fonte": "google", "nome": "Removido", "lat": -12.0, "lng": -38.0},
        {"fonte": "google", "nome": "Curado", "lat": -13.0, "lng": -39.0},
        {"fonte": "google", "nome": "Pendente", "lat": -14.0, "lng": -40.0},
        {"fonte": "google", "nome": "Fora", "lat": -23.0, "lng": -46.0},
    ]
    exclusions = [
        {
            "fonte": "Google Places",
            "nome": "Curado",
            "latitude": "-13.0",
            "longitude": "-39.0",
        }
    ]
    current = [
        {"fonte": "google", "nome": "Pendente", "lat": -14.0, "lng": -40.0}
    ]

    summary = summarize_bahia(
        historical, removals, false_positives, ambiguous, exclusions, current
    )

    assert summary == {
        "remocoes_heuristicas": 1,
        "intersecao_remocoes_exclusoes": 0,
        "falsos_positivos_nas_remocoes": 1,
        "ambiguos": {
            "total": 4,
            "nas_remocoes": 1,
            "fora_bbox": 1,
            "nas_exclusoes_curadas": 1,
            "ambiguos_pendentes_v2": 1,
        },
    }


def test_manifest_valida_hash_contagem_e_metadados_obrigatorios(tmp_path):
    data_path = tmp_path / "input.json"
    data_path.write_text(json.dumps([{"id": "a"}, {"id": "b"}]), encoding="utf-8")
    manifest = {
        "inputs": [
            {
                "name": "input",
                "path": "input.json",
                "sha256": sha256_file(data_path),
                "count": 2,
                "id_field": "id",
                "sensitivity": "interno",
                "kind": "input_bruto",
            }
        ]
    }

    validated = validate_manifest(tmp_path, manifest)

    assert validated == {"input": sha256_file(data_path)}
    actual_hash = manifest["inputs"][0]["sha256"]
    manifest["inputs"][0]["sha256"] = "0" * 64
    with pytest.raises(
        ValueError,
        match=rf"hash divergente.*input.*input.json.*{'0' * 64}.*{actual_hash}",
    ):
        validate_manifest(tmp_path, manifest)


def test_manifest_rejeita_contagem_divergente_com_diagnostico(tmp_path):
    data_path = tmp_path / "input.json"
    data_path.write_text(json.dumps([{"id": "a"}]), encoding="utf-8")
    item = {
        "name": "input",
        "path": "input.json",
        "sha256": sha256_file(data_path),
        "count": 2,
        "id_field": "id",
        "sensitivity": "interno",
        "kind": "input_bruto",
    }

    with pytest.raises(
        ValueError, match="contagem divergente.*input.*input.json.*esperado 2.*encontrado 1"
    ):
        validate_manifest(tmp_path, {"inputs": [item]})


def test_manifest_rejeita_metadata_ausente_com_diagnostico(tmp_path):
    item = {"name": "input", "path": "input.json"}

    with pytest.raises(
        ValueError, match="metadados obrigatórios.*input.*input.json.*count.*sha256"
    ):
        validate_manifest(tmp_path, {"inputs": [item]})


def test_falha_antes_da_publicacao_preserva_os_dois_outputs(tmp_path):
    from scripts.audit_legacy_v3 import generate_audit_outputs

    report_path = tmp_path / "legacy_audit.json"
    ledger_path = tmp_path / "exclusoes_curadas_v3.csv"
    report_path.write_bytes(b"relatorio antigo\n")
    ledger_path.write_bytes(b"ledger antigo\n")
    manifest = json.loads(
        (ROOT / "config/source_manifests_v3.json").read_text(encoding="utf-8")
    )

    def fail_before_publish():
        raise RuntimeError("falha controlada")

    with pytest.raises(RuntimeError, match="falha controlada"):
        generate_audit_outputs(
            ROOT,
            manifest,
            report_path,
            ledger_path,
            before_publish=fail_before_publish,
        )

    assert report_path.read_bytes() == b"relatorio antigo\n"
    assert ledger_path.read_bytes() == b"ledger antigo\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "exclusoes_curadas_v3.csv",
        "legacy_audit.json",
    ]


def test_falha_na_segunda_substituicao_restabelece_os_dois_outputs(tmp_path):
    import os

    from scripts.audit_legacy_v3 import _publish_outputs

    ledger_path = tmp_path / "ledger.csv"
    report_path = tmp_path / "report.json"
    staged_ledger = tmp_path / "ledger.stage"
    staged_report = tmp_path / "report.stage"
    ledger_path.write_text("ledger antigo", encoding="utf-8")
    report_path.write_text("relatório antigo", encoding="utf-8")
    staged_ledger.write_text("ledger novo", encoding="utf-8")
    staged_report.write_text("relatório novo", encoding="utf-8")
    publication_replacements = 0

    def fail_second_publication(source, destination):
        nonlocal publication_replacements
        if Path(source) in {staged_ledger, staged_report}:
            publication_replacements += 1
            if publication_replacements == 2:
                raise OSError("falha controlada na substituição")
        os.replace(source, destination)

    with pytest.raises(OSError, match="falha controlada"):
        _publish_outputs(
            [(staged_ledger, ledger_path), (staged_report, report_path)],
            replace=fail_second_publication,
        )

    assert ledger_path.read_text(encoding="utf-8") == "ledger antigo"
    assert report_path.read_text(encoding="utf-8") == "relatório antigo"
    assert not any("backup" in path.name for path in tmp_path.iterdir())


def test_cli_gera_outputs_reais_em_destino_configuravel(tmp_path):
    report_path = tmp_path / "legacy_audit.json"
    ledger_path = tmp_path / "exclusoes_curadas_v3.csv"

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audit_legacy_v3.py"),
            "--root",
            str(ROOT),
            "--report",
            str(report_path),
            "--ledger",
            str(ledger_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(report_path.read_text(encoding="utf-8"))["total_bruto"] == 8815
    with ledger_path.open(encoding="utf-8", newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 146


def test_outputs_reais_sao_agregados_e_preservam_baseline():
    manifest_path = ROOT / "config/source_manifests_v3.json"
    report_path = ROOT / "data/audit/v3/legacy_audit.json"
    ledger_path = ROOT / "data/audit/v3/exclusoes_curadas_v3.csv"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    with ledger_path.open(encoding="utf-8", newline="") as handle:
        ledger = list(csv.DictReader(handle))

    assert {item["kind"] for item in manifest["inputs"]} >= {
        "input_bruto",
        "agregado_bahia",
        "baseline_publicado",
    }
    assert all(not Path(item["path"]).is_absolute() for item in manifest["inputs"])
    assert all(len(item["sha256"]) == 64 for item in manifest["inputs"])
    mapeando = next(item for item in manifest["inputs"] if item["name"] == "mapeando_axe")
    assert mapeando["coordinate_authority"] == "pending"
    bahia = next(item for item in manifest["inputs"] if item["name"] == "bahia_v2")
    assert bahia["id_policy_by_source"]["google"] == "synthetic_fallback"
    assert bahia["id_policy_by_source"]["osm"] == "synthetic_fallback"
    exclusions = next(
        item for item in manifest["inputs"] if item["name"] == "exclusoes_curadas"
    )
    assert exclusions["sensitivity"] == "publico_curado_legado"
    assert "organizacionais" in exclusions["privacy_note"]
    assert "minimizado" in exclusions["privacy_note"]

    assert report["total_bruto"] == 8815
    assert report["deduplicacao_nacional"]["admitidos"] == 5492
    assert report["deduplicacao_nacional"]["mantidos"] == 4335
    assert report["deduplicacao_nacional"]["removidos"] == 1157
    assert report["bahia"]["remocoes_heuristicas"] == 499
    assert report["bahia"]["ambiguos"]["ambiguos_pendentes_v2"] == 27
    assert report["baseline_atual"]["contagem"] == 5757
    assert report["exclusoes_curadas"]["contagem"] == 146
    assert report["semantica"] == [
        "exclusao_curada",
        "remocao_heuristica_legada",
        "ambiguo_pendente",
        "dedup_legado_recuperado",
        "baseline_atual",
    ]
    serialized = json.dumps(report, ensure_ascii=False).casefold()
    assert all(term not in serialized for term in ("telefone", "endereco", "payload", "contato"))

    assert len(ledger) == 146
    assert list(ledger[0]) == ["stable_key", "identity_synthetic", "status"]
    assert not ({"nome", "municipio", "endereco", "fonte", "latitude", "longitude", "motivo"} & set(ledger[0]))
    identities = {row["stable_key"]: row for row in ledger}
    assert len(identities) == 146
    assert identities["cnpj:05419205000120"]["identity_synthetic"] == "false"
    assert identities["cnpj:04858642000187"]["identity_synthetic"] == "false"
    assert identities["cnpj:10344860000104"]["identity_synthetic"] == "false"
    assert sum(row["identity_synthetic"] == "true" for row in ledger) == 143
    assert report["hashes"]["exclusoes_curadas_v3"] == sha256_file(ledger_path)
