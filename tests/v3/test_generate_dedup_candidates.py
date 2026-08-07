import hashlib
import json
import os
from pathlib import Path

import pytest

from scripts.v3 import generate_dedup_candidates as generator


def record(
    key,
    *,
    source="mapeando_axe",
    name="Ilê Axé Exemplo",
    municipality: str | None = "Salvador",
    uf: str | None = "BA",
    lat=None,
    lon=None,
    cnpj=None,
    native_id=None,
    synthetic=False,
    raw=None,
):
    return {
        "source_record_key": key,
        "fonte": source,
        "id_fonte": native_id or key.split(":", 1)[1],
        "id_fonte_sintetico": synthetic,
        "nome_original": name,
        "localizacao_original": {
            "latitude": lat,
            "longitude": lon,
            "endereco": None,
            "municipio": municipality,
            "uf": uf,
            "cep": None,
            "precisao": None,
            "fonte_coordenada": None,
            "coordenadas_alternativas": [],
        },
        "identidade_religiosa_original": {
            "tradicao": None,
            "nacao": None,
            "denominacao": None,
        },
        "identificadores": {
            "cnpj": cnpj,
            "ceao_id": None,
            "osm_id": None,
            "google_place_id": None,
            "url": None,
        },
        "data_coleta": None,
        "flags_auditoria": {
            "baseline_atual": False,
            "exclusao_curada": False,
            "remocao_heuristica_legada": False,
            "ambiguo_pendente": False,
            "dedup_legado_recuperado": False,
        },
        "dados_originais": raw or {},
    }


def pairs(result):
    return result["candidate_pairs"]


def occurrence_ref(key):
    return hashlib.sha256(f"occurrence-ref-v1\0{key}".encode()).hexdigest()


def test_nome_exato_mesmo_municipio_e_apenas_candidato_manual():
    result = generator.generate_candidates(
        [record("mapeando_axe:a"), record("mapeando_axe:b")]
    )

    assert len(pairs(result)) == 1
    pair = pairs(result)[0]
    assert pair["suggested_relation"] == "possible_same_entity"
    assert pair["review_status"] == "pending"
    assert [item["type"] for item in pair["evidence"]] == ["exact_name"]
    assert pair["canonical_entity_created"] is False


def test_homonimos_em_geografias_diferentes_nao_viram_candidato():
    result = generator.generate_candidates(
        [
            record("mapeando_axe:a", municipality="Salvador", uf="BA"),
            record("mapeando_axe:b", municipality="Recife", uf="PE"),
        ]
    )

    assert pairs(result) == []
    assert result["metrics"]["geographic_homonym_pairs"] == 1


def test_cnpjs_diferentes_bloqueiam_fusao():
    result = generator.generate_candidates(
        [
            record("cnpj:a", source="cnpj", cnpj="05.419.205/0001-20"),
            record("cnpj:b", source="cnpj", cnpj="04.858.642/0001-87"),
        ]
    )

    pair = pairs(result)[0]
    assert pair["suggested_relation"] == "distinct_entities"
    assert pair["review_status"] == "rejected"
    assert pair["negative_evidence"] == [{"type": "different_cnpj"}]


def test_cnpj_igual_auto_linka_sem_remover_ocorrencias():
    result = generator.generate_candidates(
        [
            record("cnpj:a", source="cnpj", cnpj="05.419.205/0001-20"),
            record("outra:b", source="outra", cnpj="05.419.205/0001-20"),
        ]
    )

    pair = pairs(result)[0]
    assert pair["suggested_relation"] == "same_entity_same_location"
    assert pair["review_status"] == "auto_linked_strong_id"
    assert pair["evidence"][0]["type"] == "exact_cnpj"
    assert result["metrics"]["occurrences_preserved"] == 2


