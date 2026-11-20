"""Opção A — reclassificar as pilhas de centróide municipal em vez de excluí-las.

Problema: na v4_8, 1.799 feições estão empilhadas em 11 pontos que são
centróides de município, todas com geo_status 'geocode_cnpj_v46_validado'.
O mapa as desenha como 700 pontos na mesma esquina de Mossoró.

Solução: marcar precisão municipal, retirar o selo de validação e manter as
feições no dataset. A renderização passa a agregá-las por município.

Uso: python3 scripts/reclassificar_precisao_municipal.py
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
GEO = BASE / "data" / "v4_9_candidata" / "terreiros_nacional_v4_9_candidata.geojson"
LIMIAR_PILHA = 20  # feições no mesmo ponto exato = centróide, não endereço

def ll(f):
    c = (f.get("geometry") or {}).get("coordinates")
    return (round(float(c[0]), 6), round(float(c[1]), 6)) if c else None

def main():
    gj = json.loads(GEO.read_text(encoding="utf-8"))
    feats = gj["features"]

    pos = Counter(ll(f) for f in feats if ll(f))
    pilhas = {k for k, v in pos.items() if v >= LIMIAR_PILHA}
    print(f"pilhas de centróide detectadas: {len(pilhas)}")

    afetadas = 0
    por_pilha = defaultdict(list)
    for f in feats:
        p = f.setdefault("properties", {})
        c = ll(f)
        municipal = c in pilhas
        if municipal:
            p["precisao"] = "municipio"
            p["geo_status"] = "centroide_municipio_nao_validado"
            p["renderizacao"] = "agregada"
            p["nota_localizacao"] = (
                "Coordenada é o centro do município, não o endereço da casa. "
                "A localização exata está em verificação com as comunidades."
            )
            afetadas += 1
            por_pilha[(p.get("municipio") or "(sem município)", p.get("uf") or "(sem UF)")].append(f)
        else:
            p.setdefault("precisao", "endereco" if p.get("geo_status") != "herdado_v2_validado" else "municipio_validado")
            p.setdefault("renderizacao", "ponto")

    # agregados por município para a camada de contagem
    agregados = []
    for (mun, uf), lista in sorted(por_pilha.items(), key=lambda kv: -len(kv[1])):
        c = ll(lista[0])
        if c is None:
            continue
        agregados.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": list(c)},
            "properties": {
                "tipo": "agregado_municipal",
                "municipio": mun,
                "uf": uf,
                "total_registros": len(lista),
                "precisao": "municipio",
                "fonte": "receita_federal_cnpj",
                "nota": "Registros com localização conhecida apenas no nível do município.",
            },
        })
    agregados.sort(key=lambda f: -f["properties"]["total_registros"])

    gj["metadata"]["precisao_municipal"] = {
        "feicoes": afetadas,
        "pilhas": len(pilhas),
        "agregados": len(agregados),
        "criterio": f"{LIMIAR_PILHA} ou mais feições na mesma coordenada exata",
        "politica": "mantidas no dataset, agregadas na renderização, sem selo de validação",
    }
    gj["agregados_municipais"] = {
        "type": "FeatureCollection",
        "features": agregados,
    }

    GEO.write_text(json.dumps(gj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"feições reclassificadas: {afetadas}")
    print(f"agregados municipais gerados: {len(agregados)}")
    for a in agregados[:6]:
        p = a["properties"]
        print(f"  {p['total_registros']:4d}  {p['municipio']}/{p['uf']}")
    print("total de feições no arquivo:", len(feats))

if __name__ == "__main__":
    main()
