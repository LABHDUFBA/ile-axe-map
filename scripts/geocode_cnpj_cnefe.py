#!/usr/bin/env python3
"""Geocodifica os endereços CNPJ do acervo a partir do CNEFE 2022 (IBGE).

Fonte: Cadastro Nacional de Endereços para Fins Estatísticos, Censo 2022. Cada arquivo por UF
traz, na mesma linha, CEP, logradouro, número, latitude e longitude — o que permite casar o
endereço declarado à Receita com a coordenada do cadastro sem nenhuma API paga.

Estratégia: o CNEFE inteiro tem ~106 milhões de endereços, não cabe em memória. Para cada UF
baixamos o arquivo (uma vez, em `data/cnefe/`), percorremos em streaming e guardamos apenas as
linhas cujo CEP aparece no bruto daquele estado. O pareamento é feito depois, em memória.

Níveis de precisão gravados:
  exato   — CEP + logradouro + número
  quadra  — CEP + logradouro, número vizinho (distância declarada em `dist_numero`)
  cep     — só o CEP casou; coordenada = mediana dos endereços daquele CEP
  nenhum  — CEP ausente do CNEFE; coordenada não atribuída

Uso:
  python3 scripts/geocode_cnpj_cnefe.py            # todas as UFs, retomando de onde parou
  python3 scripts/geocode_cnpj_cnefe.py --uf RN BA # subconjunto
  python3 scripts/geocode_cnpj_cnefe.py --forcar   # refaz mesmo as UFs já concluídas
"""
import argparse
import csv
import io
import json
import os
import re
import statistics
import sys
import unicodedata
import urllib.request
import zipfile
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRUTO = os.path.join(REPO, "data", "cnpj_nacional", "terreiros_cnpj_nacional.csv")
CACHE_DIR = os.path.join(REPO, "data", "cnefe")
SAIDA = os.path.join(REPO, "data", "cnpj_nacional", "geocode_cnefe.csv")
ESTADO = os.path.join(REPO, "data", "cnefe", "progresso.json")
BASE_URL = ("https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos"
            "/Censo_Demografico_2022/Arquivos_CNEFE/CSV/UF")

COD_UF = {"RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16, "TO": 17, "MA": 21,
          "PI": 22, "CE": 23, "RN": 24, "PB": 25, "PE": 26, "AL": 27, "SE": 28, "BA": 29,
          "MG": 31, "ES": 32, "RJ": 33, "SP": 35, "PR": 41, "SC": 42, "RS": 43, "MS": 50,
          "MT": 51, "GO": 52, "DF": 53}

TIPO = {"RUA", "R", "AV", "AVENIDA", "TRAVESSA", "TV", "TRAV", "ALAMEDA", "AL", "ESTRADA", "EST",
        "RODOVIA", "ROD", "PRACA", "PCA", "LARGO", "LGO", "VIA", "VIELA", "BECO", "CAMINHO",
        "CONJUNTO", "CJ", "RESIDENCIAL", "RES", "VILA", "JD", "JARDIM", "PARQUE", "PQ",
        "CONDOMINIO", "LOTEAMENTO", "SETOR", "QUADRA", "QD", "LOTE", "CHACARA", "SITIO",
        "FAZENDA", "POVOADO", "DISTRITO", "ACESSO", "PASSAGEM", "PASS", "TRAVESSA"}

COLUNAS = ["cnpj", "razao_social", "uf", "cod_municipio", "cep", "logradouro", "numero",
           "nivel", "lat", "lon", "num_cnefe", "dist_numero", "cod_unico_endereco"]


def sem_acento(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").upper()


def chave_rua(s):
    """Tokens do logradouro sem tipo de via, pontuação e acento."""
    toks = re.sub(r"[^A-Z0-9 ]", " ", sem_acento(s)).split()
    return [t for t in toks if t not in TIPO and len(t) > 1]


def mesmo_logradouro(a, b):
    """Casa nomes de via tolerando abreviação e complemento: 'SAO JOAO' ⊂ 'SAO JOAO BATISTA'."""
    ta, tb = chave_rua(a), chave_rua(b)
    if not ta or not tb:
        return False
    sa, sb = set(ta), set(tb)
    if sa == sb or sa.issubset(sb) or sb.issubset(sa):
        return True
    inter = sa & sb
    return len(inter) / min(len(sa), len(sb)) >= 0.7 and len(inter) >= 1 and len(min(sa, sb, key=len)) >= 2


def numero_int(s):
    m = re.match(r"\s*(\d+)", s or "")
    return int(m.group(1)) if m else None


def baixar(uf):
    os.makedirs(CACHE_DIR, exist_ok=True)
    destino = os.path.join(CACHE_DIR, f"{COD_UF[uf]:02d}_{uf}.zip")
    if os.path.exists(destino) and os.path.getsize(destino) > 10_000:
        return destino
    url = f"{BASE_URL}/{COD_UF[uf]:02d}_{uf}.zip"
    tmp = destino + ".part"
    with urllib.request.urlopen(url, timeout=300) as r, open(tmp, "wb") as f:
        while True:
            bloco = r.read(1 << 20)
            if not bloco:
                break
            f.write(bloco)
    os.replace(tmp, destino)
    return destino


def enderecos_do_cep(caminho_zip, ceps_alvo):
    """Percorre o CSV da UF em streaming e devolve só as linhas dos CEPs pedidos."""
    with zipfile.ZipFile(caminho_zip) as z:
        nome = z.namelist()[0]
        with z.open(nome) as fh:
            leitor = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="replace"), delimiter=";")
            achados = defaultdict(list)
            for linha in leitor:
                cep = (linha.get("CEP") or "").strip()
                if cep in ceps_alvo:
                    achados[cep].append((linha.get("NOM_SEGLOGR") or "", linha.get("NUM_ENDERECO") or "",
                                         linha.get("LATITUDE") or "", linha.get("LONGITUDE") or "",
                                         linha.get("COD_UNICO_ENDERECO") or ""))
            return achados