def test_id_nativo_igual_em_local_distinto_sugere_movimento():
    result = generator.generate_candidates(
        [
            record("ceao:a", source="ceao", native_id="forte-1", municipality="Salvador"),
            record("ceao:b", source="ceao", native_id="forte-1", municipality="Cachoeira"),
        ]
    )

    pair = pairs(result)[0]
    assert pair["suggested_relation"] == "possible_same_entity_moved"
    assert pair["review_status"] == "auto_linked_strong_id"
    assert {item["type"] for item in pair["negative_evidence"]} == {
        "different_municipality"
    }


def test_id_forte_com_conflito_de_cnpj_nao_auto_linka_registro_sem_cnpj():
    result = generator.generate_candidates(
        [
            record(
                "ceao:a",
                source="ceao",
                native_id="forte-1",
                cnpj="05.419.205/0001-20",
            ),
            record(
                "ceao:b",
                source="ceao",
                native_id="forte-1",
                cnpj="04.858.642/0001-87",
            ),
            record("ceao:c", source="ceao", native_id="forte-1", cnpj=None),
        ]
    )

    pair = next(
        item
        for item in pairs(result)
        if {item["left_occurrence_ref"], item["right_occurrence_ref"]}
        == {occurrence_ref("ceao:a"), occurrence_ref("ceao:c")}
    )
    assert pair["review_status"] == "pending"
    assert pair["suggested_relation"] == "unresolved"
    assert {item["type"] for item in pair["negative_evidence"]} == {
        "strong_id_conflict"
    }


def test_nome_exato_cross_source_sem_local_comparavel_fica_pendente():
    result = generator.generate_candidates(
        [
            record("ceao:a", source="ceao", municipality=None, uf=None),
            record("osm:b", source="osm", municipality=None, uf=None),
        ]
    )

    pair = pairs(result)[0]
    assert pair["suggested_relation"] == "unresolved"
    assert pair["review_status"] == "pending"


def test_proximidade_sem_nome_compativel_nao_emite_par():
    result = generator.generate_candidates(
        [
            record("mapeando_axe:a", name="Casa Um", lat=-12.0, lon=-38.0),
            record("mapeando_axe:b", name="Terreiro Dois", lat=-12.0, lon=-38.0),
        ]
    )

    assert pairs(result) == []


def test_nome_compativel_e_proximidade_auxiliar_mesclam_evidencias_e_colapso():
    records = [
        record(
            f"mapeando_axe:{suffix}",
            name=name,
            lat=None,
            lon=None,
            raw={"nominatim_lat": -12.0, "nominatim_lng": -38.0},
        )
        for suffix, name in (
            ("c", "Ile Axe Terreiro Modelo"),
            ("a", "Ilê Axé Terreiro Modelo"),
            ("b", "Ile Axe Terreiro Modelo BA"),
        )
    ]

    result = generator.generate_candidates(records)

    assert len(pairs(result)) == 3
    target = next(
        pair
        for pair in pairs(result)
        if {pair["left_occurrence_ref"], pair["right_occurrence_ref"]}
        == {occurrence_ref("mapeando_axe:a"), occurrence_ref("mapeando_axe:c")}
    )
    assert [item["type"] for item in target["evidence"]] == [
        "distance",
        "exact_name",
        "name_similarity",
    ]
    distance = target["evidence"][0]
    assert distance == {
        "type": "distance",
        "provenance": "derived_spatial_grid",
        "authority": "geocoder_auxiliary",
        "distance_bucket": "0-25m",
    }
    assert {item["type"] for item in target["negative_evidence"]} == {
        "collapsed_coordinate"
    }


def test_par_e_componente_sao_deterministicos_e_ordenados():
    left = record("mapeando_axe:z")
    right = record("mapeando_axe:a")

    first = generator.generate_candidates([left, right])
    second = generator.generate_candidates([right, left])

    assert pairs(first) == pairs(second)
    pair = pairs(first)[0]
    assert pair["left_occurrence_ref"] < pair["right_occurrence_ref"]
    expected_refs = sorted((occurrence_ref("mapeando_axe:a"), occurrence_ref("mapeando_axe:z")))
    expected = hashlib.sha256(
        f"dedup-candidate-v3\0{expected_refs[0]}\0{expected_refs[1]}".encode()
    ).hexdigest()
    assert pair["candidate_pair_key"] == f"dedupv3:{expected}"
    assert pair["candidate_component_key"].startswith("dedup-component-v3:")


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )
    path.write_text(content, encoding="utf-8")


