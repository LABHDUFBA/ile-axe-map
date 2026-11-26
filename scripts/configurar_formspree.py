#!/usr/bin/env python3
"""Liga o formulário de contribuição a um endpoint do Formspree.

O site é estático, então o envio padrão é `mailto:`. Com um endpoint configurado, o
formulário passa a enviar por POST (fetch) e o visitante não precisa abrir o aplicativo de
e-mail. O endpoint fica em `data/formspree.json` e é injetado no atributo `data-endpoint`
do <body> de contribuir.html pelo build.

Uso:
  python3 scripts/configurar_formspree.py https://formspree.io/f/xxxxxxxx
  python3 scripts/configurar_formspree.py xxxxxxxx          # só o hash id
  python3 scripts/configurar_formspree.py --testar           # envia uma submissão de teste
  python3 scripts/configurar_formspree.py --remover          # volta ao mailto

O hash id aparece no Formspree em Integration → "endpoint", no formato
https://formspree.io/f/abcdefgh.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(REPO, "data", "formspree.json")
PAGINAS = os.path.join(REPO, "scripts", "build_paginas_contribuicao.py")


def normalizar(entrada):
    entrada = entrada.strip()
    m = re.search(r"formspree\.io/f/([A-Za-z0-9]+)", entrada)
    if m:
        return "https://formspree.io/f/" + m.group(1)
    if re.fullmatch(r"[A-Za-z0-9]{6,}", entrada):
        return "https://formspree.io/f/" + entrada
    raise SystemExit("Não reconheci o endpoint. Cole a URL completa "
                     "(https://formspree.io/f/xxxxxxxx) ou só o código.")


def ler():
    if not os.path.exists(CONFIG):
        return None
    with open(CONFIG, encoding="utf-8") as fh:
        return (json.load(fh) or {}).get("endpoint")


def gravar(endpoint):
    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    with open(CONFIG, "w", encoding="utf-8") as fh:
        json.dump({"endpoint": endpoint}, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def rebuild():
    r = subprocess.run([sys.executable, PAGINAS], capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())
    if r.returncode:
        raise SystemExit("O build falhou")


def conferir_no_html():
    caminho = os.path.join(REPO, "contribuir.html")
    with open(caminho, encoding="utf-8") as fh:
        html = fh.read()
    m = re.search(r'<body data-endpoint="([^"]*)"', html)
    atual = m.group(1) if m else "(atributo ausente)"
    print(f"data-endpoint em contribuir.html: {atual or '(vazio — modo mailto)'}")
    return atual


def testar(endpoint):
    """Envia uma submissão de teste. Se o formulário ainda não foi confirmado no painel,
    o Formspree devolve 200 com aviso de confirmação por e-mail — o print abaixo mostra isso."""
    dados = {
        "tipo_casa": "no_mapa",
        "registro": "TESTE",
        "nome_pessoa": "Teste automático",
        "relacao": "pesquisador",
        "autorizo": "sim",
        "represento": "nao",
        "mensagem": "Submissão de teste do Ilê Axé Map. Ignore.",
        "conteudo": "Submissão de teste gerada por scripts/configurar_formspree.py",
        "_subject": "Ilê Axé Map — teste de integração",
    }
    corpo = urllib.parse.urlencode(dados).encode()
    req = urllib.request.Request(endpoint, data=corpo, method="POST")
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("User-Agent", "IleAxeMap/1.0 (teste de integracao)")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"HTTP {r.status}")
            print(r.read().decode("utf-8", "replace")[:800])
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} — {e.reason}")
        print(e.read().decode("utf-8", "replace")[:800])
        if e.code == 404:
            print("\n404: o hash id não existe ou o formulário foi apagado.")
        elif e.code == 403:
            print("\n403: formulário desativado, domínio bloqueado ou limite do plano atingido.")
    except Exception as e:  # noqa: BLE001
        print("falhou:", e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("endpoint", nargs="?", help="URL do endpoint ou hash id")
    ap.add_argument("--testar", action="store_true", help="envia uma submissão de teste")
    ap.add_argument("--remover", action="store_true", help="volta ao modo mailto")
    args = ap.parse_args()

    if args.remover:
        gravar("")
        rebuild()
        conferir_no_html()
        print("modo mailto restaurado.")
        return

    if args.endpoint:
        ep = normalizar(args.endpoint)
        gravar(ep)
        rebuild()
        atual = conferir_no_html()
        print(f"endpoint configurado: {ep}")
        if atual != ep:
            raise SystemExit("O HTML não recebeu o endpoint — verifique o build.")
        if args.testar:
            print("\n--- envio de teste ---")
            testar(ep)
        else:
            print("\nAgora faça um envio de teste pelo site (ou rode com --testar).")
        return

    atual = ler()
    print("endpoint atual:", atual or "(nenhum — modo mailto)")
    if atual:
        conferir_no_html()
        if args.testar:
            testar(atual)


if __name__ == "__main__":
    main()
