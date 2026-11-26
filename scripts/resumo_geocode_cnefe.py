#!/usr/bin/env python3
"""Resume o geocode CNEFE por UF e mede sua concordância com o geocoder do Google (cache v46).

A concordância é o teste que interessa: o cache v46 tem 1.105 CNPJs resolvidos pelo Google com
tipo de retorno (ROOFTOP, RANGE_INTERPOLATED…). Comparar as duas coordenadas para o mesmo CNPJ
diz se o casamento por endereço no CNEFE chega ao mesmo lugar — e com que erro — sem gastar
requisição nenhuma.

Uso: python3 scripts/resumo_geocode_cnefe.py
"""
import csv
import json
import math
import os
import statistics
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRADA = os.path.join(REPO, "data", "cnpj_nacional", "geocode_cnefe.csv")
CACHE = os.path.join(REPO, "data", "geocode_cnpj_cache_v46.json")


def haversine(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def main():
    with open(ENTRADA, encoding="utf-8") as fh:
        linhas = list(csv.DictReader(fh))
    print(f"registros: {len(linhas)}")

    por_uf = defaultdict(lambda: defaultdict(int))
    for r in linhas:
        por_uf[r["uf"]][r["nivel"]] += 1

    print(f"\n{'UF':<4}{'n':>7}{'exato':>9}{'quadra':>9}{'cep':>8}{'sem':>6}{'exato%':>8}{'end.%':>7}")
    tot = defaultdict(int)
    for uf in sorted(por_uf, key=lambda u: -sum(por_uf[u].values())):
        c = por_uf[uf]
        n = sum(c.values())
        for k, v in c.items():
            tot[k] += v
        end = c["exato"] + c["quadra"]
        print(f"{uf:<4}{n:>7}{c['exato']:>9}{c['quadra']:>9}{c['cep']:>8}{c['nenhum']:>6}"
              f"{100*c['exato']/n:>7.1f}%{100*end/n:>6.1f}%")
    n = sum(tot.values())
    end = tot["exato"] + tot["quadra"]
    print(f"{'TOT':<4}{n:>7}{tot['exato']:>9}{tot['quadra']:>9}{tot['cep']:>8}{tot['nenhum']:>6}"
          f"{100*tot['exato']/n:>7.1f}%{100*end/n:>6.1f}%")

    if not os.path.exists(CACHE):
        print("\ncache do Google ausente; sem teste de concordância")
        return
    cache = json.load(open(CACHE, encoding="utf-8"))
    dist = defaultdict(list)
    for r in linhas:
        c = cache.get("cnpj:" + r["cnpj"])
        if not c or c.get("lat") is None or not r["lat"]:
            continue
        d = haversine(float(r["lat"]), float(r["lon"]), c["lat"], c["lng"])
        dist[r["nivel"]].append(d)

    print("\n=== concordância CNEFE × Google, mesmo CNPJ ===")
    print(f"{'nível':<8}{'n':>6}{'mediana':>10}{'p90':>9}{'<50m':>8}{'<100m':>8}{'<250m':>8}")
    todos = []
    for nivel in ("exato", "quadra", "cep"):
        d = sorted(dist.get(nivel, []))
        if not d:
            continue
        todos += d
        p90 = d[int(0.9 * (len(d) - 1))]
        print(f"{nivel:<8}{len(d):>6}{statistics.median(d):>9.0f}m{p90:>8.0f}m"
              f"{100*sum(1 for x in d if x < 50)/len(d):>7.0f}%"
              f"{100*sum(1 for x in d if x < 100)/len(d):>7.0f}%"
              f"{100*sum(1 for x in d if x < 250)/len(d):>7.0f}%")
    if todos:
        d = sorted(todos)
        print(f"{'todos':<8}{len(d):>6}{statistics.median(d):>9.0f}m{d[int(0.9*(len(d)-1))]:>8.0f}m"
              f"{100*sum(1 for x in d if x < 50)/len(d):>7.0f}%"
              f"{100*sum(1 for x in d if x < 100)/len(d):>7.0f}%"
              f"{100*sum(1 for x in d if x < 250)/len(d):>7.0f}%")


if __name__ == "__main__":
    main()
