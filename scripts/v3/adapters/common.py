"""Utilitários compartilhados pelos adaptadores de fontes v3."""

from __future__ import annotations

import copy
from datetime import date
import hashlib
import json
import math
import re
from typing import Any
from urllib.parse import quote, urlsplit


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
    """Normaliza IDs textuais ou inteiros, sem aceitar tipos ambíguos."""
    if value is None:
        raise ValueError("id_fonte não pode ser nulo")
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise TypeError("id_fonte deve ser string ou inteiro não booleano")

    normalized = value.strip() if isinstance(value, str) else str(value)
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
    """Gera ID sintético com fronteiras e tipos explícitos em JSON canônico."""
    _validate_source(fonte)
    if not parts:
        raise ValueError("ao menos uma parte é necessária para o ID sintético")

    typed_parts = []
    for part in parts:
        if part is None:
            typed_parts.append({"tipo": "null", "valor": None})
        elif isinstance(part, bool):
            typed_parts.append({"tipo": "boolean", "valor": part})
        elif isinstance(part, str):
            if not part.strip():
                raise ValueError("parte textual do ID sintético não pode ser vazia")
            typed_parts.append({"tipo": "string", "valor": part})
        elif isinstance(part, int):
            typed_parts.append({"tipo": "integer", "valor": part})
        elif isinstance(part, float):
            if not math.isfinite(part):
                raise ValueError("parte numérica do ID sintético deve ser finita")
            typed_parts.append({"tipo": "number", "valor": part})
        else:
            raise TypeError(
                "parte do ID sintético deve ser string, inteiro, float, booleano ou nulo"
            )

    basis = json.dumps(
        {"fonte": fonte, "partes": typed_parts},
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


def _validate_coordinate(value: Any, name: str, minimum: float, maximum: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} da coordenada deve ser numérica e não booleana")
    if not math.isfinite(value):
        raise ValueError(f"{name} da coordenada deve ser finita")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} da coordenada fora da faixa permitida")


def _validate_alternative_coordinates(coordinates: Any) -> None:
    if not isinstance(coordinates, list):
        raise TypeError("coordenadas alternativas devem ser uma lista")

    required = {"latitude", "longitude", "fonte", "precisao"}
    for coordinate in coordinates:
        if not isinstance(coordinate, dict) or set(coordinate) != required:
            raise ValueError(
                "coordenada alternativa deve conter latitude, longitude, fonte e precisao"
            )
        try:
            _validate_coordinate(coordinate["latitude"], "latitude", -90, 90)
            _validate_coordinate(coordinate["longitude"], "longitude", -180, 180)
        except (TypeError, ValueError) as error:
            raise type(error)(f"coordenada alternativa inválida: {error}") from error
        if not isinstance(coordinate["fonte"], str) or not coordinate["fonte"].strip():
            raise ValueError("fonte da coordenada alternativa deve ser texto não vazio")
        if coordinate["precisao"] is not None and not isinstance(
            coordinate["precisao"], str
        ):
            raise TypeError("precisao da coordenada alternativa deve ser texto ou nula")


def _merge_audit_flags(overrides: Any) -> dict[str, bool]:
    flags = empty_audit_flags()
    if overrides is None:
        return flags
    if not isinstance(overrides, dict):
        raise TypeError("flags_auditoria deve ser um dicionário")

    unknown = set(overrides) - set(AUDIT_FLAG_NAMES)
    if unknown:
        raise ValueError(f"flag de auditoria desconhecida: {sorted(unknown)[0]}")
    for name, value in overrides.items():
        if not isinstance(value, bool):
            raise TypeError(f"flag de auditoria {name!r} deve ser booleana")
        flags[name] = value
    return flags


def _validate_nullable_text(value: Any, name: str, *, nonempty: bool = False) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        raise TypeError(f"{name} deve ser texto ou nulo")
    if nonempty and not value.strip():
        raise ValueError(f"{name} não pode ser vazio")


def _validate_collection_date(value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        raise TypeError("data_coleta deve ser texto ou nula")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("data_coleta deve usar o formato YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("data_coleta deve representar uma data real") from error


def _validate_url(value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        raise TypeError("url deve ser texto ou nula")
    if re.search(r"\s", value):
        raise ValueError("url não pode conter espaços")
    try:
        parsed = urlsplit(value)
        parsed.port
    except ValueError as error:
        raise ValueError("url inválida") from error
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.netloc.startswith("@")
    ):
        raise ValueError("url deve ser HTTP(S) absoluta com hostname")


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
    if not isinstance(id_fonte_sintetico, bool):
        raise TypeError("id_fonte_sintetico deve ser booleano")
    _validate_nullable_text(nome_original, "nome_original", nonempty=True)
    if not isinstance(dados_originais, dict):
        raise TypeError("dados_originais deve ser um dicionário")

    nullable_text_fields = {
        "endereco": endereco,
        "municipio": municipio,
        "uf": uf,
        "cep": cep,
        "precisao": precisao,
        "fonte_coordenada": fonte_coordenada,
        "tradicao": tradicao,
        "nacao": nacao,
        "denominacao": denominacao,
        "cnpj": cnpj,
        "ceao_id": ceao_id,
        "osm_id": osm_id,
        "google_place_id": google_place_id,
    }
    for field_name, value in nullable_text_fields.items():
        _validate_nullable_text(value, field_name)
    if cnpj is not None and not valid_cnpj(cnpj):
        raise ValueError("cnpj inválido")
    _validate_url(url)
    _validate_collection_date(data_coleta)

    if (latitude is None) != (longitude is None):
        raise ValueError("coordenadas principais devem estar ambas presentes ou nulas")
    if latitude is not None:
        _validate_coordinate(latitude, "latitude", -90, 90)
        _validate_coordinate(longitude, "longitude", -180, 180)

    alternative_coordinates = (
        [] if coordenadas_alternativas is None else coordenadas_alternativas
    )
    _validate_alternative_coordinates(alternative_coordinates)
    audit_flags = _merge_audit_flags(flags_auditoria)

    record = {
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
            "coordenadas_alternativas": alternative_coordinates,
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
        "flags_auditoria": audit_flags,
        "dados_originais": dados_originais,
    }
    return copy.deepcopy(record)
