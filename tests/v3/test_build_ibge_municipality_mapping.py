import csv
import hashlib
import json
import struct
from pathlib import Path

import pytest

from scripts.v3 import build_ibge_municipality_mapping as builder


def _write_dbf(path: Path, rows: list[tuple[str, str, str]]) -> None:
    fields = (("CD_MUN", 7), ("NM_MUN", 80), ("SIGLA_UF", 2))
    header_size = 32 + 32 * len(fields) + 1
    record_size = 1 + sum(width for _, width in fields)
    header = bytearray(32)
    header[4:8] = struct.pack("<I", len(rows))
    header[8:10] = struct.pack("<H", header_size)
    header[10:12] = struct.pack("<H", record_size)
    descriptors = bytearray()
    for name, width in fields:
        descriptor = bytearray(32)
        descriptor[: len(name)] = name.encode("ascii")
        descriptor[11] = ord("C")
        descriptor[16] = width
        descriptors.extend(descriptor)
    records = bytearray()
    for values in rows:
        records.extend(b" ")
        for value, (_, width) in zip(values, fields):
            encoded = value.encode("utf-8")
            records.extend(encoded.ljust(width, b" "))
    path.write_bytes(bytes(header) + bytes(descriptors) + b"\r" + bytes(records) + b"\x1a")


def test_read_dbf_respeita_cpg_utf8(tmp_path):
    dbf = tmp_path / "municipios.dbf"
    _write_dbf(dbf, [("4300002", 'Área Operacional "Lagoa dos Patos"', "RS")])
    dbf.with_suffix(".cpg").write_text("UTF-8", encoding="ascii")

    assert builder.read_dbf(dbf) == [
        {"codigo_ibge": "4300002", "nome": 'Área Operacional "Lagoa dos Patos"', "uf": "RS"}
    ]


def test_build_registra_hashes_e_contagens_da_ponte(tmp_path, monkeypatch):
    dbf = tmp_path / "municipios.dbf"
    dbf.write_bytes(b"dbf-oficial")
    siafi = tmp_path / "tabmun.csv"
    siafi.write_bytes(
        b"3849;00000000000000;SALVADOR ;BA;2927408\r\n"
        b"9999; ;DEMAIS MUNICIPIOS ;BA;0000000\r\n"
    )
    rows = [
        {"codigo_ibge": "2927408", "nome": "Salvador", "uf": "BA"},
        {"codigo_ibge": "5101837", "nome": "Boa Esperança do Norte", "uf": "MT"},
    ]
    monkeypatch.setattr(builder, "read_dbf", lambda _path: rows)
    output = tmp_path / "mapping.csv"
    metadata = tmp_path / "mapping.metadata.json"

    builder.build(dbf, siafi, output, metadata, expected_dbf_records=None)

    mapped = list(csv.DictReader(output.open(encoding="utf-8", newline="")))
    assert mapped[0]["codigo_siafi"] == "3849"
    assert mapped[1]["codigo_siafi"] == ""
    details = json.loads(metadata.read_text(encoding="utf-8"))
    assert details["registros_com_siafi"] == 1
    assert details["registros_sem_siafi"] == 1
    assert details["sha256_mapping_csv"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert details["sha256_siafi_csv"] == hashlib.sha256(siafi.read_bytes()).hexdigest()
    assert details["fonte_siafi"].startswith("https://www.tesourotransparente.gov.br/")


def test_build_rejeita_chaves_duplicadas(tmp_path, monkeypatch):
    dbf = tmp_path / "municipios.dbf"
    dbf.write_bytes(b"dbf")
    siafi = tmp_path / "tabmun.csv"
    siafi.write_bytes(b"3849;0;SALVADOR ;BA;2927408\r\n")
    monkeypatch.setattr(
        builder,
        "read_dbf",
        lambda _path: [
            {"codigo_ibge": "2927408", "nome": "Salvador", "uf": "BA"},
            {"codigo_ibge": "2927409", "nome": "Salvador", "uf": "BA"},
        ],
    )

    with pytest.raises(RuntimeError, match="nome.*UF duplicado"):
        builder.build(dbf, siafi, tmp_path / "out.csv", tmp_path / "meta.json", expected_dbf_records=None)
