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
    assert list(normalized[0]) == fieldnames + ["stable_key", "identity_synthetic"]
    assert b"\r\n" not in output.read_bytes()


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
    manifest["inputs"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash"):
        validate_manifest(tmp_path, manifest)


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
    identities = {row["stable_key"]: row for row in ledger}
    assert len(identities) == 146
    assert identities["cnpj:05419205000120"]["identity_synthetic"] == "false"
    assert identities["cnpj:04858642000187"]["identity_synthetic"] == "false"
    assert identities["cnpj:10344860000104"]["identity_synthetic"] == "false"
    assert sum(row["identity_synthetic"] == "true" for row in ledger) == 143
    assert report["hashes"]["exclusoes_curadas_v3"] == sha256_file(ledger_path)
