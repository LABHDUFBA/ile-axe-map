#!/usr/bin/env python3
"""Classifica candidatos CNPJ nacionais sem incorporá-los ao mapa.

O bruto é uma base de RECUPERAÇÃO. Esta triagem atribui evidência textual e
situação cadastral, preservando todos os candidatos para revisão posterior.
Saídas sanitizadas: não carregam CNPJ, e-mail, telefone nem endereço completo.
"""
import csv
import json
import re
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
INP = BASE / "data" / "cnpj_nacional" / "terreiros_cnpj_nacional.csv"
OUT = BASE / "data" / "cnpj_nacional" / "triagem"
OUT.mkdir(exist_ok=True)

PATTERNS = {
    "candomble": r"\bcandombl\w*\b", "umbanda": r"\bumbanda\b", "terreiro": r"\bterreiro\b",
    "ile_axe": r"\bil[eê]\s+ax[eé]\b", "axe_de": r"\bax[eé]\s+de\b", "orixa": r"\borix[áa]s?\b",
    "batuque": r"\bbatuque\b", "jurema": r"\bjurema\b", "tambor_mina": r"\btambor\s+de\s+min[áa]\b",
    "babalorixa": r"\bbabalorix\w*\b", "ialorixa": r"\bialorix\w*\b", "casa_orixas": r"\bcasa\s+de\s+orix\w*\b",
    "macumba": r"\bmacumba\b", "quimbanda": r"\bquimbanda\b", "catimbo": r"\bcatimb[óo]\b",
    "nzo": r"\bnzo\b", "egun": r"\begun(?:gun)?\b", "vodu": r"\bvodu\b",
}
RX = {k: re.compile(v, re.I) for k, v in PATTERNS.items()}
CORE = {"candomble", "umbanda", "terreiro", "ile_axe", "tambor_mina", "babalorixa", "ialorixa", "casa_orixas", "quimbanda", "nzo"}
CONTEXT = set(PATTERNS) - CORE
RELIGIOUS_CNAE = "9491000"
# Registro confirmado pelo pesquisador. Mantém-se mesmo sem CNAE religioso.
HUMAN_CONFIRMED = {"ASSOCIACAO COMUNITARIA JUREMA RAIZ"}


def hits(text):
    text = text or ""
    return sorted(k for k, rx in RX.items() if rx.search(text))


def classify(row):
    razao = row.get("razao_social", "")
    fantasia = row.get("nome_fantasia", "")
    all_hits = sorted(set(hits(razao) + hits(fantasia)))
    active = row.get("situacao_cadastral") == "02"
    religious_cnae = row.get("cnae_fiscal") == RELIGIOUS_CNAE
    confirmed = razao.upper().strip() in HUMAN_CONFIRMED
    core = set(all_hits) & CORE
    context = set(all_hits) & CONTEXT

    if confirmed:
        return "confirmado_humano", all_hits, active, religious_cnae
    if not all_hits:
        return "ruido_lexico", all_hits, active, religious_cnae
    # Nome explícito de terreiro/candomblé é forte; CNAE religioso aumenta a evidência.
    if active and religious_cnae and core:
        return "provavel_terreiro", all_hits, active, religious_cnae
    if active and ("terreiro" in core or "candomble" in core) and not row.get("cnae_fiscal", "").startswith("47"):
        return "provavel_terreiro", all_hits, active, religious_cnae
    if active and core:
        return "religioso_a_revisar", all_hits, active, religious_cnae
    if active and context and religious_cnae:
        return "religioso_a_revisar", all_hits, active, religious_cnae
    if active and context:
        return "evidencia_fraca", all_hits, active, religious_cnae
    return "inativo_ou_irregular", all_hits, active, religious_cnae


def main():
    with open(INP, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    results = []
    summary = Counter()
    by_uf = Counter()
    by_terms = Counter()
    for r in rows:
        tier, terms, active, rel_cnae = classify(r)
        summary[tier] += 1
        by_uf[(tier, r.get("uf", ""))] += 1
        for t in terms:
            by_terms[t] += 1
        # Sanitizado: sem CNPJ, contatos ou endereço completo
        results.append({
            "nome": r.get("razao_social") or r.get("nome_fantasia") or "Sem razão social",
            "nome_fantasia": r.get("nome_fantasia") or None,
            "uf": r.get("uf"), "cod_municipio": r.get("cod_municipio"),
            "cnae_fiscal": r.get("cnae_fiscal"), "situacao_cadastral": r.get("situacao_cadastral"),
            "tier": tier, "termos": terms,
            "cnae_religioso": rel_cnae,
            "fonte": "receita_federal_cnpj_2026_10",
        })

    (OUT / "candidatos_sanitizados.json").write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")
    audit = {
        "total_candidatos_recuperados": len(results),
        "metodo": "match com fronteiras de palavra em razão social/nome fantasia; classificação conservadora por termo, CNAE 9491-0/00 e situação cadastral. Não é validação final.",
        "tiers": dict(summary),
        "termos_identificados": dict(by_terms.most_common()),
        "provavel_terreiro_por_uf": dict(sorted(((uf, n) for (tier, uf), n in by_uf.items() if tier == "provavel_terreiro"), key=lambda x: -x[1])),
        "nota": "Apenas 'provavel_terreiro' é candidata a validação posterior. Nenhum registro foi incorporado à v4 nesta etapa.",
    }
    (OUT / "auditoria_triagem.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
