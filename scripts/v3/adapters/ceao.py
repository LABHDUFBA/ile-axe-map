"""Adaptador mecânico da fonte Bahia CEAO."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from scripts.v3.adapters.common import build_base_source_record, normalize_source_id


SOURCE = "ceao"


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
        native_id = normalize_source_id(record.get("ceao_id"))
        return build_base_source_record(
            fonte=SOURCE,
            id_fonte=native_id,
            id_fonte_sintetico=False,
            nome_original=_filled_text(record.get("nome"), "nome"),
            dados_originais=record,
            latitude=record.get("lat"),
            longitude=record.get("lng"),
            endereco=record.get("endereco"),
            cep=record.get("cep"),
            ceao_id=native_id,
        )
    except (TypeError, ValueError) as error:
        raise type(error)(f"{SOURCE}, índice {index}: {error}") from error


def adapt_record(record: dict[str, Any]) -> dict[str, Any]:
    """Adapta uma ocorrência sem interpretar campos religiosos derivados."""
    return _adapt_record(record, 0)


def adapt_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Adapta um iterável em ordem, produzindo uma saída por entrada."""
    return [_adapt_record(record, index) for index, record in enumerate(records)]