def _integration_config(tmp_path, records):
    source = tmp_path / "source_records.jsonl"
    _write_jsonl(source, records)
    manifest = tmp_path / "source_records.manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "version": 3,
                "total": len(records),
                "counts": {"mapeando_axe": len(records)},
                "jsonl": {
                    "path": source.name,
                    "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    "bytes": source.stat().st_size,
                },
            }
        ),
        encoding="utf-8",
    )
    normalized = tmp_path / "exclusoes_curadas_v3.csv"
    normalized.write_text("stable_key,identity_synthetic,status\n", encoding="utf-8")
    original = tmp_path / "exclusoes_curadas.csv"
    original.write_text(
        "nome,municipio,endereco,fonte,latitude,longitude,motivo,status\n",
        encoding="utf-8",
    )
    repository_schemas = Path(__file__).resolve().parents[2] / "schemas"
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    for name in (
        "dedup-candidate-v3.schema.json",
        "source-record-v3.schema.json",
        "dedup-occurrence-status-v3.schema.json",
        "dedup-summary-v3.schema.json",
    ):
        (schema_dir / name).write_bytes((repository_schemas / name).read_bytes())
    return {
        "root": tmp_path,
        "candidate_schema_path": schema_dir / "dedup-candidate-v3.schema.json",
        "source_schema_path": schema_dir / "source-record-v3.schema.json",
        "status_schema_path": schema_dir / "dedup-occurrence-status-v3.schema.json",
        "summary_schema_path": schema_dir / "dedup-summary-v3.schema.json",
        "source_path": source,
        "source_manifest_path": manifest,
        "curated_ledger_path": normalized,
        "original_ledger_path": original,
        "candidate_output_path": tmp_path / "out" / "dedup_candidates.jsonl",
        "status_output_path": tmp_path / "out" / "dedup_occurrence_status.jsonl",
        "summary_output_path": tmp_path / "audit" / "dedup_candidates_summary.json",
    }


def test_build_publica_outputs_minimizados_e_preserva_todas_as_ocorrencias(tmp_path):
    config = _integration_config(
        tmp_path,
        [record("mapeando_axe:a"), record("mapeando_axe:b")],
    )

    summary = generator.build_dedup_candidates(**config)

    statuses = [
        json.loads(line)
        for line in config["status_output_path"].read_text(encoding="utf-8").splitlines()
    ]
    candidate_text = config["candidate_output_path"].read_text(encoding="utf-8")
    assert len(statuses) == 2
    assert set(statuses[0]) == {
        "occurrence_ref",
        "fonte",
        "exclusao_curada",
        "ledger_refs",
        "status",
    }
    assert summary["equations"]["occurrences_preserved"] == "2 = 2"
    assert summary["metric_change"]["candidate_pairs_before_d2"] == 567
    assert summary["metric_change"]["candidate_pairs_without_siafi_bridge"] == 352
    assert "SIAFI" in summary["metric_change"]["description"]
    for sensitive in ("nome_original", "dados_originais", "telefone", "latitude", "longitude", "Ilê Axé Exemplo"):
        assert sensitive not in candidate_text
        assert sensitive not in config["status_output_path"].read_text(encoding="utf-8")
        assert sensitive not in config["summary_output_path"].read_text(encoding="utf-8")


def test_hash_invalido_falha_sem_publicar(tmp_path):
    config = _integration_config(tmp_path, [record("mapeando_axe:a")])
    manifest = json.loads(config["source_manifest_path"].read_text(encoding="utf-8"))
    manifest["jsonl"]["sha256"] = "0" * 64
    config["source_manifest_path"].write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(generator.GenerationError, match="hash"):
        generator.build_dedup_candidates(**config)

    assert not config["candidate_output_path"].exists()
    assert not config["status_output_path"].exists()
    assert not config["summary_output_path"].exists()


