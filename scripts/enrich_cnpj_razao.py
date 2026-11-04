#!/usr/bin/env python3
"""Enriquece a coleta CNPJ nacional com razão social e termos de seleção.

Reprocessa apenas Empresas0-9 em streaming, produz o índice raiz→razão social
para as raízes já selecionadas e reescreve o CSV de candidatos. Não baixa nem
reprocessa Estabelecimentos (5,4 GB) novamente.
"""
import csv
import io
import json
import re
import time
import urllib.request
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "data" / "cnpj_nacional"
TMP = Path("/home/hermes/.hermes/cache/scratch")
MIRROR = "https://dados-abertos-rf-cnpj.casadosdados.com.br/arquivos/2026-10-13"

# Termos com fronteiras de palavra. Isso evita falsos positivos como RENZO e SEGUNDO.
KEYWORD_PATTERNS = [
    r"\bcandombl\w*\b", r"\bumbanda\b", r"\bterreiro\b",
    r"\bil[eê]\s+ax[eé]\b", r"\bax[eé]\s+de\b", r"\borix[áa]s?\b",
    r"\bbatuque\b", r"\bjurema\b", r"\btambor\s+de\s+min[áa]\b",
    r"\bbabalorix\w*\b", r"\bialorix\w*\b", r"\bcasa\s+de\s+orix\w*\b",
    r"\bmacumba\b", r"\bquimbanda\b", r"\bcatimb[óo]\b", r"\bnzo\b",
    r"\begun(?:gun)?\b", r"\bvodu\b",
]
KW_RE = re.compile("|".join(KEYWORD_PATTERNS), re.IGNORECASE)


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "IleAxeMap-LABHD-UFBA/1.0"})
    with urllib.request.urlopen(req, timeout=600) as r, open(dest, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)


def rows_in_zip(path):
    with zipfile.ZipFile(path) as z:
        with z.open(z.namelist()[0]) as b:
            yield from csv.reader(io.TextIOWrapper(b, encoding="latin-1"), delimiter=";")


def main():
    candidates = OUT / "terreiros_cnpj_nacional.csv"
    roots = set(json.loads((OUT / "raizes_alvo.json").read_text()))
    mapping = {}
    for i in range(10):
        zp = TMP / f"Empresas{i}.zip"
        download(f"{MIRROR}/Empresas{i}.zip", zp)
        found = 0
        for row in rows_in_zip(zp):
            if len(row) >= 2 and row[0] in roots:
                mapping[row[0]] = row[1]
                found += 1
        zp.unlink()
        print(f"Empresas{i}: {found} razões recuperadas", flush=True)

    (OUT / "razoes_sociais_alvo.json").write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
    tmp = candidates.with_suffix(".enriquecido.tmp")
    with open(candidates, encoding="utf-8") as inp, open(tmp, "w", newline="", encoding="utf-8") as out:
        reader = csv.DictReader(inp)
        cols = list(reader.fieldnames or [])
        writer = csv.DictWriter(out, fieldnames=cols + ["termos_match_razao", "termos_match_fantasia"])
        writer.writeheader()
        for r in reader:
            razao = mapping.get(r["raiz"], "")
            r["razao_social"] = razao
            r["termos_match_razao"] = "|".join(sorted(set(m.group(0).lower() for m in KW_RE.finditer(razao))))
            r["termos_match_fantasia"] = "|".join(sorted(set(m.group(0).lower() for m in KW_RE.finditer(r["nome_fantasia"]))))
            writer.writerow(r)
    tmp.replace(candidates)
    print(f"OK: {len(mapping)} razões recuperadas e {candidates.name} enriquecido", flush=True)


if __name__ == "__main__":
    main()
