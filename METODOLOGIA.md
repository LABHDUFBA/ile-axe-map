# Nota Técnico-Metodológica

## Mapeamento de Terreiros de Candomblé da Bahia

**Projeto:** LABHD/UFBA — Terreiro Map  
**Data da coleta:** 25 de julho de 2026  
**Repositório:** [github.com/LABHDUFBA/terreiro-map](https://github.com/LABHDUFBA/terreiro-map)  
**Mapa interativo:** [labhdufba.github.io/terreiro-map](https://labhdufba.github.io/terreiro-map/)  
**Responsável:** Leonardo Fonseca (leofn@ufba.br)

---

## 1. Apresentação

Este projeto consolida dados de quatro fontes distintas para mapear terreiros de candomblé e outros espaços religiosos afro-brasileiros no estado da Bahia. O resultado é um conjunto deduplicado de **2.158 registros únicos**, dos quais **1.924 possuem coordenadas geográficas** passíveis de georreferenciamento em mapa interativo.

O mapa utiliza a biblioteca **MapLibre GL JS** sobre a base cartográfica **OpenFreeMap** (dark theme), com paleta cromática afro-baiana (terracota, âmbar, dourado), tipografia Fraunces + Hanken Grotesk e painéis em glassmorphism.

---

## 2. Fontes de Dados

### 2.1 OpenStreetMap (Overpass API)

| Item | Detalhe |
|---|---|
| **Fonte** | OpenStreetMap — Overpass API |
| **URL** | overpass-api.de |
| **Área** | Estado da Bahia |
| **Método** | Queries Overpass QL com múltiplos termos |
| **Termos de busca** | candomblé, terreiro, ilê axé, ile axe, place_of_worship+afro, ogum, oxum, rocambole, matriz africana |
| **Data da coleta** | 23–24 de julho de 2026 |
| **Registros obtidos** | 50 elementos brutos |
| **Após filtragem** | 44 terreiros (removidas pousadas, barracas, restaurantes) |
| **Campos disponíveis** | nome, coordenadas, tipo (amenity), nação (quando tag presente) |
| **Custo** | Gratuito (open data) |
| **Licença** | Open Database License (ODbL) |

**Termos filtrados manualmente:** "pousada", "barraca", "restaurante" — removidos por não corresponderem a espaços religiosos.

**Mantidos:** Monumento Mãe Gilda de Ogum e Cachoeira de Oxumarê — embora não sejam terreiros stricto sensu, são sítios de relevância religiosa afro-brasileira.

### 2.2 Google Places API

| Item | Detalhe |
|---|---|
| **Fonte** | Google Places API — Text Search |
| **Área** | Estado da Bahia (219 cidades) |
| **Método** | Text Search com 14 termos de busca, 1 requisição por cidade por termo |
| **Termos de busca** | terreiro de candomblé, candomblé, casa de santo, ilê, ilê axé, centro religioso afro-brasileiro, centro de candomblé, ilê asé, abassá, inzo, nzo, vodum, nkisi, egbé |
| **Estratégia** | 3 termos comuns em todas as 219 cidades; 11 termos específicos nas 45 maiores cidades |
| **Data da coleta** | 25 de julho de 2026 |
| **Requisições utilizadas** | 900 (limite estabelecido: 950) |
| **Registros obtidos** | 1.532 lugares únicos |
| **Campos disponíveis** | nome, coordenadas, endereço, telefone, rating, número de reviews, place_id |
| **Custo** | $0.042 por requisição ( Places API) — ~$37,80 |
| **Chave API** | Fornecida pelo pesquisador |

**Limitação:** A API retorna estabelecimentos comerciais registrados no Google. Terreiros sem presença digital (sem cadastro no Google Business) não são captados. Há viés de cobertura toward áreas urbanas e terreiros com maior visibilidade institucional.

### 2.3 CEAO/UFBA — Centro de Estudos Afro-Orientais

| Item | Detalhe |
|---|---|
| **Fonte** | CEAO/UFBA — terreiros.ceao.ufba.br |
| **URL** | https://www.terreiros.ceao.ufba.br/ |
| **Método** | Scraping da página principal (extração de marcadores JavaScript) + requisições AJAX individuais para detalhes de cada terreiro |
| **Data da coleta** | 25 de julho de 2026 |
| **Registros obtidos** | 1.155 terreiros |
| **Campos disponíveis** | nome, liderança, nação, ano de fundação, orixá regente, endereço, bairro, CEP, telefone, foto (thumbnail + grande), coordenadas |
| **Cobertura de campos** | Nome 100%, Liderança 100%, Nação 100%, Telefone 100%, Endereço 83%, Foto 98% |
| **Custo** | Gratuito (dados abertos) |
| **Observação** | Certificado SSL do site vencido — requisições com verificação desativada |

**Páginas baixadas:** index (página principal com mapa), apresentação, análise, equipe, contato, links.

**Fotos:** 1.081 thumbnails (21MB) incluídos no repositório. 1.081 fotos em alta resolução (168MB) disponíveis mediante solicitação.

**Limitação:** O cadastro CEAO é resultado de pesquisa acadêmica e pode não refletir a totalidade de terreiros em atividade. A data de atualização do cadastro não é explicitada no site.

### 2.4 SEFAZ/Salvador — Prefeitura Municipal

| Item | Detalhe |
|---|---|
| **Fonte** | SEMUR — Secretaria Municipal de Reparação (Prefeitura de Salvador) |
| **URL** | https://www.sefaz.salvador.ba.gov.br/geosalvador/sharing/rest/content/items/08d566c4316a470b8a146e640c998b08/data |
| **Formato original** | PDF cartográfico (17MB), projeção UTM 24S, datum SIRGAS 2000 |
| **Método** | Renderização do PDF em alta resolução (pymupdf) + recorte segmentado + OCR visual para extração da lista numerada |
| **Data da coleta** | 25 de julho de 2026 |
| **Registros obtidos** | 635 terreiros (códigos 2–888, com lacunas na numeração) |
| **Campos disponíveis** | código SEMUR, nome |
| **Coordenadas** | Não extraídas (pontos georreferenciados no mapa, mas em coordenadas de pixel — conversão UTM não automatizada) |
| **Custo** | Gratuito (dados públicos) |
| **Dados de 2020** | Atualização SEMUR 2020, base cartográfica SICAD 2006 |

**Distribuição por região administrativa:**

| Região | Terreiros |
|---|---|
| I — Centro / Brotas | 59 |
| II — Subúrbio / Ilhas | 121 |
| III — Cajazeiras | 86 |
| IV — Itapuã / Ipitanga | 69 |
| V — Cidade Baixa | 22 |
| VI — Barra / Pituba | 38 |
| VII — Liberdade / São Caetano | 106 |
| VIII — Cabula / Tancredo Neves | 66 |
| IX — Pau da Lima | 68 |
| X — Valéria | 34 |
| **Total** | **633** |

**Limitação:** Cobertura restrita ao município de Salvador. Coordenadas não extraídas — os 234 registros únicos da SEFAZ sem correspondência em outras fontes não aparecem no mapa interativo. Os nomes foram extraídos via OCR visual, sujeitos a erros de transcrição.

---

## 3. Metodologia de Consolidação

### 3.1 Deduplicação

A deduplicação foi realizada em duas etapas:

1. **Coordenadas:** dois registros são considerados duplicados se a distância Haversine entre suas coordenadas for inferior a **50 metros**.

2. **Nome normalizado:** dois registros são considerados duplicados se o nome normalizado (lowercase, sem acentos, sem caracteres não-alfanuméricos, espaços colapsados) for idêntico, ou se um contiver o outro como substring (para nomes com comprimento > 5 caracteres).

Quando uma duplicata é detectada, o registro com maior número de campos preenchidos é mantido, e os campos do registro mais rico sobrescrevem os do menos rico.

### 3.2 Resultado da consolidação

| Etapa | Quantidade |
|---|---|
| Total bruto (4 fontes) | 3.242 |
| Duplicatas removidas | 1.084 |
| **Total único** | **2.158** |
| Com coordenadas (no mapa) | 1.924 |
| Sem coordenadas (apenas SEFAZ) | 234 |

**Distribuição por fonte após deduplicação:**

| Fonte | Registros únicos |
|---|---|
| Google Places | 1.221 |
| CEAO/UFBA | 682 |
| SEFAZ/Salvador | 234 |
| OSM | 21 |
| **Total** | **2.158** |

### 3.3 Proveniência

Cada registro mantém o campo `fonte` indicando sua origem (`osm`, `google`, `ceao`, `sefaz`) e `fonte_detalhe` com a descrição completa da fonte. Registros do CEAO preservam o ID original (`ceao_id`); registros da SEFAZ preservam o código SEMUR (`sefaz_codigo`).

---

## 4. Stack Tecnológica

| Componente | Tecnologia |
|---|---|
| Mapa interativo | MapLibre GL JS |
| Base cartográfica | OpenFreeMap (dark theme) |
| Tipografia | Fraunces (display) + Hanken Grotesk (body) |
| Paleta | Terracota `#C8553D`, Âmbar `#E8A87C`, Dourado `#F2C944` |
| Hospedagem | GitHub Pages (labhdufba.github.io) |
| Dados | GeoJSON (estático, sem backend) |
| Scraping CEAO | Python 3.12 + urllib + ssl (certificado ignorado) |
| Coleta Google | Python 3.12 + Google Places API (Text Search) |
| Coleta OSM | Python 3.12 + Overpass API |
| Extração SEFAZ | Python 3.12 + pymupdf + OCR visual |
| Deduplicação | Python 3.12 + Haversine + normalização de texto (unidecode) |

---

## 5. Limitações e Considerações

1. **Cobertura desigual:** O Google Places cobre toda a Bahia mas privilegia terreiros com presença digital. O CEAO cobre Salvador e região metropolitana com dados acadêmicos ricos. A SEFAZ cobre apenas Salvador. O OSM tem cobertura limitada mas dados abertos verificáveis.

2. **SEFAZ sem coordenadas:** Os 234 registros únicos da SEFAZ não aparecem no mapa interativo por falta de coordenadas extraídas. Extração futura via conversão UTM→WGS84 dos pontos no PDF é possível.

3. **Viés de visibilidade:** Terreiros com menor visibilidade institucional (sem cadastro no Google, sem presença no OSM, não incluídos no cadastro CEAO) estão sub-representados.

4. **Atualização dos dados:** A data de coleta é 25 de julho de 2026. Terreiros abertos ou fechados após esta data não estão refletidos. O cadastro CEAO e o mapa SEFAZ (2020) podem estar desatualizados.

5. **Sensibilidade dos dados:** Terreiros são espaços religiosos que enfrentam intolerância e violência. A disponibilização pública de endereços e coordenadas deve ser ponderada. Este projeto, vinculado ao LABHD/UFBA, tem finalidade acadêmica e de preservação da memória.

6. **Erros de OCR:** A extração da lista SEFAZ foi feita via OCR visual do PDF cartográfico. Nomes podem conter erros de transcrição. Recomenda-se conferência com o documento original.

---

## 6. Referências

- **CEAO/UFBA.** Terreiros de Candomblé da Bahia. Centro de Estudos Afro-Orientais, Universidade Federal da Bahia. Disponível em: https://terreiros.ceao.ufba.br/

- **SEMUR/Salvador.** Mapa de Terreiros — Salvador Dados: Sistema de Informação Municipal. Secretaria Municipal de Reparação, Prefeitura Municipal de Salvador, 2020. Base cartográfica: SICAD 2006, projeção UTM 24S, datum SIRGAS 2000.

- **OpenStreetMap.** OpenStreetMap contributors. Dados disponíveis sob a Open Database License (ODbL). Consulta via Overpass API (overpass-api.de).

- **Google.** Google Places API — Text Search. Google Maps Platform. Consulta em 25 de julho de 2026.

- **MapLibre GL JS.** MapLibre GL — biblioteca open-source para renderização de mapas vetoriais. https://maplibre.org/

- **OpenFreeMap.** Map tiles gratuitos baseados em OpenStreetMap. https://openfreemap.org/

---

## 7. Arquivos do Repositório

```
terreiro-map/
├── index.html                      # Mapa interativo (MapLibre GL JS)
├── README.md                       # Documentação do projeto
├── METODOLOGIA.md                  # Esta nota técnico-metodológica
├── .gitignore                      # Exclui arquivos grandes
├── scripts/
│   └── collect_osm.py              # Script de coleta Overpass
├── data/
│   ├── terreiros.geojson           # GeoJSON do mapa (1.924 com coords)
│   ├── terreiros_all.geojson       # GeoJSON consolidado
│   ├── terreiros_all_sources.json  # JSON completo com metadados (2.158)
│   ├── ceao/
│   │   ├── terreiros_ceao_complete.json   # 1.155 terreiros com detalhes
│   │   ├── terreiros_ceao.geojson         # GeoJSON CEAO
│   │   ├── markers.json                   # Marcadores extraídos do JS
│   │   ├── pages/                         # Páginas HTML do site CEAO
│   │   │   ├── index.html
│   │   │   ├── apresentacao.html
│   │   │   ├── analise.html
│   │   │   ├── equipe.html
│   │   │   ├── contato.html
│   │   │   └── link.html
│   │   └── fotos/                         # 1.081 thumbnails (21MB)
│   │       ├── 1_thumb.jpg
│   │       └── ...
│   └── sefaz/
│       └── sefaz_terreiros_complete.json  # 635 terreiros SEMUR
```

**Arquivos não incluídos no repositório (disponíveis mediante solicitação):**
- `data/ceao/fotos_grandes.zip` — 1.081 fotos em alta resolução (162MB)
- `data/sefaz/sefaz_salvador_map.pdf` — PDF cartográfico original (17MB)

---

## 8. Como Citar

> FONSECA, Leonardo N. **Mapeamento de Terreiros de Candomblé da Bahia.** LABHD/UFBA, 2026. Disponível em: https://labhdufba.github.io/terreiro-map/. Acesso em: [data].

---

*Nota elaborada em 25 de julho de 2026.*