def test_candidato_fora_do_schema_falha_antes_de_publicar(tmp_path, monkeypatch):
    config = _integration_config(
        tmp_path,
        [record("mapeando_axe:a"), record("mapeando_axe:b")],
    )
    real_generate = generator.generate_candidates

    def invalid(records, **kwargs):
        result = real_generate(records, **kwargs)
        result["candidate_pairs"][0]["nome_original"] = "valor proibido"
        return result

    monkeypatch.setattr(generator, "generate_candidates", invalid)

    with pytest.raises(generator.GenerationError, match="schema"):
        generator.build_dedup_candidates(**config)

    assert not config["candidate_output_path"].exists()
    assert not config["status_output_path"].exists()
    assert not config["summary_output_path"].exists()


def test_falha_antes_do_pointer_mantem_release_anterior_atual(tmp_path, monkeypatch):
    config = _integration_config(
        tmp_path,
        [record("mapeando_axe:a"), record("mapeando_axe:b")],
    )
    config["release_root_path"] = tmp_path / "data/processed/v3/dedup_releases"
    config["pointer_output_path"] = tmp_path / "data/processed/v3/dedup_current.json"
    config["pointer_output_path"].parent.mkdir(parents=True)
    config["pointer_output_path"].write_text('{"release_id":"anterior"}\n')
    before = config["pointer_output_path"].read_bytes()
    real_replace = os.replace
    failed = False

    def fail_pointer(source, destination):
        nonlocal failed
        if not failed and Path(destination) == config["pointer_output_path"] and ".tmp-" in Path(source).name:
            failed = True
            raise OSError("falha sintética")
        return real_replace(source, destination)

    monkeypatch.setattr(generator.os, "replace", fail_pointer)

    with pytest.raises(OSError, match="falha sintética"):
        generator.build_dedup_candidates(**config)

    assert config["pointer_output_path"].read_bytes() == before
    assert not list(tmp_path.rglob(".*.tmp-*"))
    assert not list(tmp_path.rglob(".*.bak-*"))


def municipality_index():
    return generator.MunicipalityIndex.from_rows(
        [
            {"codigo_ibge": "2927408", "codigo_siafi": "3849", "nome": "Salvador", "uf": "BA"},
            {"codigo_ibge": "2904902", "codigo_siafi": "3347", "nome": "Cachoeira", "uf": "BA"},
        ]
    )


def test_harmoniza_codigo_ibge_texto_e_alias_explicito_de_uf():
    result = generator.generate_candidates(
        [
            record(
                "cnpj:a",
                source="cnpj",
                municipality=None,
                uf="Bahia",
                raw={"codigo_municipio": "2927408"},
            ),
            record("mapeando_axe:b", municipality="Salvador", uf="BA"),
            record("mapeando_axe:c", municipality="Cachoeira", uf="Bahia"),
        ],
        municipality_index=municipality_index(),
    )

    emitted = {(item["left_source"], item["right_source"]) for item in pairs(result)}
    assert ("cnpj", "mapeando_axe") in emitted
    assert result["metrics"]["geographic_homonym_pairs"] == 2


def test_codigo_siafi_desconhecido_nao_infere_geografia_por_texto():
    index = municipality_index()
    coded = record(
        "cnpj:a",
        source="cnpj",
        municipality="Salvador",
        uf="BA",
        raw={"codigo_municipio": "9999"},
    )
    textual = record("mapeando_axe:b", municipality="Salvador", uf="BA")

    assert generator._municipality_key(coded, index) is None
    assert generator._geography_relation(coded, textual, index)[0] == "unknown"


