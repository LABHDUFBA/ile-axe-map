#!/usr/bin/env python3
"""Reconstroi a v4.9 candidata sem alterar as bases publicadas.
Uso: python3 scripts/build_v4_9_nomes.py
Requer Python 3 e os arquivos de origem rastreados em Git.
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

BASE=Path(__file__).resolve().parent.parent
DATA=BASE/"data"
OUT=DATA/"v4_9_candidata"
OUT.mkdir(parents=True,exist_ok=True)

def readgeo(path):
    return json.loads(path.read_text(encoding="utf-8"))["features"]

def cep(x):
    return "".join(c for c in str(x or "") if c.isdigit())

def _hash(x, n=12):
    """Referência não reversível para CEP/CNPJ: a política do projeto não
    publica identificadores, mas a auditoria precisa reencontrar o registro."""
    import hashlib
    return hashlib.sha256(cep(x).encode()).hexdigest()[:n]

def hav(a,b):
    import math
    ax,ay=a["geometry"]["coordinates"]
    bx,by=b["geometry"]["coordinates"]
    p,q=map(math.radians,(ay,by))
    dy=math.radians(by-ay);dx=math.radians(bx-ax)
    return 12742000*math.asin(math.sqrt(math.sin(dy/2)**2+math.cos(p)*math.cos(q)*math.sin(dx/2)**2))

def run():
    v3=readgeo(DATA/"terreiros_nacional_v3.geojson")
    v48=readgeo(DATA/"v4_8"/"terreiros_nacional_v4_8.geojson")
    with (DATA/"cnpj"/"geocoding"/"terreiros_cnpj_geocoded.csv").open(encoding="utf-8",newline="") as f:
        sources=list(csv.DictReader(f))
    with (DATA/"unified"/"terreiros_unified.csv").open(encoding="utf-8",newline="") as f:
        uni=[x for x in csv.DictReader(f) if x["source"]=="receita_federal_cnpj"]
    bycep=defaultdict(list); byuni=defaultdict(list)
    for x in sources:bycep[cep(x["cep"])].append(x)
    for x in uni:byuni[cep(x["cep"])].append(x)
    all_exact=[(i,f) for i,f in enumerate(v3) if f["properties"].get("nome")=="Sem nome"]
    targets=[(i,f) for i,f in all_exact if f["properties"].get("fonte_label")=="CNPJ"]
    counts=Counter(cep(f["properties"].get("cep")) for _,f in targets)
    assert len(v3)==7755 and len(v48)==8036 and len(all_exact)==1238 and len(targets)==1237
    groups=[];representatives={}
    for i,f in targets:
        found=next((x for x in groups if x[1]["properties"]["uf"]==f["properties"]["uf"] and hav(x[1],f)<=500),None)
        if found is None:groups.append((i,f));representatives[i]=i
        else:representatives[i]=found[0]
    assert len(groups)==700 and sum(i!=k for i,k in representatives.items())==537
    audit_by_index={}
    for i,f in targets:
        p=f["properties"];key=cep(p.get("cep"));items=bycep[key];cross=byuni[key]
        why=None;name=None;source=None
        if counts[key]!=1:why="CEP repetido entre registros sem nome da v3"
        elif len(items)!=1:why="CEP nao identifica um unico registro no CSV CNPJ"
        else:
            source=items[0];coords=f["geometry"]["coordinates"]
            if not source.get("lng") or not source.get("lat") or abs(float(source["lng"])-coords[0])>1e-5 or abs(float(source["lat"])-coords[1])>1e-5:
                why="coordenadas divergentes da fonte CNPJ"
            else:
                name=(source.get("razao_social") or source.get("nome_fantasia") or "").strip()
                if not name:why="fonte CNPJ sem nome"
                elif any(x["cnpj"]!=source["cnpj"] and x["nome"]!=name for x in cross):
                    why="fontes CNPJ conflitantes"
        if why:name=None
        audit_by_index[i]=(name,source if name else None,why)
    assert sum(bool(x[0]) for x in audit_by_index.values())==1016
    kept=[f for f in v48 if not (f["properties"].get("nome")=="Sem nome" and f["properties"].get("fonte_label")=="CNPJ/Receita Federal")]
    assert len(kept)==7336
    generated=[]
    for i,f in targets:
        p=f["properties"];name,source,why=audit_by_index[i]
        props={
            "entity_id":f"rec_cnpj_v3_{i:06d}",
            "nome":name or "Sem nome",
            "municipio":p.get("municipio") or "",
            "uf":p.get("uf") or "",
            "fontes":["receita_federal_cnpj"],
            "num_fontes":1,
            "coord_origin":p.get("geo_source") or "csv",
            "geo_status":p.get("geo_status") or "csv",
            "fonte_label":"CNPJ/Receita Federal",
            "nacao":p.get("nacao") or None,
            "categoria":p.get("categoria") or "Não informado",
            "endereco":p.get("endereco") or "",
            "cep_ref_sha256":_hash(p.get("cep")),
            "linha_religiosa":None,
            "match_axecloud":"nao_verificado",
            "versao":"v4.9_candidata",
            "tradicao":p.get("tradicao") or "Não especificada",
            "tradicoes_adicionais":[],"nacoes":[],"raiz":None,"linhas":[],"pratica":None,"cruzamento":False,
            "classificacao_origem":"herdada_v3_nao_reinferida",
            "indice_v3":i,
            "entity_id_anterior":"e_5f460de11578_"+(p.get("uf") or "XX"),
            "representante_grupo_v4_original":representatives[i],
            "nome_original_v3":p["nome"],
            "recuperacao_status":"recuperado_fonte_cnpj" if name else "pendente_revisao",
            "uf_fonte_cnpj":source["uf"] if source else None,
            "uf_divergente_fonte":bool(source and source["uf"]!=p["uf"]),
            "fonte_nome_recuperado":"data/cnpj/geocoding/terreiros_cnpj_geocoded.csv" if name else None,
        }
        generated.append({"type":"Feature","geometry":f["geometry"],"properties":props})
    result={"type":"FeatureCollection","metadata":{
        "versao":"v4.9_candidata","base_v4_8":"a9b909230013ce37b24a0c91ebf617fabe7b102b",
        "total_v4_8":8036,"placeholder_v4_removido":700,
        "cnpj_ocorrencias_restauradas":1237,"nomes_recuperados":1016,"pendencias_cnpj":221,
        "nao_publicar_sem_revisao":True,
    },"features":kept+generated}
    assert len(result["features"])==8573
    assert len(set(x["properties"]["entity_id"] for x in generated))==1237
    target=OUT/"terreiros_nacional_v4_9_candidata.geojson"
    target.write_text(json.dumps(result,ensure_ascii=False),encoding="utf-8")
    print(f"OK: {target} — 8573 pontos; 1016 nomes recuperados; 221 CNPJ pendentes; 537 agrupamentos revertidos")
if __name__=="__main__":run()
