#!/usr/bin/env python3
"""Segunda passagem conservadora dos nomes CNPJ na candidata v4.9.

Apenas correspondências em que (CEP, latitude, longitude) é exclusivo
em TODOS os registros CNPJ v3 e na fonte CNPJ, com verificação de conflito
no CSV unificado. Não altera v3, v4.8, main ou o mapa público.
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
OUT = DATA / "v4_9_candidata"
SRC_PATH = DATA / "cnpj" / "geocoding" / "terreiros_cnpj_geocoded.csv"
UNIFIED_PATH = DATA / "unified" / "terreiros_unified.csv"
GEO_PATH = OUT / "terreiros_nacional_v4_9_candidata.geojson"

def readcsv(p):
    with p.open("r", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))

def _hash(x, n=12):
    """Referência não reversível: a política do projeto não publica CNPJ/CEP,
    mas a auditoria precisa reencontrar o registro na fonte."""
    import hashlib
    limpo = "".join(c for c in str(x or "") if c.isdigit())
    return hashlib.sha256(limpo.encode()).hexdigest()[:n]

def writecsv(p, rows, columns):
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(p)

def digits(x):
    return "".join(c for c in str(x or "") if c.isdigit())

def same_coords(point, source):
    if not source.get("lat") or not source.get("lng"):
        return False
    coords = point["geometry"]["coordinates"]
    return abs(float(source["lat"]) - coords[1]) < 1e-5 and abs(float(source["lng"]) - coords[0]) < 1e-5

def main():
    v3 = json.loads((DATA / "terreiros_nacional_v3.geojson").read_text(encoding="utf-8"))["features"]
    candidate = json.loads(GEO_PATH.read_text(encoding="utf-8"))
    sources = readcsv(SRC_PATH)
    unified = [x for x in readcsv(UNIFIED_PATH) if x["source"] == "receita_federal_cnpj"]
    indexed = {f["properties"]["indice_v3"]: f for f in candidate["features"]
               if f["properties"].get("indice_v3") is not None}

    targets = [(i, f) for i, f in enumerate(v3)
               if f["properties"].get("nome") == "Sem nome" and f["properties"].get("fonte_label") == "CNPJ"]
    all_v3_cnpj = [(i, f) for i, f in enumerate(v3)
                   if f["properties"].get("fonte_label") == "CNPJ"]
    counts = Counter(digits(f["properties"].get("cep")) for _, f in targets)
    bycep, byuni, byv3 = defaultdict(list), defaultdict(list), defaultdict(list)
    for s in sources:
        bycep[digits(s.get("cep"))].append(s)
    for s in unified:
        byuni[digits(s.get("cep"))].append(s)
    for i, f in all_v3_cnpj:
        byv3[digits(f["properties"].get("cep"))].append((i, f))

    assert len(v3) == 7755 and len(targets) == 1237 and len(indexed) == 1237
    added = {}
    for i, f in targets:
        key = digits(f["properties"].get("cep"))
        pool = bycep[key]
        # A primeira passagem já cuidou dos CEPs unívocos.
        if counts[key] == 1 and len(pool) == 1:
            continue
        exact = [s for s in pool if same_coords(f, s)]
        matching_v3 = [(j, old) for j, old in byv3[key]
                       if abs(old["geometry"]["coordinates"][0] - f["geometry"]["coordinates"][0]) < 1e-5
                       and abs(old["geometry"]["coordinates"][1] - f["geometry"]["coordinates"][1]) < 1e-5]
        if len(exact) != 1 or len(matching_v3) != 1 or matching_v3[0][0] != i:
            continue
        source = exact[0]
        name = (source.get("razao_social") or source.get("nome_fantasia") or "").strip()
        if not name or name.lower().startswith("(sem filtro"):
            continue
        conflicts = [s for s in byuni[key]
                     if same_coords(f, s)
                     and s.get("cnpj") != source.get("cnpj") and s.get("nome") != name]
        if conflicts:
            continue
        if indexed[i]["properties"].get("recuperacao_status") not in ("pendente_revisao", "recuperado_fonte_cnpj"):
            continue
        added[i] = (name, source, any(s.get("cnpj") == source.get("cnpj") for s in byuni[key]))

    # Travar mudança inesperada na base de referência e revisar o método.
    assert len(added) == 43, f"Esperados 43 candidatos exclusivos, obtidos {len(added)}"
    assert sum(v3[i]["properties"].get("uf") != s.get("uf") for i, (_, s, _) in added.items()) == 5

    for i, (name, source, corroborated) in added.items():
        p = indexed[i]["properties"]
        p.update({
            "nome": name,
            "recuperacao_status": "recuperado_fonte_cnpj",
            "recuperacao_metodo": "cep_e_coordenada_exclusivos_segunda_passagem",
            "uf_fonte_cnpj": source.get("uf"),
            "uf_divergente_fonte": source.get("uf") != p.get("uf"),
            "fonte_nome_recuperado": "data/cnpj/geocoding/terreiros_cnpj_geocoded.csv",
            "cnpj_ref_sha256": _hash(source.get("cnpj")),
            "validacao_comunitaria": "pendente"
        })

    rec = [f for f in indexed.values() if f["properties"].get("recuperacao_status") == "recuperado_fonte_cnpj"]
    pend = [f for f in indexed.values() if f["properties"].get("recuperacao_status") == "pendente_revisao"]
    assert (len(rec), len(pend)) == (1059, 178), (len(rec), len(pend))
    assert len(candidate["features"]) == 8573

    before_path = OUT / "antes_depois_1238.csv"
    before = readcsv(before_path)
    before_cols = list(before[0].keys())
    for row in before:
        idx = int(row["indice_v3_zero_based"])
        if idx in added:
            name, source, corroborated = added[idx]
            row.update({
                "nome_depois": name, "status": "RECUPERADO",
                "motivo": "CEP e coordenadas exclusivos na fonte e em todos os CNPJ v3; CEP isoladamente nao era unico",
                "origem_prova": "data/cnpj/geocoding/terreiros_cnpj_geocoded.csv",
                "corroborado_unified": str(corroborated).lower(),
                "uf_fonte_cnpj": source.get("uf", "")
            })

    pending_path = OUT / "pendencias_sem_chave.csv"
    pending = [row for row in readcsv(pending_path)
               if int(row["indice_v3_zero_based"]) not in added]
    pending_cols = list(readcsv(pending_path)[0].keys())
    assert len(pending) == 179, len(pending)

    dest_path = OUT / "destino_537.csv"
    dest = readcsv(dest_path)
    dest_cols = list(dest[0].keys())
    for row in dest:
        grouped = indexed[int(row["indice_v3_agrupado"])]["properties"]
        representative = indexed[int(row["indice_v3_representante"])]["properties"]
        row["nome_agrupado_recuperado"] = grouped["nome"] if grouped["nome"] != "Sem nome" else ""
        row["nome_representante_recuperado"] = representative["nome"] if representative["nome"] != "Sem nome" else ""
        # Igualdade textual não comprova que dois pontos sejam a mesma casa.
        row["mesmo_nome_comprovado"] = "false"
    assert len(dest) == 537

    audit_path = OUT / "auditoria_recuperacao.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    audit.update({
        "cnpj_nomes_recuperados": len(rec),
        "cnpj_pendentes": len(pend),
        "pendencias_escopo_total": len(pending),
        "segunda_passagem_ceps_repetidos_coordenadas_exclusivas": 43,
        "segunda_passagem_ufs_divergentes": 5,
        "uf_divergente_com_fonte": sum(bool(f["properties"].get("uf_divergente_fonte")) for f in rec),
        "n_recuperados_entre_537": sum(bool(row["nome_agrupado_recuperado"]) for row in dest),
        "n_pendentes_entre_537": sum(not bool(row["nome_agrupado_recuperado"]) for row in dest),
        "n_grupos_com_dois_nomes_recuperados_diferentes": sum(
            bool(row["nome_agrupado_recuperado"]) and bool(row["nome_representante_recuperado"])
            and row["nome_agrupado_recuperado"] != row["nome_representante_recuperado"] for row in dest),
        "criterio_segunda_passagem": "CEP + coordenadas exatas, correspondencia exclusiva em todas as feicoes CNPJ v3 e na fonte geocodificada, sem conflito com CSV unificado",
        "ressalva": "Correspondencia documental candidata, nao equivale a validacao comunitaria. Nao publicar sem revisao de UF e geografia."
    })
    candidate["metadata"].update({
        "nomes_recuperados": len(rec), "pendencias_cnpj": len(pend),
        "segunda_passagem_recuperados": 43, "nao_publicar_sem_revisao": True
    })

    GEO_PATH.write_text(json.dumps(candidate, ensure_ascii=False), encoding="utf-8")
    writecsv(before_path, before, before_cols)
    writecsv(pending_path, pending, pending_cols)
    writecsv(dest_path, dest, dest_cols)
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"VALIDADO: 8573 feicoes, {len(rec)} nomes, {len(pend)} CNPJ sem nome, {len(pending)} pendencias totais, 537 registros reconstituidos")

if __name__ == "__main__":
    main()
