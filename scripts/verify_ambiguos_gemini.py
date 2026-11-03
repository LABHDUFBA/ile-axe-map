#!/usr/bin/env python3
"""
verify_ambiguos_gemini.py — Verificação com Gemini dos 133 casos ambíguos da fila Google.

Fluxo:
- Lê data/revisao_google.json; seleciona registros com sugestao == 'ambíguo'.
- Para cada um, pede ao Gemini (gemini-3.5-flash) classificação estruturada:
  manter | falso_positivo | pendente, com motivo curto e confiança.
- Resultados salvos incrementalmente em data/verificacao_gemini_ambiguos.jsonl
  (um registro por linha; reexecuções pulam review_id já verificados).
- Nunca remove registros do dataset: a ferramenta humana (revisao-google.html)
  continua sendo a via de decisão; este script é assistivo.

Uso: GEMINI_API_KEY=... python3 scripts/verify_ambiguos_gemini.py
"""
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
REV = BASE / "data" / "revisao_google.json"
OUT = BASE / "data" / "verificacao_gemini_ambiguos.jsonl"
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
API = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

PROMPT = """Você é um assistente de curadoria de um mapa acadêmico de terreiros de candomblé e umbanda (Ilê Axé Map, LABHD/UFBA).
Classifique o registro abaixo: ele é um terreiro/casa de culto afro-brasileiro legítimo, ou um falso positivo (comércio, condomínio, associação não-religiosa, CRAS, sítio arqueológico, etc.)?

Nome: {nome}
Endereço: {endereco}
Categoria sugerida: {sugestao_automática}
Motivo da suspeita automática: {motivo_sugestao}

Responda APENAS com JSON: {{"decisao": "manter|falso_positivo|pendente", "motivo": "<motivo curto em pt-BR>", "confianca": 0.0-1.0}}"""


def gemini_classify(rec, api_key):
    body = json.dumps({
        "contents": [{"parts": [{"text": PROMPT.format(
            nome=rec.get("nome", ""),
            endereco=rec.get("endereco", ""),
            sugestao_automática=rec.get("sugestao", ""),
            motivo_sugestao=rec.get("motivo_sugestao", ""),
        )}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 300},
    }).encode()

    req = urllib.request.Request(
        API + "?key=" + api_key,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.load(r)
    text = resp["candidates"][0]["content"]["parts"][0]["text"].strip()
    # tolerar cercas de código
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    return json.loads(text)


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERRO: GEMINI_API_KEY não definida no ambiente.")
        return 2

    regs = json.loads(REV.read_text(encoding="utf-8"))["registros"]
    ambiguos = [r for r in regs if r.get("sugestao") == "ambíguo"]
    print(f"casos ambíguos: {len(ambiguos)}")

    done = set()
    if OUT.exists():
        with OUT.open(encoding="utf-8") as f:
            done = {json.loads(l)["review_id"] for l in f if l.strip()}

    todo = [r for r in ambiguos if r["review_id"] not in done]
    print(f"já verificados: {len(done)}; a verificar: {len(todo)}")
    if not todo:
        return 0

    ok = err = 0
    with OUT.open("a", encoding="utf-8") as f:
        for i, rec in enumerate(todo):
            try:
                verdict = gemini_classify(rec, api_key)
                f.write(json.dumps({
                    "review_id": rec["review_id"],
                    "nome": rec.get("nome"),
                    "decisao": verdict.get("decisao"),
                    "motivo": verdict.get("motivo"),
                    "confianca": verdict.get("confianca"),
                    "modelo": MODEL,
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                }, ensure_ascii=False) + "\n")
                f.flush()
                ok += 1
                if (i + 1) % 20 == 0:
                    print(f"  {i+1}/{len(todo)} processados...")
            except Exception as e:
                err += 1
                print(f"  ERRO em {rec['review_id']}: {e}")
                time.sleep(3)

    print(f"\nOK: {ok} verificados, {err} erros. Saída: {OUT}")
    return 0 if err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())