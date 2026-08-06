#!/usr/bin/env python3
import argparse
import csv
import json
import sys
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

    validate_manifest(root, manifest)
    source_ledger = next(
        root / item["path"]
        for item in manifest["inputs"]
        if item["name"] == "exclusoes_curadas"
    )
    normalize_curated_ledger(source_ledger, ledger_path)
    report = build_report(root, manifest, ledger_path)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"auditoria gerada: {report_path}")
    print(f"ledger normalizado: {ledger_path}")


if __name__ == "__main__":
    main()
