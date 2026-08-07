#!/usr/bin/env python3
"""Inventaria variáveis das sete fontes v3 sem expor valores dos registros."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "config/source_manifests_v3.json"
DEFAULT_CSV = ROOT / "data/audit/v3/source_variable_matrix.csv"
DEFAULT_JSON = ROOT / "data/audit/v3/source_variable_coverage.json"

EXPECTED_LOGICAL_COUNTS = {
    "bahia_google": 550,
    "ceao": 1155,
    "cnpj": 2673,
    "mapeando_axe": 3923,
    "osm": 20,
    "sefaz": 234,
    "terreiros_brasil": 260,
}
EXPECTED_RAW_TOTAL = 8815
BAHIA_SOURCE_NAMES = {
    "ceao": "ceao",
    "google": "bahia_google",
    "osm": "osm",
    "sefaz": "sefaz",
}
INPUT_NAMES = ("mapeando_axe", "cnpj", "terreiros_brasil", "bahia_v2")
CSV_COLUMNS = (
    "fonte",
    "campo_original",
    "tipos_observados",
    "registros_fonte",
    "preenchidos",
    "cobertura_percentual",
    "grupo_semantico",
    "campo_nacional",
    "regra_harmonizacao",
    "incluir_formato_nacional",
    "observacao",
)

# Mapeamento inicial e revisável. Ausência desta tabela significa preservar ou revisar,
# nunca assumir equivalência semântica por semelhança do nome.
SEMANTIC_FIELDS = {
    "address_raw": ("localizacao_endereco", "localizacao.endereco_declarado", "copiar_declarado", "sim", "Endereço livre declarado pela fonte."),
    "ano_fundacao": ("organizacao_historia", "organizacao.ano_fundacao_declarado", "normalizar_sem_substituir", "sim", "Manter também a forma declarada."),
    "bairro": ("localizacao_endereco", "localizacao.bairro_declarado", "normalizar_sem_substituir", "sim", ""),
    "categoria_raw": ("identidade_religiosa", "identidade_religiosa.categoria_declarada", "copiar_declarado", "sim", "Categoria textual preservada sem convertê-la em tradição ou nação."),
    "ceao_id": ("identificadores", "identificadores.ceao_id", "identificador", "sim", ""),
    "cep": ("localizacao_endereco", "localizacao.cep_declarado", "normalizar_sem_substituir", "sim", ""),
    "cidade": ("localizacao_endereco", "localizacao.municipio_declarado", "normalizar_sem_substituir", "sim", ""),
    "city": ("localizacao_endereco", "localizacao.municipio_declarado", "normalizar_sem_substituir", "sim", ""),
    "cnpj": ("identificadores", "identificadores.cnpj", "identificador", "sim", "Dado organizacional sujeito a validação, sem substituir o declarado."),
    "codigo_municipio": ("localizacao_endereco", "localizacao.codigo_municipio_declarado", "preservar_original", "revisar", "Código cadastral de domínio não confirmado; não tratar como IBGE sem validação da fonte."),
    "data_inicio": ("organizacao_historia", "organizacao.data_inicio_cadastral_declarada", "preservar_original", "revisar", "Data cadastral de semântica pendente; não representa fundação religiosa confirmada."),
    "descricao": ("identificacao_nome", "identificacao.descricao_declarada", "copiar_declarado", "sim", "Descrição exclusiva útil, mantida com proveniência."),
    "endereco": ("localizacao_endereco", "localizacao.endereco_declarado", "copiar_declarado", "sim", ""),
    "fonte": ("proveniencia_qualidade", "proveniencia.fonte", "identificador", "sim", ""),
    "source": ("proveniencia_qualidade", "proveniencia.fonte", "identificador", "sim", ""),
    "fonte_detalhe": ("proveniencia_qualidade", "proveniencia.descricao_fonte", "copiar_declarado", "sim", ""),
    "foto_grande": ("midia", "midia.imagem_principal_url", "copiar_declarado", "sim", "URL de mídia, publicação sujeita a direitos e controle."),
    "foto_thumb": ("midia", "midia.miniatura_url", "copiar_declarado", "sim", "URL de mídia, publicação sujeita a direitos e controle."),
    "fontes": ("proveniencia_qualidade", "proveniencia.fontes_relacionadas", "preservar_original", "revisar", "Pode refletir processamento anterior."),
    "geo_status": ("proveniencia_qualidade", "qualidade.status_geografico", "normalizar_sem_substituir", "sim", ""),
    "id": ("identificadores", "identificadores.id_nativo", "identificador", "sim", "Identificador com namespace da fonte."),
    "lat": ("localizacao_endereco", "localizacao.latitude", "coordenada", "sim", ""),
    "lideranca": ("organizacao_historia", "organizacao.lideranca_declarada", "copiar_declarado", "sim", "Dado interno, controlar publicação."),
    "link": ("proveniencia_qualidade", "proveniencia.url_registro", "copiar_declarado", "sim", ""),
    "lng": ("localizacao_endereco", "localizacao.longitude", "coordenada", "sim", ""),
    "logradouro": ("localizacao_endereco", "localizacao.logradouro_declarado", "normalizar_sem_substituir", "sim", ""),
    "metodo_classificacao": ("proveniencia_qualidade", "qualidade.metodo_classificacao", "preservar_original", "revisar", "Classificação derivada, não tratar como declaração."),
    "nacao": ("identidade_religiosa", "identidade_religiosa.nacao_declarada", "preservar_original", "revisar", "Destino candidato; validar por fonte se é declaração, descrição editorial ou classificação de terceiro."),
    "nacao_categoria": ("identidade_religiosa", "identidade_religiosa.categoria_normalizada", "preservar_original", "revisar", "Campo derivado no agregado Bahia."),
    "nacao_componentes": ("identidade_religiosa", "identidade_religiosa.componentes", "preservar_original", "revisar", "Campo derivado no agregado Bahia."),
    "nacao_original": ("identidade_religiosa", "identidade_religiosa.nacao_declarada", "preservar_original", "revisar", "Destino candidato; origem e semântica precisam ser validadas por fonte."),
    "nacao_primaria": ("identidade_religiosa", "identidade_religiosa.nacao_normalizada", "preservar_original", "revisar", "Campo derivado no agregado Bahia."),
    "name": ("identificacao_nome", "nome.declarado", "copiar_declarado", "sim", "Não eleger nome preferido nesta etapa."),
    "nome": ("identificacao_nome", "nome.declarado", "copiar_declarado", "sim", "Não eleger nome preferido nesta etapa."),
    "nome_fantasia": ("identificacao_nome", "nome.declarado", "copiar_declarado", "sim", "Nome fantasia cadastral."),
    "nominatim_addresstype": ("geocodificacao", "geocodificacao.tipo_endereco", "inferido_geocodificacao", "revisar", "Vocabulário específico do geocodificador."),
    "nominatim_confidence": ("geocodificacao", "geocodificacao.confianca", "inferido_geocodificacao", "sim", "Escala precisa ser documentada antes da harmonização."),
    "nominatim_display_name": ("geocodificacao", "geocodificacao.resultado.endereco", "inferido_geocodificacao", "sim", "Resultado auxiliar do geocodificador; não substitui endereço declarado."),
    "nominatim_lat": ("geocodificacao", "geocodificacao.resultado.latitude", "inferido_geocodificacao", "sim", "Coordenada do resultado do geocodificador, não coordenada declarada ou canônica da entidade."),
    "nominatim_lng": ("geocodificacao", "geocodificacao.resultado.longitude", "inferido_geocodificacao", "sim", "Coordenada do resultado do geocodificador, não coordenada declarada ou canônica da entidade."),
    "nominatim_osm_id": ("geocodificacao", "geocodificacao.resultado.osm_id", "inferido_geocodificacao", "sim", "ID do objeto retornado pelo geocodificador; não prova identidade da entidade."),
    "nominatim_osm_type": ("geocodificacao", "geocodificacao.resultado.osm_tipo", "inferido_geocodificacao", "sim", "Tipo do objeto retornado pelo geocodificador."),
    "nominatim_precision": ("geocodificacao", "geocodificacao.precisao", "inferido_geocodificacao", "sim", "Precisão informada pelo processo de geocodificação."),
    "nominatim_query": ("geocodificacao", "geocodificacao.consulta", "inferido_geocodificacao", "revisar", "Interno; pode reproduzir dados de endereço e não deve ser publicado automaticamente."),
    "nominatim_status": ("geocodificacao", "geocodificacao.status", "inferido_geocodificacao", "sim", "Status do processo de geocodificação."),
    "numero": ("localizacao_endereco", "localizacao.numero_declarado", "normalizar_sem_substituir", "sim", ""),
    "postcode": ("localizacao_endereco", "localizacao.cep_declarado", "normalizar_sem_substituir", "sim", ""),
    "precision": ("localizacao_endereco", "localizacao.precisao", "normalizar_sem_substituir", "sim", ""),
    "query_used": ("proveniencia_qualidade", "proveniencia.consulta_geocodificacao", "preservar_original", "revisar", "Interno; pode reproduzir dados de endereço e não deve ser publicado automaticamente."),
    "rating": ("proveniencia_qualidade", "qualidade.avaliacao_fonte", "preservar_original", "revisar", "Métrica específica de plataforma, manter proveniência."),
    "razao_social": ("identificacao_nome", "nome.juridico_declarado", "copiar_declarado", "sim", ""),
    "recovery_method": ("proveniencia_qualidade", "proveniencia.metodo_recuperacao", "preservar_original", "sim", "Método de recuperação do registro, não atributo da entidade."),
    "regente": ("organizacao_historia", "organizacao.regente_declarado", "copiar_declarado", "sim", "Dado interno, controlar publicação."),
    "reviews": ("proveniencia_qualidade", "qualidade.quantidade_avaliacoes_fonte", "preservar_original", "revisar", "Métrica específica de plataforma; confirmar semântica e data de coleta."),
    "sefaz_codigo": ("identificadores", "identificadores.sefaz_codigo", "identificador", "sim", "Identificador com namespace SEFAZ."),
    "source_record_id": ("identificadores", "identificadores.id_nativo", "identificador", "sim", "Identificador com namespace da fonte."),
    "state": ("localizacao_endereco", "localizacao.uf_declarada", "normalizar_sem_substituir", "sim", ""),
    "telefone": ("contato_publicacao", "contato.telefone_declarado", "normalizar_sem_substituir", "sim", "Dado interno; publicação exige controle explícito."),
    "uf": ("localizacao_endereco", "localizacao.uf_declarada", "normalizar_sem_substituir", "sim", ""),
}
PATH_SEMANTIC_FIELDS = {
    "fontes": ("proveniencia_qualidade", "", "preservar_original", "nao", "Contêiner original; mapear pelos campos filhos."),
    "fontes[]": ("proveniencia_qualidade", "", "preservar_original", "nao", "Item estrutural do contêiner original."),
    "fontes[].fonte": ("proveniencia_qualidade", "proveniencia.fontes_relacionadas[].fonte", "identificador", "sim", ""),
    "fontes[].id": ("proveniencia_qualidade", "proveniencia.fontes_relacionadas[].id", "identificador", "sim", "Pode estar ausente no agregado; não inventar ID nativo."),
}
SOURCE_PATH_SEMANTIC_FIELDS = {
    ("cnpj", "lat"): ("geocodificacao", "geocodificacao.resultado.latitude", "inferido_geocodificacao", "sim", "Coordenada do resultado de geocodificação do input CNPJ; não é coordenada declarada ou canônica da entidade."),
    ("cnpj", "lng"): ("geocodificacao", "geocodificacao.resultado.longitude", "inferido_geocodificacao", "sim", "Coordenada do resultado de geocodificação do input CNPJ; não é coordenada declarada ou canônica da entidade."),
    ("cnpj", "precision"): ("geocodificacao", "geocodificacao.precisao", "inferido_geocodificacao", "sim", "Precisão do processo de geocodificação do input CNPJ."),
    ("cnpj", "query_used"): ("geocodificacao", "geocodificacao.consulta", "inferido_geocodificacao", "revisar", "Consulta interna do processo de geocodificação; não publicar automaticamente."),
}


def infer_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    raise TypeError(f"tipo JSON não suportado: {type(value).__name__}")


def _flatten_into(value: Any, path: str, result: dict[str, list[Any]]) -> None:
    if path:
        result[path].append(value)
    if isinstance(value, dict):
        for key in sorted(value):
            child = f"{path}.{key}" if path else key
            _flatten_into(value[key], child, result)
    elif isinstance(value, list):
        item_path = f"{path}[]"
        for item in value:
            _flatten_into(item, item_path, result)


def flatten_record(record: dict[str, Any]) -> dict[str, list[Any]]:
    if not isinstance(record, dict):
        raise TypeError("registro deve ser objeto JSON")
    result: dict[str, list[Any]] = defaultdict(list)
    for key in sorted(record):
        _flatten_into(record[key], key, result)
    return {path: result[path] for path in sorted(result)}


def is_filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(is_filled(item) for item in value)
    if isinstance(value, dict):
        return any(is_filled(item) for item in value.values())
    return True


def _semantic_mapping(source: str, path: str) -> tuple[str, str, str, str, str]:
    if (source, path) in SOURCE_PATH_SEMANTIC_FIELDS:
        return SOURCE_PATH_SEMANTIC_FIELDS[(source, path)]
    if path in PATH_SEMANTIC_FIELDS:
        return PATH_SEMANTIC_FIELDS[path]
    root = path.split(".", 1)[0].removesuffix("[]")
    if root in SEMANTIC_FIELDS:
        return SEMANTIC_FIELDS[root]
    return (
        "especifico_fonte",
        "",
        "preservar_original",
        "revisar",
        "Sem equivalência nacional confirmada; revisar antes de adaptar.",
    )


def build_inventory(source: str, records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    records = list(records)
    total = len(records)
    paths: dict[str, dict[str, Any]] = {}
    for record in records:
        flattened = flatten_record(record)
        for path, values in flattened.items():
            info = paths.setdefault(path, {"types": set(), "filled": 0})
            filled_values = [value for value in values if is_filled(value)]
            if filled_values:
                info["filled"] += 1
                info["types"].update(infer_type(value) for value in filled_values)
    rows = []
    for path in sorted(paths):
        group, national, rule, include, note = _semantic_mapping(source, path)
        filled = paths[path]["filled"]
        rows.append(
            {
                "fonte": source,
                "campo_original": path,
                "tipos_observados": "|".join(sorted(paths[path]["types"])),
                "registros_fonte": total,
                "preenchidos": filled,
                "cobertura_percentual": f"{(100 * filled / total if total else 0):.6f}",
                "grupo_semantico": group,
                "campo_nacional": national,
                "regra_harmonizacao": rule,
                "incluir_formato_nacional": include,
                "observacao": note,
            }
        )
    return rows


def separate_bahia_sources(
    records: Iterable[dict[str, Any]], expected_total: int = 1959
) -> dict[str, list[dict[str, Any]]]:
    separated = {name: [] for name in sorted(BAHIA_SOURCE_NAMES.values())}
    records = list(records)
    if len(records) != expected_total:
        raise ValueError(
            f"contagem Bahia divergente: esperado {expected_total}, encontrado {len(records)}"
        )
    for index, record in enumerate(records):
        raw_source = record.get("fonte") if isinstance(record, dict) else None
        if raw_source not in BAHIA_SOURCE_NAMES:
            raise ValueError(
                f"fonte Bahia desconhecida no registro {index}: {raw_source!r}"
            )
        separated[BAHIA_SOURCE_NAMES[raw_source]].append(record)
    if sum(map(len, separated.values())) != expected_total:
        raise ValueError("separação Bahia duplicou ou omitiu registros")
    return separated


def validate_logical_counts(counts: dict[str, int]) -> None:
    if counts != EXPECTED_LOGICAL_COUNTS:
        raise ValueError(
            f"contagens lógicas divergentes: esperado {EXPECTED_LOGICAL_COUNTS}, encontrado {counts}"
        )
    if sum(counts.values()) != EXPECTED_RAW_TOTAL:
        raise ValueError("total lógico bruto não fecha em 8815")
    bahia_total = sum(counts[name] for name in BAHIA_SOURCE_NAMES.values())
    if bahia_total != 1959:
        raise ValueError(f"quatro fontes Bahia não fecham 1959: {bahia_total}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _records_for_input(name: str, payload: Any) -> list[dict[str, Any]]:
    if name == "bahia_v2":
        if not isinstance(payload, dict) or not isinstance(payload.get("terreiros"), list):
            raise ValueError("input bahia_v2 sem lista terreiros")
        return payload["terreiros"]
    if not isinstance(payload, list):
        raise ValueError(f"input {name} não é lista")
    return payload


def load_and_validate_inputs(
    manifest_path: Path,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = {entry["name"]: entry for entry in manifest.get("inputs", [])}
    sources: dict[str, list[dict[str, Any]]] = {}
    metadata = []
    for name in INPUT_NAMES:
        if name not in entries:
            raise ValueError(f"manifest sem input obrigatório: {name}")
        entry = entries[name]
        path = ROOT / entry["path"]
        actual_hash = _sha256(path)
        if actual_hash != entry["sha256"]:
            raise ValueError(f"hash divergente para {name}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = _records_for_input(name, payload)
        if len(records) != entry["count"]:
            raise ValueError(
                f"contagem divergente para {name}: esperado {entry['count']}, encontrado {len(records)}"
            )
        metadata.append(
            {
                "name": name,
                "path": entry["path"],
                "sha256": actual_hash,
                "count": len(records),
            }
        )
        if name == "bahia_v2":
            sources.update(separate_bahia_sources(records, entry["count"]))
        else:
            sources[name] = records
    counts = {name: len(sources[name]) for name in sorted(sources)}
    validate_logical_counts(counts)
    return sources, metadata


def build_coverage_document(
    rows: list[dict[str, Any]],
    source_counts: dict[str, int],
    input_metadata: list[dict[str, Any]],
    total_records: int,
) -> dict[str, Any]:
    rows = sorted(rows, key=lambda row: (row["fonte"], row["campo_original"]))
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    national: dict[str, dict[str, Any]] = {}
    for row in rows:
        by_source[row["fonte"]].append(
            {
                "campo_original": row["campo_original"],
                "tipos_observados": row["tipos_observados"].split("|") if row["tipos_observados"] else [],
                "preenchidos": row["preenchidos"],
                "cobertura_percentual": row["cobertura_percentual"],
            }
        )
        if row["campo_nacional"]:
            item = national.setdefault(
                row["campo_nacional"],
                {
                    "grupo_semantico": row["grupo_semantico"],
                    "contribuicoes_aprovadas": [],
                    "contribuicoes_pendentes": [],
                },
            )
            contribution = {
                "campo_original": row["campo_original"],
                "fonte": row["fonte"],
                "incluir_formato_nacional": row["incluir_formato_nacional"],
                "regra_harmonizacao": row["regra_harmonizacao"],
            }
            key = (
                "contribuicoes_aprovadas"
                if row["incluir_formato_nacional"] == "sim"
                else "contribuicoes_pendentes"
            )
            item[key].append(contribution)
    return {
        "metadados": {
            "versao": 3,
            "total_registros": total_records,
            "contagens_fontes": {name: source_counts[name] for name in sorted(source_counts)},
            "inputs": sorted(input_metadata, key=lambda item: item["name"]),
            "privacidade": "Somente nomes de campos, tipos, contagens, percentuais, hashes e mapeamentos; sem valores de registros.",
        },
        "politica_ausencia": {
            "valor_para_variavel_nao_coletada": None,
            "imputacao_silenciosa_permitida": False,
            "inferencia_exige_marcacao_explicita": True,
        },
        "fontes": {
            source: {
                "registros": source_counts[source],
                "quantidade_campos": len(by_source[source]),
                "campos": by_source[source],
            }
            for source in sorted(by_source)
        },
        "campos_nacionais_propostos": {
            field: {
                "grupo_semantico": national[field]["grupo_semantico"],
                "contribuicoes_aprovadas": national[field]["contribuicoes_aprovadas"],
                "contribuicoes_pendentes": national[field]["contribuicoes_pendentes"],
            }
            for field in sorted(national)
        },
    }


def write_outputs(
    rows: list[dict[str, Any]],
    coverage: dict[str, Any],
    csv_path: Path,
    json_path: Path,
) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows, key=lambda row: (row["fonte"], row["campo_original"]))
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(ordered)
    json_path.write_text(
        json.dumps(coverage, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run(manifest_path: Path, csv_path: Path, json_path: Path) -> dict[str, Any]:
    sources, metadata = load_and_validate_inputs(manifest_path)
    rows = [
        row
        for source in sorted(sources)
        for row in build_inventory(source, sources[source])
    ]
    counts = {source: len(records) for source, records in sorted(sources.items())}
    coverage = build_coverage_document(rows, counts, metadata, sum(counts.values()))
    write_outputs(rows, coverage, csv_path, json_path)
    return coverage


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    args = parser.parse_args()
    coverage = run(args.manifest, args.csv, args.json)
    counts = coverage["metadados"]["contagens_fontes"]
    print(json.dumps({"fontes": counts, "total": sum(counts.values())}, sort_keys=True))


if __name__ == "__main__":
    main()
