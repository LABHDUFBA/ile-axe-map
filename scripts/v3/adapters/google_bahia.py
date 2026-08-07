"""Adaptador mecânico da fonte Google no agregado Bahia."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from scripts.v3.adapters.common import build_base_source_record, synthetic_source_id


SOURCE = "bahia_google"


def _filled_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{field} deve ser texto ou nulo")
    return value if value.strip() else None


def _adapt_record(record: Any, index: int) -> dict[str, Any]:
    try:
        if not isinstance(record, dict):
            raise TypeError("registro deve ser um dicionário")
        name = _filled_text(record.get("nome"), "nome")
        latitude = record.get("lat")
        longitude = record.get("lng")
        source_id = synthetic_source_id(SOURCE, name, latitude, longitude)
        return build_base_source_record(
            fonte=SOURCE,
            id_fonte=source_id,
            id_fonte_sintetico=True,
            nome_original=name,
            dados_originais=record,
            latitude=latitude,
            longitude=longitude,
            endereco=record.get("endereco"),
        )
    except (TypeError, ValueError) as error:
        raise type(error)(f"{SOURCE}, índice {index}: {error}") from error


def adapt_record(record: dict[str, Any]) -> dict[str, Any]:
    """Adapta uma ocorrência, sem inventar o Place ID ausente no agregado."""
    return _adapt_record(record, 0)


def adapt_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Adapta um iterável em ordem, produzindo uma saída por entrada."""
    return [_adapt_record(record, index) for index, record in enumerate(records)]
