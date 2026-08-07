"""Adaptador mecânico da fonte nacional Mapeando Axé."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from scripts.v3.adapters.common import build_base_source_record


SOURCE = "mapeando_axe"


def _filled_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("nome deve ser texto ou nulo")
    return value if value.strip() else None


def _adapt_record(record: Any, index: int) -> dict[str, Any]:
    try:
        if not isinstance(record, dict):
            raise TypeError("registro deve ser um dicionário")
        return build_base_source_record(
            fonte=SOURCE,
            id_fonte=record.get("source_record_id"),
            id_fonte_sintetico=False,
            nome_original=_filled_text(record.get("name")),
            dados_originais=record,
            endereco=record.get("address_raw"),
            municipio=record.get("city"),
            uf=record.get("state"),
            cep=record.get("postcode"),
        )
    except (TypeError, ValueError) as error:
        raise type(error)(f"{SOURCE}, índice {index}: {error}") from error


def adapt_record(record: dict[str, Any]) -> dict[str, Any]:
    """Adapta uma ocorrência, preservando o payload integral sem inferências."""
    return _adapt_record(record, 0)


def adapt_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Adapta um iterável em ordem, produzindo uma saída por entrada."""
    return [_adapt_record(record, index) for index, record in enumerate(records)]
