"""Utilitários compartilhados pelos adaptadores de fontes v3."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence, Set
from typing import Any
from urllib.parse import quote


SOURCES = frozenset(
    {
        "ceao",
        "bahia_google",
        "osm",
        "sefaz",
        "mapeando_axe",
        "cnpj",
        "terreiros_brasil",
    }
)

AUDIT_FLAG_NAMES = (
    "baseline_atual",
    "exclusao_curada",
    "remocao_heuristica_legada",
    "ambiguo_pendente",
    "dedup_legado_recuperado",
)


def normalize_source_id(value: Any) -> str:
    """Converte um ID escalar em texto, preservando zeros à esquerda."""
    if value is None:
        raise ValueError("id_fonte não pode ser nulo")
    if isinstance(value, (Mapping, Set)) or (
        isinstance(value, Sequence) and not isinstance(value, str)
    ):
        raise TypeError("id_fonte deve ser escalar")

    normalized = str(value).strip()
    if not normalized:
        raise ValueError("id_fonte não pode ser vazio")
    return normalized


def _validate_source(fonte: str) -> None:
    if fonte not in SOURCES:
        raise ValueError(f"fonte fora do contrato v3: {fonte!r}")


def make_source_record_key(fonte: str, id_fonte: Any) -> str:
    """Monta a chave com o ID codificado por percent-encoding UTF-8."""
    _validate_source(fonte)
    encoded_id = quote(normalize_source_id(id_fonte), safe="")
    return f"{fonte}:{encoded_id}"


def synthetic_source_id(fonte: str, *parts: Any) -> str:
    """Gera ID sintético SHA-256 sobre fonte e partes serializadas em JSON."""
    _validate_source(fonte)
    if not parts:
        raise ValueError("ao menos uma parte é necessária para o ID sintético")

    normalized_parts = [normalize_source_id(part) for part in parts]
    basis = json.dumps(
        {"fonte": fonte, "partes": normalized_parts},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"synthetic:{hashlib.sha256(basis).hexdigest()}"


def valid_cnpj(value: Any) -> bool:
    """Valida formato, comprimento e dígitos verificadores de um CNPJ."""
    if not isinstance(value, str):
        return False
    if re.fullmatch(r"\d{14}", value):
        digits = value
    elif re.fullmatch(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", value):
        digits = re.sub(r"\D", "", value)
    else:
        return False

    if len(set(digits)) == 1:
        return False

    def check_digit(prefix: str, weights: tuple[int, ...]) -> str:
        total = sum(int(digit) * weight for digit, weight in zip(prefix, weights))
        remainder = total % 11
        return "0" if remainder < 2 else str(11 - remainder)

    first = check_digit(digits[:12], (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
    second = check_digit(
        digits[:12] + first, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    )
    return digits[-2:] == first + second


def empty_audit_flags() -> dict[str, bool]:
    """Retorna um novo conjunto vazio de flags a cada chamada."""
    return {name: False for name in AUDIT_FLAG_NAMES}


def build_base_source_record(
    *,
    fonte: str,
    id_fonte: Any,
    id_fonte_sintetico: bool,
    nome_original: str | None,
    dados_originais: dict[str, Any],
    latitude: float | None = None,
    longitude: float | None = None,
    endereco: str | None = None,
    municipio: str | None = None,
    uf: str | None = None,
    cep: str | None = None,
    precisao: str | None = None,
    fonte_coordenada: str | None = None,
    coordenadas_alternativas: list[dict[str, Any]] | None = None,
    tradicao: str | None = None,
    nacao: str | None = None,
    denominacao: str | None = None,
    cnpj: str | None = None,
    ceao_id: str | None = None,
    osm_id: str | None = None,
    google_place_id: str | None = None,
    url: str | None = None,
    data_coleta: str | None = None,
    flags_auditoria: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Monta a estrutura comum sem classificar identidade religiosa."""
    normalized_id = normalize_source_id(id_fonte)
    return {
        "source_record_key": make_source_record_key(fonte, normalized_id),
        "fonte": fonte,
        "id_fonte": normalized_id,
        "id_fonte_sintetico": id_fonte_sintetico,
        "nome_original": nome_original,
        "localizacao_original": {
            "latitude": latitude,
            "longitude": longitude,
            "endereco": endereco,
            "municipio": municipio,
            "uf": uf,
            "cep": cep,
            "precisao": precisao,
            "fonte_coordenada": fonte_coordenada,
            "coordenadas_alternativas": list(coordenadas_alternativas or []),
        },
        "identidade_religiosa_original": {
            "tradicao": tradicao,
            "nacao": nacao,
            "denominacao": denominacao,
        },
        "identificadores": {
            "cnpj": cnpj,
            "ceao_id": ceao_id,
            "osm_id": osm_id,
            "google_place_id": google_place_id,
            "url": url,
        },
        "data_coleta": data_coleta,
        "flags_auditoria": dict(flags_auditoria or empty_audit_flags()),
        "dados_originais": dados_originais,
    }