def casar(reg, achados):
    """Devolve (nivel, lat, lon, num_cnefe, dist, cod_unico)."""
    cep = (reg["cep"] or "").strip()
    lista = achados.get(cep)
    if not lista:
        return "nenhum", "", "", "", "", ""
    alvo = numero_int(reg["numero"])
    mesma = [(n, num, la, lo, cu) for (n, num, la, lo, cu) in lista if mesmo_logradouro(reg["logradouro"], n)]
    if mesma and alvo is not None:
        exatos = [x for x in mesma if numero_int(x[1]) == alvo]
        if exatos:
            n, num, la, lo, cu = exatos[0]
            return "exato", la, lo, num, 0, cu
        # número vizinho na mesma via: distância em números de porta
        melhor = min(mesma, key=lambda x: abs((numero_int(x[1]) or 0) - alvo))
        la, lo = melhor[2], melhor[3]
        if la and lo:
            return "quadra", la, lo, melhor[1], abs((numero_int(melhor[1]) or 0) - alvo), melhor[4]
    if mesma:
        n, num, la, lo, cu = mesma[0]
        if la and lo:
            return "quadra", la, lo, num, "", cu
    # só o CEP: mediana dos endereços daquele CEP
    coords = [(float(la), float(lo)) for (_, _, la, lo, _) in lista if la and lo]
    if coords:
        med_lat = statistics.median([p[0] for p in coords])
        med_lon = statistics.median([p[1] for p in coords])
        return "cep", f"{med_lat:.7f}", f"{med_lon:.7f}", "", "", ""
    return "nenhum", "", "", "", "", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uf", nargs="*", help="siglas a processar; padrão: todas as presentes no bruto")
    ap.add_argument("--forcar", action="store_true")
    args = ap.parse_args()

    with open(BRUTO, encoding="utf-8") as fh:
        registros = [r for r in csv.DictReader(fh) if (r.get("uf") or "").strip()]
    por_uf = defaultdict(list)
    for r in registros:
        por_uf[r["uf"].strip()].append(r)

    ufs = args.uf or sorted(por_uf, key=lambda u: -len(por_uf[u]))
    progresso = {}
    if os.path.exists(ESTADO):
        progresso = json.load(open(ESTADO, encoding="utf-8"))

    novo_arquivo = not os.path.exists(SAIDA) or args.forcar
    saida = open(SAIDA, "w" if novo_arquivo else "a", encoding="utf-8", newline="")
    escritor = csv.writer(saida)
    if novo_arquivo:
        escritor.writerow(COLUNAS)

    for uf in ufs:
        if uf not in COD_UF:
            print(f"[{uf}] UF desconhecida, pulando", flush=True)
            continue
        if uf in progresso and not args.forcar:
            print(f"[{uf}] já concluída ({progresso[uf]['n']} registros), pulando", flush=True)
            continue
        regs = por_uf[uf]
        ceps = {(r["cep"] or "").strip() for r in regs if (r.get("cep") or "").strip()}
        print(f"[{uf}] {len(regs)} registros, {len(ceps)} CEPs — baixando CNEFE…", flush=True)
        caminho = baixar(uf)
        print(f"[{uf}] {os.path.getsize(caminho)/1e6:.1f} MB — lendo…", flush=True)
        achados = enderecos_do_cep(caminho, ceps)
        contagem = {"exato": 0, "quadra": 0, "cep": 0, "nenhum": 0}
        for r in regs:
            nivel, lat, lon, num, dist, cu = casar(r, achados)
            contagem[nivel] += 1
            escritor.writerow([r["cnpj"], r["razao_social"], uf, r["cod_municipio"], r["cep"],
                               r["logradouro"], r["numero"], nivel, lat, lon, num, dist, cu])
        saida.flush()
        progresso[uf] = {"n": len(regs), "ceps": len(ceps), **contagem}
        json.dump(progresso, open(ESTADO, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        pct = lambda k: 100 * contagem[k] / len(regs) if regs else 0
        print(f"[{uf}] exato {contagem['exato']} ({pct('exato'):.1f}%) · quadra {contagem['quadra']} "
              f"({pct('quadra'):.1f}%) · cep {contagem['cep']} ({pct('cep'):.1f}%) · "
              f"sem {contagem['nenhum']} ({pct('nenhum'):.1f}%)", flush=True)
        del achados

    saida.close()
    total = {"exato": 0, "quadra": 0, "cep": 0, "nenhum": 0}
    for v in progresso.values():
        for k in total:
            total[k] += v.get(k, 0)
    n = sum(total.values())
    print("\n=== TOTAL " + str(n) + " registros ===")
    for k, v in total.items():
        print(f"  {k:7s} {v:6d}  {100*v/n:5.1f}%")
    recuperavel = total["exato"] + total["quadra"]
    print(f"  endereço↔coordenada (exato+quadra): {recuperavel} ({100*recuperavel/n:.1f}%)")
    print(f"  saída: {SAIDA}")


if __name__ == "__main__":
    main()
