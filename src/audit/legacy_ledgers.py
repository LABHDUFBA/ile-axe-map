import csv
import hashlib
import json
import os
import re
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path


def normalize_text(value):
    ascii_value = unicodedata.normalize("NFKD", value or "")
    ascii_value = ascii_value.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_value.casefold().split())


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record_count(path):
    if path.suffix == ".csv":
        with path.open(encoding="utf-8", newline="") as handle:
            return sum(1 for _ in csv.DictReader(handle))
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return len(data)
    if isinstance(data.get("google_false_positives"), list) and isinstance(
        data.get("google_ambiguous"), list
    ):
        return len(data["google_false_positives"]) + len(data["google_ambiguous"])
    for key in ("features", "terreiros", "removidos", "duplicates"):
        if isinstance(data.get(key), list):
            return len(data[key])
    raise ValueError(f"contagem não suportada para {path}")


def validate_manifest(root, manifest):
    root = Path(root).resolve()
    required = {"name", "path", "sha256", "count", "id_field", "sensitivity", "kind"}
    validated = {}
    for item in manifest["inputs"]:
        missing = sorted(required - set(item))
        if missing:
            name = item.get("name", "<sem name>")
            path_value = item.get("path", "<sem path>")
            raise ValueError(
                "manifest sem metadados obrigatórios: "
                f"name={name}, path={path_value}, ausentes={','.join(missing)}"
            )
        relative = Path(item["path"])
        if relative.is_absolute():
            raise ValueError("manifest exige path local relativo")
        path = (root / relative).resolve()
        if root not in path.parents:
            raise ValueError("path do manifest escapa da raiz")
        actual_hash = sha256_file(path)
        if actual_hash != item["sha256"]:
            raise ValueError(
                "hash divergente: "
                f"name={item['name']}, path={item['path']}, "
                f"esperado={item['sha256']}, encontrado={actual_hash}"
            )
        actual_count = _record_count(path)
        if actual_count != item["count"]:
            raise ValueError(
                "contagem divergente: "
                f"name={item['name']}, path={item['path']}, "
                f"esperado {item['count']}, encontrado {actual_count}"
            )
        validated[item["name"]] = actual_hash
    return validated


