#!/usr/bin/env python3
"""Recuperação sequencial auditável dos CNPJ restantes da v4.9 candidata.

A lista de 2.442 registros CNPJ na v3 preserva, como subsequência, a
ordem dos 2.673 registros no CSV original. Somente atribui nomes quando
o alinhamento progressivo e regressivo de CEP concorda no MESMO registro.
Usar depois de build_v4_9_nomes.py e completar_nomes_v49_correspondencia.py.
Não altera nenhuma base publicada, não corrige coordenadas e não deduplica.
"""
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "v4_9_candidata"
SRC = DATA / "cnpj" / "geocoding" / "terreiros_cnpj_geocoded.csv"
GEO = OUT / "terreiros_nacional_v4_9_candidata.geojson"
AUDIT = OUT / "antes_depois_1238.csv"
PENDING = OUT / "pendencias_sem_chave.csv"
DEST = OUT / "destino_537.csv"
REPORT = OUT / "auditoria_recuperacao.json"
RECOVERED178 = OUT / "recuperacao_sequencial_178.csv"
OUTRO = OUT / "identidade_sem_nome_oficial_mapeando_axe_130.json"

def loadcsv(path):
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))

def _hash(x, n=12):
    """Referência não reversível para CNPJ/CEP: a política do projeto não
    publica identificadores, mas a auditoria precisa reencontrar o registro."""
    import hashlib
    limpo = "".join(c for c in str(x or "") if c.isdigit())
    return hashlib.sha256(limpo.encode()).hexdigest()[:n]

def savecsv(path, rows, columns):
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

def cep(s):
    return "".join(c for c in str(s or "") if c.isdigit())

def norm(s):
    return str(s or "").strip().casefold()

def coordinates_match(feature, source):
    if not source.get("lat") or not source.get("lng"):
        return False
    lon, lat = feature["geometry"]["coordinates"][:2]
    return abs(lon-float(source["lng"]))<1e-5 and abs(lat-float(source["lat"]))<1e-5

