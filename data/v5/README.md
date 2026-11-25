# Camada v5 — base publicada desde 25/11/2026

`terreiros_nacional_v5.geojson` é o arquivo que a interface carrega (`index.html`).
Reúne **8.215 entidades**: as 8.036 da v4.8 mais **172 do Amazonas** (Atlas do Axé)
e **7 do Distrito Federal** (AXÉS/LHS-UnB).

## Construção
```bash
python3 scripts/ingest_atlas_axe.py     # coleta/normaliza o Atlas do Axé (AM)
python3 scripts/ingest_axes_unb.py      # coleta/normaliza o AXÉS/LHS-UnB (DF)
python3 scripts/build_v5.py             # v4.8 + novas fontes → data/v5/
```
`scripts/build_v5.py` lê `data/v4_8/terreiros_nacional_v4_8.geojson` e as duas camadas
normalizadas; não altera nada da base anterior. A taxonomia canônica vem de
`scripts/taxonomia_v48.py` (extração sem efeitos colaterais do script da v4.8).

## Regras aplicadas
1. **Base intocada.** Os 8.036 registros da v4.8 entram exatamente como estavam (exceto
   nada: nenhum campo é reescrito).
2. **Comércio fora.** As duas lojas de artigos religiosos do Atlas ficaram fora da camada
   (decisão editorial: o mapa é de casas de axé). Seguem no payload bruto da fonte.
3. **Plataforma fora.** O registro "Atlas dos Terreiros" (Campus Darcy Ribeiro) do AXÉS é a
   própria plataforma, não uma casa — excluído.
4. **Duplicata interna fundida.** "ILÊ AXÉ YÁLÓÓDÊ OMIM ORUN" e "Ilê axé Yálóódê omim orun"
   (mesma casa, mesma cidade, 1,36 km) viraram uma entidade. Homônimos em bairros distintos,
   como "Terreiro de Umbanda (sem nome próprio no cadastro)", **não** foram fundidos.
5. **Tradição declarada é autoritativa.** Nação e linhagem só são convertidas para o
   vocabulário canônico quando compatíveis com a tradição declarada; quando não são (por
   exemplo "Mina Nagô" numa casa de Tambor de Mina), o valor bruto é preservado e marcado em
   `nacao_revisar`, em vez de corrigido por suposição.
6. **Sem coordenada, centróide declarado.** Registros sem ponto recebem o centróide do
   município (Nominatim, 24/11/2026) com `geo_status` que oculta o ponto por padrão.

## Precisão e visibilidade
| status | entidades | aparece por padrão |
|---|---|---|
| `fonte_declarada_alta` (ponto de mapa da fonte) | 154 | sim |
| `fonte_declarada_baixa` (≈100 m) | 5 | sim |
| `fonte_declarada_aproximada` (pelo endereço) | 9 | não |
| `centroide_municipio_atlas_axe` (sem coordenada na fonte) | 4 | não |
| `centroide_suspeito_axes` (região administrativa) | 6 | não |
| `centroide_municipio_axes_unb` (sem coordenada na fonte) | 1 | não |

Resultado: **159 das 179 entidades novas aparecem por padrão**; as 20 restantes ficam
ocultas até revisão, sem serem descartadas. Nada foi apagado da base anterior — o rollback
consiste em voltar `index.html` para `data/v4_8/terreiros_nacional_v4_8.geojson`.

## Auditoria
`auditoria_v5.json` registra: entrada por fonte, exclusões com motivo, fusões com distância,
publicados por fonte/UF/tradição, distribuição de `geo_status` e valores de nação enviados
para revisão humana (`Mina Nagô`, `Jeje`, `Mina`, `Quimbanda Congo`, `JUREMA`, `Ketu` em casa
de Umbanda).

## Anomalias herdadas da base (não introduzidas pela v5)
- **163 features** da v4.8 não têm `entity_id` (herança da candidata v4.1; aparecem com
  `versao: v4.1_candidata`).
- **188 `entity_id` repetidos** na base herdada (homônimos consolidados em municípios
  diferentes). Nenhum dos 179 registros novos repete id.
- Ambas são dívidas anteriores ao merge e ficam registradas aqui para não serem atribuídas
  à v5. Corrigi-las exige remanejar ids estáveis, o que deve ser feito em release própria.
