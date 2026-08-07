"""Gera os registros intermediários v3 de forma validada e atômica."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import jsonschema

from scripts.v3.adapters.ceao import adapt_records as adapt_ceao
from scripts.v3.adapters.cnpj import adapt_records as adapt_cnpj
from scripts.v3.adapters.google_bahia import adapt_records as adapt_bahia_google
from scripts.v3.adapters.mapeando_axe import adapt_records as adapt_mapeando_axe
from scripts.v3.adapters.osm import adapt_records as adapt_osm
from scripts.v3.adapters.sefaz import adapt_records as adapt_sefaz
from scripts.v3.adapters.terreiros_brasil import adapt_records as adapt_terreiros_brasil


SOURCE_ORDER = (
    "mapeando_axe",
    "cnpj",
    "terreiros_brasil",
    "ceao",
    "bahia_google",
    "osm",
    "sefaz",
)
EXPECTED_COUNTS = {
    "mapeando_axe": 3923,
    "cnpj": 2673,
    "terreiros_brasil": 260,
    "ceao": 1155,
    "bahia_google": 550,
    "osm": 20,
    "sefaz": 234,
}
REQUIRED_INPUTS = ("mapeando_axe", "cnpj", "terreiros_brasil", "bahia_v2")
BAHIA_SOURCE_NAMES = {
    "ceao": "ceao",
    "bahia_google": "google",
    "osm": "osm",
    "sefaz": "sefaz",
}
DEFAULT_ADAPTERS = {
    "mapeando_axe": adapt_mapeando_axe,
    "cnpj": adapt_cnpj,
    "terreiros_brasil": adapt_terreiros_brasil,
    "ceao": adapt_ceao,
    "bahia_google": adapt_bahia_google,
    "osm": adapt_osm,
    "sefaz": adapt_sefaz,
}


class BuildError(RuntimeError):
    """Falha de integridade ou contrato na geração."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_and_validate_inputs(
    root: Path, manifest_path: Path, expected_counts: Mapping[str, int]
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = {entry.get("name"): entry for entry in manifest.get("inputs", [])}
    missing = [name for name in REQUIRED_INPUTS if name not in entries]
    if missing:
        raise BuildError(f"inputs ausentes no manifesto: {', '.join(missing)}")

    loaded: dict[str, Any] = {}
    input_hashes: dict[str, dict[str, Any]] = {}
    for name in REQUIRED_INPUTS:
        entry = entries[name]
        path = root / entry["path"]
        actual_hash = _sha256(path)
        if actual_hash != entry.get("sha256"):
            raise BuildError(f"hash inválido para input {name}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if name == "bahia_v2":
            if not isinstance(payload, dict) or not isinstance(payload.get("terreiros"), list):
                raise BuildError("estrutura inválida para input bahia_v2")
            actual_count = len(payload["terreiros"])
        else:
            if not isinstance(payload, list):
                raise BuildError(f"estrutura inválida para input {name}")
            actual_count = len(payload)
        if actual_count != entry.get("count"):
            raise BuildError(f"contagem inválida para input {name}")
        loaded[name] = payload
        input_hashes[name] = {
            "path": entry["path"],
            "sha256": actual_hash,
            "count": actual_count,
        }

    bahia_rows = loaded["bahia_v2"]["terreiros"]
    blocks = {
        "mapeando_axe": loaded["mapeando_axe"],
        "cnpj": loaded["cnpj"],
        "terreiros_brasil": loaded["terreiros_brasil"],
        **{
            output_source: [
                row
                for row in bahia_rows
                if isinstance(row, dict) and row.get("fonte") == input_source
            ]
            for output_source, input_source in BAHIA_SOURCE_NAMES.items()
        },
    }
    actual_counts = {source: len(blocks[source]) for source in SOURCE_ORDER}
    if actual_counts != dict(expected_counts):
        differences = ", ".join(
            f"{source}={actual_counts[source]} (esperado {expected_counts.get(source)})"
            for source in SOURCE_ORDER
            if actual_counts[source] != expected_counts.get(source)
        )
        raise BuildError(f"contagens por fonte inválidas: {differences}")
    return blocks, input_hashes


def _serialize_records(records: Sequence[dict[str, Any]]) -> bytes:
    lines = [
        json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        for record in records
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _write_synced(path: Path, content: bytes) -> None:
    with path.open("xb") as target:
        target.write(content)
        target.flush()
        os.fsync(target.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_pair_atomically(
    output_path: Path,
    output_content: bytes,
    manifest_path: Path,
    manifest_content: bytes,
) -> None:
    if output_path.parent != manifest_path.parent:
        raise BuildError("JSONL e manifesto devem estar no mesmo diretório")
    directory = output_path.parent
    directory.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    temporary = {
        output_path: directory / f".{output_path.name}.tmp-{token}",
        manifest_path: directory / f".{manifest_path.name}.tmp-{token}",
    }
    backups = {
        output_path: directory / f".{output_path.name}.bak-{token}",
        manifest_path: directory / f".{manifest_path.name}.bak-{token}",
    }
    backed_up: set[Path] = set()
    published: set[Path] = set()
    try:
        _write_synced(temporary[output_path], output_content)
        _write_synced(temporary[manifest_path], manifest_content)
        _fsync_directory(directory)
        for destination in (output_path, manifest_path):
            if destination.exists():
                os.replace(destination, backups[destination])
                backed_up.add(destination)
        _fsync_directory(directory)
        for destination in (output_path, manifest_path):
            os.replace(temporary[destination], destination)
            published.add(destination)
        _fsync_directory(directory)
    except BaseException:
        for destination in published:
            destination.unlink(missing_ok=True)
        for destination in (output_path, manifest_path):
            if destination in backed_up and backups[destination].exists():
                os.replace(backups[destination], destination)
        _fsync_directory(directory)
        raise
    finally:
        for path in (*temporary.values(), *backups.values()):
            path.unlink(missing_ok=True)
        _fsync_directory(directory)


def build_source_records(
    *,
    root: Path,
    manifest_path: Path,
    schema_path: Path,
    output_path: Path,
    output_manifest_path: Path,
    expected_counts: Mapping[str, int] = EXPECTED_COUNTS,
    adapters: Mapping[
        str, Callable[[Sequence[dict[str, Any]]], list[dict[str, Any]]]
    ] = DEFAULT_ADAPTERS,
) -> dict[str, Any]:
    """Valida inputs, adapta cada bloco e publica o JSONL e seu manifesto."""
    root = root.resolve()
    manifest_path = manifest_path.resolve()
    schema_path = schema_path.resolve()
    output_path = output_path.resolve()
    output_manifest_path = output_manifest_path.resolve()
    if tuple(expected_counts) != SOURCE_ORDER:
        raise BuildError("expected_counts deve seguir a ordem fixa das fontes")
    if set(adapters) != set(SOURCE_ORDER):
        raise BuildError("conjunto de adaptadores inválido")

    blocks, input_hashes = _load_and_validate_inputs(
        root, manifest_path, expected_counts
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )

    records: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    counts: dict[str, int] = {}
    for source in SOURCE_ORDER:
        outputs = adapters[source](blocks[source])
        if len(outputs) != len(blocks[source]):
            raise BuildError(f"cardinalidade inválida no bloco {source}")
        counts[source] = len(outputs)
        for index, record in enumerate(outputs):
            if record.get("fonte") != source:
                raise BuildError(
                    f"fonte da saída não corresponde ao bloco {source}, índice {index}"
                )
            errors = list(validator.iter_errors(record))
            if errors:
                raise BuildError(
                    f"schema inválido no bloco {source}, índice {index}: "
                    f"{errors[0].json_path}"
                )
            key = record["source_record_key"]
            if key in seen_keys:
                raise BuildError(f"source_record_key duplicada no bloco {source}")
            seen_keys.add(key)
            records.append(record)

    if counts != dict(expected_counts) or len(records) != sum(expected_counts.values()):
        raise BuildError("contagem final inválida")

    jsonl = _serialize_records(records)
    jsonl_hash = hashlib.sha256(jsonl).hexdigest()
    aggregate_manifest = {
        "version": 3,
        "schema": schema.get("$id", str(schema_path)),
        "source_order": list(SOURCE_ORDER),
        "total": len(records),
        "counts": counts,
        "jsonl": {
            "path": os.path.relpath(output_path, root),
            "sha256": jsonl_hash,
            "bytes": len(jsonl),
        },
        "input_hashes": input_hashes,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    manifest_bytes = (
        json.dumps(
            aggregate_manifest,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    _publish_pair_atomically(
        output_path, jsonl, output_manifest_path, manifest_bytes
    )
    return aggregate_manifest


def _parser(root: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument("--input-manifest", type=Path)
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--output-manifest", type=Path)
    return parser


def _resolve_cli_paths(args: argparse.Namespace) -> dict[str, Path]:
    root = args.root.resolve()

    def resolve(value: Path | None, default: str) -> Path:
        if value is None:
            return root / default
        return value if value.is_absolute() else root / value

    return {
        "root": root,
        "manifest_path": resolve(
            args.input_manifest, "config/source_manifests_v3.json"
        ),
        "schema_path": resolve(args.schema, "schemas/source-record-v3.schema.json"),
        "output_path": resolve(
            args.output, "data/processed/v3/source_records.jsonl"
        ),
        "output_manifest_path": resolve(
            args.output_manifest,
            "data/processed/v3/source_records.manifest.json",
        ),
    }


def main() -> int:
    default_root = Path(__file__).resolve().parents[2]
    args = _parser(default_root).parse_args()
    paths = _resolve_cli_paths(args)
    result = build_source_records(
        root=paths["root"],
        manifest_path=paths["manifest_path"],
        schema_path=paths["schema_path"],
        output_path=paths["output_path"],
        output_manifest_path=paths["output_manifest_path"],
    )
    print(f"source-records gerados: {result['total']}")
    print(f"contagens: {json.dumps(result['counts'], sort_keys=True)}")
    print(f"sha256: {result['jsonl']['sha256']}")
    print(f"bytes: {result['jsonl']['bytes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
