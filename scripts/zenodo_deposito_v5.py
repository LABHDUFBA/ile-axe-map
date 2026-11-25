#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publica a camada v5 no Zenodo como registro de acesso restrito.

Fluxo (InvenioRDM):
  1. POST /api/records                      → cria o draft
  2. POST /api/records/<id>/draft/files    → anuncia cada arquivo
  3. PUT  .../draft/files/<key>/content    → envia o conteúdo
  4. PUT  /api/records/<id>/draft          → metadados (creators em person_or_org)
  5. POST /api/records/<id>/draft/actions/publish

Sem --publicar, o script para no passo 4 e imprime o id do draft, para revisão na
interface. A publicação é irreversível: o DOI é registrado e o registro passa a
existir publicamente (metadados abertos, arquivos restritos).

Token: variável de ambiente ZENODO_TOKEN (scopes deposit:write e deposit:actions).
Nunca colar o token em chat; ele vive em ~/.hermes/.env.

Uso:
    python3 scripts/zenodo_deposito_v5.py                # prepara e para
    python3 scripts/zenodo_deposito_v5.py --publicar     # publica
"""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META = os.path.join(REPO, "docs", "zenodo_deposito_v5.json")
ARQUIVOS = [
    (os.path.join(REPO, "data", "v5", "terreiros_nacional_v5.geojson"), "terreiros_nacional_v5.geojson"),
    (os.path.join(REPO, "data", "v5", "auditoria_v5.json"), "auditoria_v5.json"),
    (os.path.join(REPO, "data", "v5", "README.md"), "README_v5.md"),
    (os.path.join(REPO, "metodologia.html"), "metodologia.html"),
]
BASE = "https://zenodo.org/api"


def token():
    t = os.environ.get("ZENODO_TOKEN", "").strip()
    if not t:
        sys.exit("ZENODO_TOKEN ausente. Coloque o token em ~/.hermes/.env (scopes deposit:write e deposit:actions).")
    return t


def call(method, path, tok, data=None, content_type="application/json", raw=None) -> tuple[int, Any]:
    url = path if path.startswith("http") else BASE + path
    body = None
    if raw is not None:
        body = raw
    elif data is not None:
        body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {tok}")
    req.add_header("Content-Type", content_type)
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            txt = r.read().decode() or "{}"
            payload: Any = json.loads(txt) if txt.strip().startswith(("{", "[")) else txt
            return r.status, payload
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:800]
        return e.code, {"erro": detail}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publicar", action="store_true")
    ap.add_argument("--draft-id", default=None, help="retoma um draft existente")
    args = ap.parse_args()

    meta_doc = json.load(open(META, encoding="utf-8"))
    meta = meta_doc["metadata"]

    faltando = [(p, k) for p, k in ARQUIVOS if not os.path.exists(p)]
    if faltando:
        sys.exit("arquivos ausentes: " + ", ".join(k for _, k in faltando))
    for p, k in ARQUIVOS:
        print(f"  {k:42s} {os.path.getsize(p)/1e6:6.2f} MB  md5 {hashlib.md5(open(p,'rb').read()).hexdigest()[:8]}")
    print("acesso:", meta["access_right"], "| licença:", meta["license"], "| criadores:", len(meta["creators"]))

    if not args.publicar and not args.draft_id:
        print("\n--publicar não informado: nada foi enviado ao Zenodo.")
        print("revise docs/zenodo_deposito_v5.json e rode com --publicar quando estiver de acordo.")

    tok = token()

    if args.draft_id:
        rid = args.draft_id
        print("retomando draft", rid)
    else:
        st, r = call("POST", "/records", tok, data={})
        if st not in (200, 201):
            sys.exit(f"falha ao criar draft: {st} {r}")
        rid = r.get("id") if isinstance(r, dict) else None
        if not rid:
            sys.exit(f"resposta sem id: {r}")
        print("draft criado:", rid)

    for p, key in ARQUIVOS:
        st, r = call("POST", f"/records/{rid}/draft/files", tok, data=[{"key": key}])
        if st not in (200, 201):
            sys.exit(f"falha ao anunciar {key}: {st} {r}")
        with open(p, "rb") as fh:
            st, r = call("PUT", f"/records/{rid}/draft/files/{key}/content", tok,
                         raw=fh.read(), content_type="application/octet-stream")
        if st not in (200, 201):
            sys.exit(f"falha no upload de {key}: {st} {r}")
        call("POST", f"/records/{rid}/draft/files/{key}/commit", tok, data={})
        print("  enviado:", key)
        time.sleep(1)

    st, r = call("PUT", f"/records/{rid}/draft", tok, data={"metadata": meta})
    if st not in (200, 201):
        sys.exit(f"falha nos metadados: {st} {r}")
    print("metadados aplicados")

    if not args.publicar:
        print(f"\ndraft pronto: https://zenodo.org/uploads/{rid}")
        print("revise na interface e rode de novo com --publicar --draft-id", rid)
        return

    st, r = call("POST", f"/records/{rid}/draft/actions/publish", tok, data={})
    if st not in (200, 201, 202):
        sys.exit(f"falha ao publicar: {st} {r}")
    print("publicado. DOI:", r.get("doi"), "| concept:", r.get("conceptdoi"))


if __name__ == "__main__":
    main()
