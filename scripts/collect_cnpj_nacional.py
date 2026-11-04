#!/usr/bin/env python3
"""
collect_cnpj_nacional.py — Coleta completa de terreiros no CNPJ (todas as UFs).

Fonte: dados abertos RFB (mirror Casa dos Dados, carga 2026-10-13).
Layout: CSV sem cabeçalho, ';' separado, aspas, ISO-8859-1.

PIPELINE (streaming, disco seguro — 95% cheio):
  Passada 1: Empresas0-9 → filtrar razão social por keywords afro → raízes-alvo
  Passada 2: Estabelecimentos0-9 → linhas com raiz ∈ alvo OU nome_fantasia com keyword
  Cada zip é baixado, processado em streaming e APAGADO antes do próximo.

Saída: data/cnpj_nacional/terreiros_cnpj_nacional.csv (+ relatório JSON)
Encoding de saída: UTF-8. Fonte oficial, republicável (dados abertos, CC-BY).

Uso: python3 scripts/collect_cnpj_nacional.py
"""
import csv
import io
import json
import re
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "data" / "cnpj_nacional"
OUT.mkdir(exist_ok=True)
TMP = Path("/home/hermes/.hermes/cache/scratch")

MIRROR = "https://dados-abertos-rf-cnpj.casadosdados.com.br/arquivos/2026-10-13"

KEYWORDS = [
    "candombl", "umbanda", "terreiro", "ile ax", "axé de", "axe de",
    "orixá", "orixa", "batuque", "jurema", "tambor de mina", "babalorix",
    "ialorix", "casa de orix", "macumba", "quimbanda", "catimbó", "catimbo",
    # Forma contextual: recupera Nzo Boya/Nzo ... (Angola), sem capturar Enzo/Lorenzo.
    "nzo ", "egun", "vodu",
]
KW_RE = re.compile("|".join(re.escape(k) for k in KEYWORDS), re.IGNORECASE)

# CNAE 9491-0/00 = organizações religiosas (usado só como sinal extra, não filtro único)
CNAE_RELIGIOSO = "9491"


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "IleAxeMap-LABHD-UFBA/1.0"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    dt = time.time() - t0
    print(f"    baixado {dest.name} ({dest.stat().st_size/1e6:.0f} MB) em {dt:.0f}s", flush=True)


def stream_zip_csv(zip_path):
    """Lê o CSV dentro do zip em streaming (sem extrair)."""
    with zipfile.ZipFile(zip_path) as zf:
        name = zf.namelist()[0]
        with zf.open(name) as f:
            wrapper = io.TextIOWrapper(f, encoding="latin-1")
            reader = csv.reader(wrapper, delimiter=";")
            for row in reader:
                yield row


def main():
    print("PASSADA 1: Empresas (razão social → raízes-alvo)", flush=True)
    roots = set()
    for i in range(10):
        zip_path = TMP / f"Empresas{i}.zip"
        url = f"{MIRROR}/Empresas{i}.zip"
        try:
            download(url, zip_path)
        except Exception as e:
            print(f"    ERRO Empresas{i}: {e}", flush=True)
            continue
        n = 0
        for row in stream_zip_csv(zip_path):
            if len(row) < 2:
                continue
            if KW_RE.search(row[1] or ""):
                roots.add(row[0])
                n += 1
        print(f"    Empresas{i}: {n} raízes-alvo (total acumulado {len(roots)})", flush=True)
        zip_path.unlink()

    (OUT / "raizes_alvo.json").write_text(json.dumps(sorted(roots)), encoding="utf-8")
    print(f"TOTAL raízes-alvo: {len(roots)}", flush=True)

    print("\nPASSADA 2: Estabelecimentos (raiz-alvo OU nome fantasia)", flush=True)
    out_path = OUT / "terreiros_cnpj_nacional.csv"
    cols = ["cnpj", "raiz", "razao_social", "nome_fantasia", "situacao_cadastral",
            "data_situacao", "cnae_fiscal", "tipo_logradouro", "logradouro", "numero",
            "complemento", "bairro", "cep", "uf", "cod_municipio", "ddd1", "tel1", "email",
            "match_tipo"]
    total = 0
    with open(out_path, "w", newline="", encoding="utf-8") as fo:
        w = csv.writer(fo)
        w.writerow(cols)
        for i in range(10):
            zip_path = TMP / f"Estabelecimentos{i}.zip"
            url = f"{MIRROR}/Estabelecimentos{i}.zip"
            try:
                download(url, zip_path)
            except Exception as e:
                print(f"    ERRO Estab{i}: {e}", flush=True)
                continue
            n = 0
            for row in stream_zip_csv(zip_path):
                if len(row) < 21:
                    continue
                raiz = row[0]
                nf = row[4] or ""
                match = None
                if raiz in roots:
                    match = "razao_social"
                elif KW_RE.search(nf):
                    match = "nome_fantasia"
                if not match:
                    continue
                w.writerow([
                    (raiz + row[1] + row[2]) if raiz.isdigit() else f"{raiz}{row[1]}{row[2]}",
                    raiz, "", nf, row[5] if len(row) > 5 else "", row[6] if len(row) > 6 else "",
                    row[11] if len(row) > 11 else "", row[13] if len(row) > 13 else "",
                    row[14] if len(row) > 14 else "", row[15] if len(row) > 15 else "",
                    row[16] if len(row) > 16 else "", row[17] if len(row) > 17 else "",
                    row[18] if len(row) > 18 else "", row[19] if len(row) > 19 else "",
                    row[20] if len(row) > 20 else "", row[21] if len(row) > 21 else "",
                    row[23] if len(row) > 23 else "", row[27] if len(row) > 27 else "",
                    match,
                ])
                n += 1
                total += 1
            print(f"    Estabelecimentos{i}: {n} registros (total {total})", flush=True)
            zip_path.unlink()

    print(f"\nOK: {total} registros → {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())