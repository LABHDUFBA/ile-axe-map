import csv
import hashlib
import json
import re
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
        if not required.issubset(item):
            raise ValueError("manifest sem metadados obrigatórios")
        relative = Path(item["path"])
        if relative.is_absolute():
            raise ValueError("manifest exige path local relativo")
        path = (root / relative).resolve()
        if root not in path.parents:
            raise ValueError("path do manifest escapa da raiz")
        actual_hash = sha256_file(path)
        if actual_hash != item["sha256"]:
            raise ValueError(f"hash divergente: {item['name']}")
        if _record_count(path) != item["count"]:
            raise ValueError(f"contagem divergente: {item['name']}")
        validated[item["name"]] = actual_hash
    return validated


def build_stable_identity(row):
    cnpjs = re.findall(r"(?:\d[.\-/ ]*){14}", row.get("motivo", ""))
    if cnpjs:
        digits = re.sub(r"\D", "", cnpjs[0])
        if len(digits) == 14:
            return {
                "stable_key": f"cnpj:{digits}",
                "identity_synthetic": False,
            }

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
    with source_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    output_rows = []
    for row in rows:
        identity = build_stable_identity(row)
        output_rows.append(
            {
                **row,
                "stable_key": identity["stable_key"],
                "identity_synthetic": str(identity["identity_synthetic"]).lower(),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames + ["stable_key", "identity_synthetic"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(output_rows)
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
    if admitted != dedup_report["total_bruto"]:
        raise ValueError("admitidos não fecham com o relatório legado")

    removed_by_source = Counter(
        item["removed_source"] for item in dedup_report["duplicates"]
    )
    source_labels = {
        "receita_federal_cnpj": "cnpj",
        "mapeando_axe": "mapeando_axe",
        "terreirosdobrasil": "terreirosdobrasil",
    }
    breakdown = {label: 0 for label in source_labels.values()}
    for source, count in removed_by_source.items():
        breakdown[source_labels[source]] = count

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