def test_codigo_siafi_real_do_cnpj_harmoniza_com_ibge_completo():
    coded = record("cnpj:a", source="cnpj", municipality=None, uf="Bahia", raw={"codigo_municipio": "3849"})
    salvador = record("mapeando_axe:b", municipality="Salvador", uf="BA")
    cachoeira = record("mapeando_axe:c", municipality="Cachoeira", uf="BA")

    assert generator._municipality_key(coded, municipality_index()) == ("2927408", "BA")
    assert generator._geography_relation(coded, salvador, municipality_index())[0] == "same"
    assert generator._geography_relation(coded, cachoeira, municipality_index()) == (
        "different",
        ["different_municipality"],
    )


def test_normalizacao_preserva_unicode_nao_latino_e_remove_so_marcas():
    assert generator._normalize("Ação, ÇA!") == "acao ca"
    assert generator._normalize("宗教・寺") == "宗教 寺"


def test_400_placeholders_nao_geram_pares_nominais_e_contagem_e_linear():
    records = [record(f"mapeando_axe:{index}", name="Terreiro sem nome") for index in range(400)]

    result = generator.generate_candidates(records, municipality_index=municipality_index())

    assert pairs(result) == []
    assert result["metrics"]["placeholder_name_records"] == 400
    assert result["metrics"]["name_pair_comparisons"] == 0


def test_grupo_nominal_adversarial_e_agregado_sem_materializar_quadratico():
    records = [record(f"mapeando_axe:{index}", name="Casa Adversarial") for index in range(400)]

    result = generator.generate_candidates(
        records,
        municipality_index=municipality_index(),
        max_name_bucket=50,
    )

    assert pairs(result) == []
    assert result["metrics"]["oversized_name_groups"] == 1
    assert result["metrics"]["oversized_name_theoretical_pairs"] == 79_800
    assert result["metrics"]["name_pair_comparisons"] == 0


def test_grupo_de_id_forte_acima_do_limite_falha_como_anomalia():
    records = [
        record(f"ceao:{index}", source="ceao", native_id="repetido")
        for index in range(11)
    ]

    with pytest.raises(generator.GenerationError, match="grupo de ID forte"):
        generator.generate_candidates(records, max_strong_group=10)


def test_id_forte_com_local_desconhecido_nao_afirma_mesmo_local():
    result = generator.generate_candidates(
        [
            record("ceao:a", source="ceao", native_id="forte", municipality=None, uf=None),
            record("ceao:b", source="ceao", native_id="forte", municipality=None, uf=None),
        ]
    )

    pair = pairs(result)[0]
    assert pair["suggested_relation"] == "possible_same_entity"
    assert pair["review_status"] == "auto_linked_strong_id"


def test_refs_opacas_componentes_por_par_e_rejeitado_nao_conecta_transitivamente():
    result = generator.generate_candidates(
        [
            record("ceao:email@x.test+5511999999999", source="ceao", native_id="x", cnpj="05.419.205/0001-20"),
            record("ceao:b", source="ceao", native_id="x", cnpj="04.858.642/0001-87"),
            record("ceao:c", source="ceao", native_id="x"),
        ]
    )

    serialized = json.dumps(result, sort_keys=True)
    assert "email@x.test" not in serialized
    assert "+5511999999999" not in serialized
    assert all(set(item) == {
        "candidate_pair_key", "left_occurrence_ref", "right_occurrence_ref",
        "left_source", "right_source", "evidence", "negative_evidence",
        "suggested_relation", "review_status", "candidate_component_key",
        "conflicting_pair_keys", "canonical_entity_created",
    } for item in pairs(result))
    assert len({item["candidate_component_key"] for item in pairs(result)}) == len(pairs(result))


def test_input_invalido_por_schema_falha_antes_de_gerar(tmp_path, monkeypatch):
    invalid = record("mapeando_axe:a")
    invalid["id_fonte_sintetico"] = 1
    config = _integration_config(tmp_path, [invalid])
    called = False

    def should_not_generate(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("não deveria gerar")

    monkeypatch.setattr(generator, "generate_candidates", should_not_generate)
    with pytest.raises(generator.GenerationError, match="source-record"):
        generator.build_dedup_candidates(**config)
    assert called is False
