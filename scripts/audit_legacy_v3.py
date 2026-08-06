#!/usr/bin/env python3
import argparse
import csv
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audit.legacy_ledgers import (  # noqa: E402
    build_stable_identity,
    normalize_curated_ledger,
    sha256_file,
    summarize_bahia,
    summarize_national,
    validate_manifest,
)


SEMANTICA = [
    "exclusao_curada",
    "remocao_heuristica_legada",
    "ambiguo_pendente",
    "dedup_legado_recuperado",
    "baseline_atual",
]


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _input_paths(root, manifest):
    return {
        item["name"]: root / item["path"]
        for item in manifest["inputs"]
    }


def build_report(root, manifest, ledger_path):
    paths = _input_paths(root, manifest)
    mapeando = _read_json(paths["mapeando_axe"])
    cnpj = _read_json(paths["cnpj"])
    terreiros_brasil = _read_json(paths["terreiros_brasil"])
    dedup = _read_json(paths["dedup_nacional"])
    historical = _read_json(paths["snapshot_bahia_pre_96493ef"])["terreiros"]
    removals = _read_json(paths["remocoes_bahia"])["removidos"]
    suspects = _read_json(paths["suspeitos_bahia"])
    current = _read_json(paths["bahia_v2"])["terreiros"]

    with paths["exclusoes_curadas"].open(encoding="utf-8", newline="") as handle:
        exclusions = list(csv.DictReader(handle))

    national = summarize_national(mapeando, cnpj, terreiros_brasil, dedup)
    bahia = summarize_bahia(
        historical,
        removals,
        suspects["google_false_positives"],
        suspects["google_ambiguous"],
        exclusions,
        current,
    )
    baseline_count = next(
        item["count"] for item in manifest["inputs"] if item["name"] == "baseline_v2"
    )
    input_hashes = validate_manifest(root, manifest)

    return {
        "version": 3,
        "total_bruto": national["brutos"] + len(current),
        "deduplicacao_nacional": national,
        "bahia": bahia,
        "baseline_atual": {"contagem": baseline_count},
        "exclusoes_curadas": {
            "contagem": len(exclusions),
            "identidades_sinteticas": sum(
                build_stable_identity(row)["identity_synthetic"] for row in exclusions
            ),
        },
        "semantica": SEMANTICA,
        "hashes": {
            "inputs": input_hashes,
            "exclusoes_curadas_v3": sha256_file(ledger_path),
        },
    }


def _temporary_path(destination, label="stage"):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.{label}.",
        suffix=".tmp",
    )
    os.close(descriptor)
    path = Path(name)
    path.unlink()
    return path


def _write_report(path, report):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _publish_outputs(outputs, replace=os.replace):
    outputs = [(Path(staged), Path(destination)) for staged, destination in outputs]
    backups = {}
    installed = set()
    try:
        for _, destination in outputs:
            if destination.exists():
                backup = _temporary_path(destination, label="backup")
                replace(destination, backup)
                backups[destination] = backup

        for staged, destination in outputs:
            replace(staged, destination)
            installed.add(destination)
    except Exception:
        for destination in installed:
            destination.unlink(missing_ok=True)
        for destination, backup in reversed(list(backups.items())):
            destination.unlink(missing_ok=True)
            replace(backup, destination)
        raise
    finally:
        for backup in backups.values():
            backup.unlink(missing_ok=True)


def generate_audit_outputs(
    root, manifest, report_path, ledger_path, before_publish=None
):
    root = Path(root).resolve()
    report_path = Path(report_path)
    ledger_path = Path(ledger_path)
    validate_manifest(root, manifest)
    source_ledger = next(
        root / item["path"]
        for item in manifest["inputs"]
        if item["name"] == "exclusoes_curadas"
    )
    staged_ledger = _temporary_path(ledger_path)
    staged_report = _temporary_path(report_path)
    try:
        normalize_curated_ledger(source_ledger, staged_ledger)
        report = build_report(root, manifest, staged_ledger)
        _write_report(staged_report, report)
        if before_publish is not None:
            before_publish()
        _publish_outputs(
            [(staged_ledger, ledger_path), (staged_report, report_path)]
        )
        return report
    finally:
        staged_ledger.unlink(missing_ok=True)
        staged_report.unlink(missing_ok=True)


def parse_args():
    parser = argparse.ArgumentParser(description="Audita ledgers legados da unificação v3")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--ledger", type=Path)
    return parser.parse_args()


def main():
    args = parse_args()
    root = args.root.resolve()
    report_path = args.report or root / "data/audit/v3/legacy_audit.json"
    ledger_path = args.ledger or root / "data/audit/v3/exclusoes_curadas_v3.csv"
    manifest = _read_json(root / "config/source_manifests_v3.json")

    generate_audit_outputs(root, manifest, report_path, ledger_path)
    print(f"auditoria gerada: {report_path}")
    print(f"ledger normalizado: {ledger_path}")


if __name__ == "__main__":
    main()