def main():
    v3 = json.loads((DATA / "terreiros_nacional_v3.geojson").read_text(encoding="utf-8"))["features"]
    sources = loadcsv(SRC)
    candidate = json.loads(GEO.read_text(encoding="utf-8"))
    audit = loadcsv(AUDIT)
    pending = loadcsv(PENDING)
    dest = loadcsv(DEST)
    assert len(v3) == 7755 and len(sources) == 2673
    block = v3[1271:3713]
    assert len(block) == 2442 and all(f["properties"].get("fonte_label") == "CNPJ" for f in block)
    assert len(candidate["features"]) == 8573

    # Reconstrói o alinhamento em ambas as direções, independentemente.
    forward = []
    j = 0
    for f in block:
        target = cep(f["properties"].get("cep"))
        while j < len(sources) and cep(sources[j].get("cep")) != target:
            j += 1
        assert j < len(sources), "CNPJ v3 não é subsequência da fonte: rejeitado"
        forward.append(j)
        j += 1
    reverse = [None] * len(block)
    j = len(sources) - 1
    for i in range(len(block) - 1, -1, -1):
        target = cep(block[i]["properties"].get("cep"))
        while j >= 0 and cep(sources[j].get("cep")) != target:
            j -= 1
        assert j >= 0, "Falha no alinhamento reverso"
        reverse[i] = j
        j -= 1

    assert sum(a == b for a,b in zip(forward, reverse)) == 2440
    assert sum(a != b for a,b in zip(forward, reverse)) == 2
    named = [(i, f) for i,f in enumerate(block) if f["properties"].get("nome") != "Sem nome"]
    assert len(named) == 1205
    # Controle cego: 1.203+ nomes já conhecidos nos registros unívocos
    # têm de coincidir literalmente com o nome original da fonte.
    known_unique = 0
    for i,f in named:
        if forward[i] != reverse[i]:
            continue
        s = sources[forward[i]]
        n = norm(f["properties"]["nome"])
        assert n in {norm(s.get("razao_social")),norm(s.get("nome_fantasia"))}, (
            "Nome conhecido diverge da fonte", i + 1271, n, s.get("razao_social"))
        known_unique += 1
    assert known_unique >= 1203

    ref = {int(f["properties"]["indice_v3"]):f for f in candidate["features"]
           if f["properties"].get("indice_v3") is not None}
    assert len(ref) == 1237

    remaining = [x for x in pending if x["fonte"] == "CNPJ"]
    assert len(remaining) == 178
    restored, generated = {}, []
    for r in remaining:
        idx = int(r["indice_v3_zero_based"])
        assert 1271 <= idx < 3713
        i = idx - 1271
        assert forward[i] == reverse[i], f"CEP ambíguo na sequência: v3 {idx}"
        s = sources[forward[i]]
        name = (s.get("razao_social") or s.get("nome_fantasia") or "").strip()
        assert name and not name.lower().startswith("(sem filtro"), idx
        assert norm(ref[idx]["properties"]["nome"]) == "sem nome"
        restored[idx] = (name, s)
        p = ref[idx]["properties"]
        p.update({
            "nome":name, "recuperacao_status":"recuperado_fonte_cnpj",
            "recuperacao_metodo":"alinhamento_sequencial_bidirecional_cep",
            "fonte_nome_recuperado":"data/cnpj/geocoding/terreiros_cnpj_geocoded.csv",
            "cnpj_ref_sha256":_hash(s["cnpj"]),
            "uf_fonte_cnpj":s["uf"],
            "uf_divergente_fonte":s["uf"] != p.get("uf"),
            "coordenada_divergente_fonte":not coordinates_match(v3[idx],s),
            "validacao_comunitaria":"pendente"
        })
        generated.append({
            "indice_v3_zero_based":idx,"indice_csv_fonte_zero_based":forward[i],
            "cnpj_sha256":_hash(s["cnpj"]),"cep_sha256":_hash(s["cep"]),"nome_recuperado":name,
            "uf_v3":v3[idx]["properties"].get("uf"),"uf_fonte":s["uf"],
            "coordenadas_concordantes":str(coordinates_match(v3[idx],s)).lower(),
            "metodo":"subsequencia_CNPJ_CEP_ordem_original_bidirecional"
        })
    assert len(restored) == 178 and len({s["cnpj"] for _,s in restored.values()}) == 178
    assert sum(x["coordenadas_concordantes"] == "true" for x in generated) == 81

    oldCols = list(audit[0])
    for x in audit:
        idx = int(x["indice_v3_zero_based"])
        if idx in restored:
            name,s = restored[idx]
            x.update({
                "nome_depois":name,"status":"RECUPERADO",
                "motivo":"Correspondência única por subsequência CEP bidirecional dos 2.442 CNPJ v3 em 2.673 registros de origem",
                "uf_fonte_cnpj":s["uf"],
                "origem_prova":"data/cnpj/geocoding/terreiros_cnpj_geocoded.csv",
                "corroborado_unified":"alinhamento_original"
            })
    assert sum(x["status"]=="RECUPERADO" and x["fonte"]=="CNPJ" for x in audit)==1237

    pending = [r for r in pending if int(r["indice_v3_zero_based"]) not in restored]
    assert len(pending)==1 and pending[0]["fonte"]=="Outro" and pending[0]["indice_v3_zero_based"]=="7488"
    pending[0]["motivo"]="Origem Mapeando Axé 2010 id 130 contém nome vazio; liderança identificada, nome da casa não fornecido"

    # Última ocorrência: a fonte original nomeia a liderança, mas o nome da
    # casa está literalmente vazio. Preservamos a distinção e NÃO inventamos.
    other_matches = [x for x in candidate["features"] if
                     x["properties"].get("nome")=="Sem nome" and
                     x["properties"].get("fonte_label")=="Mapeando Axé (CSV)" and
                     x["geometry"]["coordinates"]==[-48.5530148,-1.2455034]]
    assert len(other_matches)==1
    other = other_matches[0]["properties"]
    other.update({
        "source_record_id":"130","fonte_identidade":"mapeando_axe_2010",
        "tem_lideranca_documentada":True,
        "nome_oficial":"nao_consta_na_fonte",
        "identificacao_descritiva":"Registro 130 do Mapeando Axé; nomes de liderança e endereço original não publicados (política de privacidade do projeto)",
        "recuperacao_status":"pendente_nome_oficial",
        "revisao_geografica_pendente":True,
        "nome_original_v3":"Sem nome"
    })
    lastAudit = [x for x in audit if x["indice_v3_zero_based"]=="7488"]
    assert len(lastAudit)==1
    lastAudit[0]["motivo"]="Fonte original Mapeando Axé 2010 (registro 130) sem nome da casa; liderança documentada, não publicada por política de privacidade"

    for r in dest:
        a=ref[int(r["indice_v3_agrupado"])]["properties"]
        b=ref[int(r["indice_v3_representante"])]["properties"]
        r["nome_agrupado_recuperado"]=a["nome"] if a["nome"]!="Sem nome" else ""
        r["nome_representante_recuperado"]=b["nome"] if b["nome"]!="Sem nome" else ""
        r["mesmo_nome_comprovado"]="false"
    assert len(dest)==537
    assert all(r["nome_agrupado_recuperado"] for r in dest)

    rec=[x for x in ref.values() if x["properties"].get("recuperacao_status")=="recuperado_fonte_cnpj"]
    pend_cnpj=[x for x in ref.values() if x["properties"].get("recuperacao_status")=="pendente_revisao"]
    assert len(rec)==1237 and not pend_cnpj
    assert len({x["properties"]["entity_id"] for x in ref.values()})==1237

    report=json.loads(REPORT.read_text(encoding="utf-8"))
    report.update({
        "cnpj_nomes_recuperados":1237, "cnpj_pendentes":0,
        "pendencias_escopo_total":1,
        "terceira_passagem_alinhamento_sequencial":178,
        "terceira_passagem_controles_ja_nomeados":known_unique,
        "terceira_passagem_cnpj_ordem_unica":2440,
        "terceira_passagem_cnpj_ordem_ambigua":2,
        "terceira_passagem_coordenadas_concordantes":81,
        "terceira_passagem_coordenadas_divergentes":97,
        "uf_divergente_com_fonte":sum(bool(x["properties"].get("uf_divergente_fonte")) for x in rec),
        "n_recuperados_entre_537":537,"n_pendentes_entre_537":0,
        "n_grupos_com_dois_nomes_recuperados_diferentes":sum(bool(r["nome_agrupado_recuperado"]) and bool(r["nome_representante_recuperado"]) and r["nome_agrupado_recuperado"]!=r["nome_representante_recuperado"] for r in dest),
        "ultimo_registro_sem_nome_oficial":{"indice_v3":7488,"fonte":"mapeando_axe_2010",
          "id_fonte":"130","nome_na_fonte":"", "lideranca_nome_omitido":True},
        "ressalva":"1.237 nomes CNPJ documentais candidatos. Um registro de outra fonte sem nome oficial; não inventar nome. 97 coordenadas de terceira passagem divergentes, preservar local original e revisar antes da publicação."
    })
    candidate["metadata"].update({
        "nomes_recuperados":1237,"pendencias_cnpj":0,
        "terceira_passagem_recuperados":178,
        "pendencias_nome_nao_informado_outras_fontes":1,
        "nao_publicar_sem_revisao":True
    })
    # Todas as verificações ocorreram antes da escrita.
    GEO.write_text(json.dumps(candidate,ensure_ascii=False),encoding="utf-8")
    savecsv(AUDIT,audit,oldCols)
    savecsv(PENDING,pending,list(pending[0]))
    savecsv(DEST,dest,list(dest[0]))
    savecsv(RECOVERED178,generated,list(generated[0]))
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    OUTRO.write_text(json.dumps({
        "indice_v3":7488,"source_record_id":"130","fonte":"mapeando_axe_2010",
        "source_url":"https://www.mapeandoaxe.org.br/cd/paginas/terreiros.htm",
        "nome_na_fonte":"","tem_lideranca_documentada":True,
        "nota_privacidade":"Nomes de liderança e endereço original omitidos por política de privacidade do projeto; consulta interna ao registro 130 da fonte.",
        "coordenadas_v3":[-48.5530148,-1.2455034],
        "coordenada_endereco":"Divergencia potencial: fonte geocodificou rua em Outeiro, endereço menciona Cotijuba",
        "status":"Identidade da fonte rastreada; nome do terreiro nao declarado, requer pesquisa comunitaria",
        "nao_inventar_nome":True
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"VALIDADO: {len(candidate['features'])} pontos; 1237 CNPJ nomeados; 0 CNPJ pendentes; 1 casa sem nome oficial na fonte; {known_unique} controles conhecidos")

if __name__=="__main__":
    main()
