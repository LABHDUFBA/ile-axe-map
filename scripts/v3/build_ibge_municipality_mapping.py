"""Extrai a ponte municipal mínima do DBF oficial da Malha Municipal IBGE 2024."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import struct
import sys
from pathlib import Path


def read_dbf(path: Path) -> list[dict[str, str]]:
    content = path.read_bytes()
    cpg_path = path.with_suffix(".cpg")
    encoding = cpg_path.read_text(encoding="ascii").strip() if cpg_path.exists() else "latin-1"
    record_count = struct.unpack("<I", content[4:8])[0]
    header_size = struct.unpack("<H", content[8:10])[0]
    record_size = struct.unpack("<H", content[10:12])[0]
    fields: list[tuple[str, int]] = []
    offset = 32
    while content[offset] != 13:
        descriptor = content[offset : offset + 32]
        fields.append((descriptor[:11].split(b"\0")[0].decode("ascii"), descriptor[16]))
        offset += 32
    rows = []
    for index in range(record_count):
        record = content[header_size + index * record_size : header_size + (index + 1) * record_size]
        if record[:1] == b"*":
            continue
        position = 1
        values = {}
        for name, width in fields:
            values[name] = record[position : position + width].decode(encoding).strip()
            position += width
        rows.append({"codigo_ibge": values["CD_MUN"], "nome": values["NM_MUN"], "uf": values["SIGLA_UF"]})
    return rows


def read_siafi(path: Path) -> tuple[dict[str, str], bytes]:
    content = path.read_bytes()
    mapping: dict[str, str] = {}
    seen_siafi: set[str] = set()
    for line in content.decode("ascii").splitlines():
        siafi, _cnpj, _name, _uf, ibge = line.split(";")
        if ibge == "0000000":
            continue
        if ibge in mapping or siafi in seen_siafi:
            raise RuntimeError("código IBGE ou SIAFI duplicado na tabela SIAFI")
        mapping[ibge] = siafi
        seen_siafi.add(siafi)
    return mapping, content


def build(
    source: Path,
    siafi_source: Path,
    csv_output: Path,
    metadata_output: Path,
    *,
    expected_dbf_records: int | None = 5_573,
) -> None:
    rows = read_dbf(source)
    siafi_by_ibge, siafi_content = read_siafi(siafi_source)
    if expected_dbf_records is not None and len(rows) != expected_dbf_records:
        raise RuntimeError("DBF municipal inesperado")
    if len({row["codigo_ibge"] for row in rows}) != len(rows):
        raise RuntimeError("código IBGE duplicado no DBF")
    if len({(row["nome"], row["uf"]) for row in rows}) != len(rows):
        raise RuntimeError("par nome e UF duplicado no DBF")
    matched = sum(row["codigo_ibge"] in siafi_by_ibge for row in rows)
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    with csv_output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["codigo_ibge", "codigo_siafi", "nome", "uf"], lineterminator="\n")
        writer.writeheader()
        writer.writerows({**row, "codigo_siafi": siafi_by_ibge.get(row["codigo_ibge"], "")} for row in rows)
    mapping_content = csv_output.read_bytes()
    content = source.read_bytes()
    metadata = {
        "arquivo_fonte": source.name,
        "bytes_dbf": len(content),
        "campos_fonte": {"codigo_ibge": "CD_MUN", "nome": "NM_MUN", "uf": "SIGLA_UF"},
        "geracao": "Leitura determinística do DBF oficial, sem geometria nem fuzzy matching.",
        "observacao_registros": "A Malha Municipal 2024 contém 5.573 registros: municípios e áreas operacionais codificadas pelo IBGE. A ponte preserva todos os registros oficiais.",
        "registros": len(rows),
        "registros_com_siafi": matched,
        "registros_sem_siafi": len(rows) - matched,
        "sha256_dbf": hashlib.sha256(content).hexdigest(),
        "fonte_siafi": "https://www.tesourotransparente.gov.br/ckan/dataset/abb968cb-3710-4f85-89cf-875c91b9c7f6/resource/eebb3bc6-9eea-4496-8bcf-304f33155282/download/tabmun.csv",
        "sha256_siafi_csv": hashlib.sha256(siafi_content).hexdigest(),
        "sha256_mapping_csv": hashlib.sha256(mapping_content).hexdigest(),
        "versao": "IBGE Malha Municipal 2024",
    }
    metadata_output.write_text(json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--siafi-csv", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    source = root / "data/reference/BR_Municipios_2024/BR_Municipios_2024.dbf"
    build(source, args.siafi_csv, root / "config/ibge_municipios_2024.csv", root / "config/ibge_municipios_2024.metadata.json")
    print("mapping IBGE 2024: 5.573 municípios")