def _valid_cnpj(digits):
    if len(digits) != 14 or len(set(digits)) == 1:
        return False

    def check_digit(prefix, weights):
        total = sum(int(digit) * weight for digit, weight in zip(prefix, weights))
        remainder = total % 11
        return "0" if remainder < 2 else str(11 - remainder)

    first = check_digit(digits[:12], (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
    second = check_digit(
        digits[:12] + first, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    )
    return digits[-2:] == first + second


def build_stable_identity(row):
    motivo = row.get("motivo", "")
    cnpjs = re.findall(
        r"(?<!\d)(?:\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14})(?!\d)",
        motivo,
    )
    if cnpjs:
        raw_cnpj = cnpjs[0]
        digits = re.sub(r"\D", "", raw_cnpj)
        if not _valid_cnpj(digits):
            raise ValueError(f"CNPJ inválido na curadoria: {raw_cnpj}")
        return {
            "stable_key": f"cnpj:{digits}",
            "identity_synthetic": False,
        }

    malformed = re.search(
        r"\bCNPJ\b\s*[:#-]?\s*([0-9][0-9.\-/ ]*)",
        motivo,
        flags=re.IGNORECASE,
    )
    if malformed:
        raw_cnpj = malformed.group(1).strip()
        raise ValueError(f"CNPJ inválido na curadoria: {raw_cnpj}")

    basis = "|".join(
        (
            normalize_text(row["fonte"]),
            normalize_text(row["nome"]),
            f'{float(row["latitude"]):.6f}',
            f'{float(row["longitude"]):.6f}',
        )
    )
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()
    return {"stable_key": f"synthetic:{digest}", "identity_synthetic": True}


def normalize_curated_ledger(source_path, output_path):
    source_path = Path(source_path)
    output_path = Path(output_path)
    with source_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    output_rows = []
    seen_keys = {}
    for line_number, row in enumerate(rows, start=2):
        identity = build_stable_identity(row)
        stable_key = identity["stable_key"]
        if stable_key in seen_keys:
            raise ValueError(
                f"stable_key duplicada {stable_key}: "
                f"linhas {seen_keys[stable_key]} e {line_number}"
            )
        seen_keys[stable_key] = line_number
        output_rows.append(
            {
                "stable_key": stable_key,
                "identity_synthetic": str(identity["identity_synthetic"]).lower(),
                "status": row["status"],
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            writer = csv.DictWriter(
                handle,
                fieldnames=["stable_key", "identity_synthetic", "status"],
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(output_rows)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output_path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"row_count": len(output_rows)}


def summarize_national(mapeando, cnpj, terreiros_brasil, dedup_report):
    admitted_mapeando = sum(
        row.get("nominatim_lat") is not None and row.get("nominatim_lng") is not None
        for row in mapeando
    )
    admitted_cnpj = sum(
        row.get("lat") is not None and row.get("lng") is not None for row in cnpj
    )
    natal_default = (-5.7841695, -35.1999708)
    admitted_tdb = sum(
        row.get("lat") is not None
        and row.get("lng") is not None
        and (row["lat"], row["lng"]) != natal_default
        for row in terreiros_brasil
    )
    admitted = admitted_mapeando + admitted_cnpj + admitted_tdb
    duplicates = dedup_report["duplicates"]
    duplicate_count = dedup_report["duplicatas"]
    if duplicate_count != len(duplicates):
        raise ValueError(
            "duplicatas divergentes: "
            f"esperado {duplicate_count}, encontrado {len(duplicates)}"
        )
    accounted = dedup_report["mantidos"] + duplicate_count
    total_bruto = dedup_report["total_bruto"]
    if accounted != total_bruto or accounted != admitted:
        raise ValueError(
            "equação contábil nacional divergente: "
            f"mantidos({dedup_report['mantidos']}) + duplicatas({duplicate_count}) "
            f"= {accounted}, total_bruto={total_bruto}, admitidos={admitted}"
        )

    removed_by_source = Counter(
        item["removed_source"] for item in dedup_report["duplicates"]
    )
    source_labels = {
        "receita_federal_cnpj": "cnpj",
        "mapeando_axe": "mapeando_axe",
        "terreirosdobrasil": "terreirosdobrasil",
    }
    known_sources = set(source_labels)
    for index, item in enumerate(duplicates, start=1):
        for field in ("removed_source", "kept_source"):
            if item[field] not in known_sources:
                raise ValueError(
                    f"fonte desconhecida em duplicates[{index}].{field}: {item[field]}"
                )
    breakdown = {label: 0 for label in source_labels.values()}
    for source, count in removed_by_source.items():
        breakdown[source_labels[source]] = count
    if sum(breakdown.values()) != duplicate_count:
        raise ValueError(
            "breakdown de duplicatas não fecha: "
            f"esperado {duplicate_count}, encontrado {sum(breakdown.values())}"
        )

    pair_counts = Counter(
        (item["removed_source"], item["kept_source"])
        for item in dedup_report["duplicates"]
    )
    return {
        "brutos": len(mapeando) + len(cnpj) + len(terreiros_brasil),
        "admitidos": admitted,
        "admitidos_por_fonte": {
            "mapeando_axe": admitted_mapeando,
            "cnpj": admitted_cnpj,
            "terreirosdobrasil": admitted_tdb,
        },
        "mantidos": dedup_report["mantidos"],
        "removidos": dedup_report["duplicatas"],
        "removidos_por_fonte": breakdown,
        "pares_mapeando": {
            "mapeando_axe->mapeando_axe": pair_counts[
                ("mapeando_axe", "mapeando_axe")
            ],
            "mapeando_axe->cnpj": pair_counts[
                ("mapeando_axe", "receita_federal_cnpj")
            ],
        },
        "limiar_efetivo_legado": 0.5,
    }


def _source_name_key(row):
    return normalize_text(row["fonte"]), normalize_text(row["nome"])


def _location_key(row):
    source_aliases = {"google places": "google"}
    source = source_aliases.get(normalize_text(row["fonte"]), normalize_text(row["fonte"]))
    latitude = row.get("lat", row.get("latitude"))
    longitude = row.get("lng", row.get("longitude"))
    return (
        source,
        normalize_text(row["nome"]),
        round(float(latitude), 6),
        round(float(longitude), 6),
    )


def summarize_bahia(
    historical, removals, false_positives, ambiguous, exclusions, current
):
    historical_index = {}
    for row in historical:
        historical_index.setdefault(_source_name_key(row), []).append(row)

    recovered_removals = set()
    for removal in removals:
        matches = historical_index.get(_source_name_key(removal), [])
        if len(matches) != 1:
            raise ValueError("remoção legada não resolve unicamente no snapshot histórico")
        recovered_removals.add(_location_key(matches[0]))

    exclusion_keys = {_location_key(row) for row in exclusions}
    false_positive_keys = {_location_key(row) for row in false_positives}
    ambiguous_keys = {_location_key(row) for row in ambiguous}
    current_keys = {
        _location_key(row)
        for row in current
        if row.get("lat", row.get("latitude")) is not None
        and row.get("lng", row.get("longitude")) is not None
    }

    in_removals = ambiguous_keys & recovered_removals
    in_exclusions = ambiguous_keys & exclusion_keys
    pending = ambiguous_keys & current_keys
    residual = ambiguous_keys - in_removals - in_exclusions - pending
    outside_bbox = {
        key
        for key in residual
        if not (-18.5 <= key[2] <= -8.5 and -46.7 <= key[3] <= -37.0)
    }
    if residual != outside_bbox:
        raise ValueError("ambíguos não reconciliados por chave exata")

    return {
        "remocoes_heuristicas": len(recovered_removals),
        "intersecao_remocoes_exclusoes": len(recovered_removals & exclusion_keys),
        "falsos_positivos_nas_remocoes": len(
            false_positive_keys & recovered_removals
        ),
        "ambiguos": {
            "total": len(ambiguous_keys),
            "nas_remocoes": len(in_removals),
            "fora_bbox": len(outside_bbox),
            "nas_exclusoes_curadas": len(in_exclusions),
            "ambiguos_pendentes_v2": len(pending),
        },
    }
