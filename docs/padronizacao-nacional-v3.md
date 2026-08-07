# Padronização Nacional v3 — Análise Multi-Modelo Consolidada

**Data:** 2026-08-07
**Modelos:** GLM-5.2 (semântica/nomes), Claude Sonnet 4.6 (estrutura/campos), Gemini 2.5 Pro (proveniência/reconciliação)
**Base:** 8.815 registros, 7 fontes, 394 candidatos de deduplicação
**Commits:** D2 `789cfcc` + `a3b4830` + `b84d37e` (branch `feature/dedup-preservadora-v3`)

---

## 1. Cobertura Nominal

| Fonte | Total | Com nome | Sem nome | Placeholder |
|---|---:|---:|---:|---:|
| mapeando_axe | 3.923 | 3.922 | 1 | 24 (0,61%) |
| cnpj | 2.673 | 2.673 | 0 | 12 (0,45%) |
| ceao | 1.155 | 1.155 | 0 | 80 (6,93%) |
| bahia_google | 550 | 550 | 0 | 0 |
| sefaz | 234 | 234 | 0 | 0 |
| terreiros_brasil | 260 | 260 | 0 | 0 |
| osm | 20 | 20 | 0 | 0 |
| **Total** | **8.815** | **8.814** | **1** | **116 (1,32%)** |

**Nomes utilizáveis:** 8.698 (98,67%)

---

## 2. Padrões de Variação Nominal

### Variações ortográficas principais

| Conceito | Formas encontradas | Frequência |
|---|---|---|
| Ilê | `Ilê`, `Ilé`, `Ilè`, `Ìlè`, `Ile`, `Ylê`, `Ylé`, `Yle` | 1.030 (mapeando_axe), 564 (ceao), 369 (cnpj) |
| Axé | `Axé`, `Axê`, `Axe`, `Asé`, `Asê`, `Ase`, `Àṣẹ`, `Aṣé` | 674 (mapeando_axe), 521 (ceao), 333 (cnpj) |
| Oxum | `Oxum`, `Osum`, `Oxun` | Oxum dominante; Osum 6; Oxun 4 |
| Ogum | `Ogum`, `Ogun`, `Ògún`, `Ogún` | Ogum dominante |
| Xangô | `Xangô`, `Xango`, `Shango`, `Sango` | Xangô/Xango dominante |
| Iemanjá | `Iemanjá`, `Yemanjá` | Iemanjá dominante |
| Oyá/Iansã | `Oyá`, `Oya`, `Oiá`, `Iansã` | Relacionar, não substituir |
| Unzó (Bantu) | `Unzó`, `Onzo`, `Inzó`, `Nzó`, `Mansu`, `Manso` | SEFAZ dominante |

### Convenções por fonte

| Fonte | Característica |
|---|---|
| **cnpj** | 100% maiúsculas, sem diacríticos, nomes jurídicos, `ASSOCIACAO`/`ORGANIZACAO` |
| **sefaz** | 87,6% maiúsculas, léxico Bantu (`UNZO`/`MANSU`), `ASE` |
| **ceao** | Nomes curtos capitalizados, `Ilê Axé` dominante, 6,93% placeholders |
| **mapeando_axe** | Maior heterogeneidade, mistura de tradições regionais |
| **bahia_google** | Alta incidência de formas acentuadas `Ilê Axé` |
| **terreiros_brasil** | 19 entidades HTML não decodificadas, diversidade Unicode |

### Consistência entre fontes

- **123 grupos, 325 registros** com mesma chave canônica nominal em 2+ fontes
- **7 grupos** com mesma assinatura de tokens em ordem diferente
- **Nenhum identificador compartilhado** entre fontes (CNPJ, CEAO ID, OSM ID, Place ID)

---

## 3. Matriz de Cobertura por Fonte

| Fonte | Registros | Campos efetivos/93 | Coordenadas | Município/UF |
|---|---:|---:|---|---|
| mapeando_axe | 3.923 | 16 | 2.828 auxiliares (não promovidas) | Sim (3.907/3.923) |
| cnpj | 2.673 | 15 | 2.526 auxiliares (colapsadas) | Via SIAFI (2.633/2.673) |
| ceao | 1.155 | 23 | 1.155 (100%) | Não tem; via espacial |
| bahia_google | 550 | 11 | 550 (100%) | Não tem; via espacial |
| sefaz | 234 | 9 | 0 | Não tem |
| terreiros_brasil | 260 | 14 | 259 (99,6%, mas só 29 únicos) | Sim (137/137) |
| osm | 20 | 8 | 20 (100%) | Não tem; via espacial |

**48 campos** têm algum valor efetivo; **45 campos** permanecem `null` em todas as fontes.

### Campos exclusivos úteis por fonte

| Fonte | Campos exclusivos |
|---|---|
| CEAO | Ano fundação, liderança, regente, telefone, fotos, CEAO ID |
| CNPJ | CNPJ, razão social, data cadastral, endereço cadastral estruturado, código SIAFI |
| Mapeando Axé | Consulta, confiança, status, precisão geocodificação |
| Terreiros Brasil | Descrição, URL, categoria declarada, método recuperação |
| SEFAZ | Código SEFAZ |
| Google | Rating, reviews |
| OSM | (OSM ID perdido no agregado) |

---

## 4. Problemas de Padronização Identificados

### Endereço
- CNPJ fornece logradouro/número/bairro/CEP separados; demais fontes usam concatenado
- **Recomendação:** separar `endereco_culto.*` de `endereco_cadastral.*`

### Coordenadas
- Terreiros Brasil: 259 pares, apenas **29 únicos** (93,4% compartilhados)
- CNPJ: 2.526 pares, apenas 1.636 únicos (1 ponto aparece 510 vezes)
- CNPJ `precision` tem 47 taxons heterogêneos (`musical_instrument`, `restaurant`) — não é precisão espacial
- **Recomendação:** vocabulário controlado: `rooftop`, `parcel`, `street`, `neighbourhood`, `postcode`, `municipality`, `unknown`

### CNPJ
- 2.673 CNPJs com máscara, todos validados (dígitos verificadores OK)
- Valor canônico: 14 dígitos; preservar representação original separada

### Telefone
- Apenas CEAO tem telefone (966 com 8 dígitos, 136 com 16 dígitos, 38 sem dígitos)
- **Recomendação:** lista `contato.telefones[]` com número original, normalizado, DDD, tipo, status

### Datas
- CNPJ: 2.673 em `YYYYMMDD` (data cadastral, NÃO fundação)
- CEAO: 1.133 anos em `YYYY` (fundação)
- **Recomendação:** manter `data_inicio_cadastral` separado de `data_fundacao`

### Categoria/Nação
- CEAO: 51 grafias de nação (`Keto`, `Keto Angola`, `Angola Keto`, `Jêje`, `Jêje Savalu`)
- Terreiros Brasil: 11 nações, 12 categorias (taxonomia distinta)
- Google/SEFAZ/OSM: apenas `Não informado` (deve ser null, não categoria)
- **Recomendação:** crosswalk versionado, componentes múltiplos, categoria analítica derivada

---

## 5. Algoritmo de Normalização Nominal Proposto

```text
normalizar_nome(registro):
    original = registro.nome_original
    guardar original imutável em nome.declarado

    se nulo/vazio: status = "ausente"; retornar
    se placeholder: status = "placeholder"; retornar

    comparacao = html_unescape(original)
    comparacao = unicode_normalize_NFKC(comparacao)
    comparacao = casefold(comparacao)
    comparacao = substituir "&" por " e "
    normalizar apóstrofos/hífens como limites de token
    remover pontuação não semântica
    colapsar espaços

    chave_base = remover_diacriticos(comparacao)

    para cada token, aplicar equivalências ortográficas seguras:
        ile/yle → ile; axe/ase/ashe → axe
        ogun → ogum; osum/oshum → oxum
        shango/sango → xango; yemanja → iemanja

    # NÃO reordenar nem excluir componentes
    nome.normalizado_match = juntar tokens na ordem original
    nome.assinatura_tokens = ordenar tokens  # apenas para candidatos

    classificar qualidade: ausente | placeholder | generico | utilizavel

    gerar candidatos:
        1. identificador forte compartilhado
        2. nome estrito + município/UF
        3. nome aproximado + endereço/coordenadas
        4. assinatura de tokens + evidência territorial

    nunca fundir apenas por nome
```

**Princípios:**
- Preservar forma original intacta
- Forma canônica para comparação, não substituição
- Não perder homônimos legítimos
- Números/datas são componentes legítimos (`7 Flechas`, `12 de Outubro`)
- Não aplicar title case (danifica Yorùbá, Bantu)

---

## 6. Vocabulário Controlado Preliminar

| Grupo | ID | Formas/aliases |
|---|---|---|
| Tipo de casa | `HOUSE_ILE` | Ilê, Ilé, Ile, Ylê, Ylé, Yle |
| Conceito | `REL_AXE` | Axé, Axe, Asé, Ase, Àṣẹ |
| Tipo genérico | `HOUSE_GENERIC` | terreiro, casa, roça, barracão, centro, tenda, templo |
| Tipo Bantu | `HOUSE_BANTU` | unzó, inzó, onzo, nzó, mansu, manso, kwe |
| Orixá | `ORIXA_OSUN` | Oxum, Osum, Oshum, Oxun |
| Orixá | `ORIXA_OGUN` | Ogum, Ogun, Ògún, Ogún |
| Orixá | `ORIXA_SANGO` | Xangô, Xango, Shango, Sango |
| Orixá | `ORIXA_OYA` | Oyá, Oya, Oiá (relacionar Iansã) |
| Orixá | `ORIXA_YEMANJA` | Iemanjá, Yemanjá |
| Orixá | `ORIXA_OSOSSI` | Oxóssi, Oxossi (relacionar Odé) |
| Honoríficos | `HONOR_LEADERSHIP` | Pai, Mãe, Tatá, Mameto, Makota, Babalorixá, Ialorixá, Babalaô |

---

## 7. Modelo de Reconciliação em 3 Camadas

### Camada 1 — Registro-fonte (imutável)
- `source_record_key`, fonte, ID nativo, payload original, hash
- Coordenadas declaradas separadas de geocodificação auxiliar
- Referência a exclusões e decisões de revisão

### Camada 2 — Entidade terreiro
Estados de relação:
- `entidades_distintas` — CNPJs diferentes, conflito forte, revisão negativa
- `possivel_mesma_entidade` — nome/endereço compatíveis, sem ID forte
- `mesma_entidade_mesmo_local` — ID forte comum + localização compatível
- `mesma_entidade_local_anterior` — ID forte comum + episódio temporal antigo
- `mesma_entidade_local_atual` — episódio vigente
- `nao_resolvido` — evidência conflitante/insuficiente

**Regras mínimas:**
1. CNPJs válidos diferentes → bloqueia fusão automática
2. CNPJ/place_id/OSM ID exato → pode auto-linkar (preservando ambas ocorrências)
3. Telefone comum exige município compatível
4. Nome/endereço/proximidade isoladamente → apenas candidatos
5. CNPJ matriz/filial → mesma organização, não necessariamente mesmo terreiro

### Camada 3 — Episódios de localização
- `location_id`, `entity_id`, endereço, coordenadas, `valid_from`, `valid_to`, `status`
- **Limitação atual:** `data_coleta` é nulo em todos os 8.815; não é possível distinguir local anterior de atual

---

## 8. Análise dos 394 Candidatos

### Distribuição

| Dimensão | Categoria | Pares |
|---|---|---:|
| Evidência | nome exato | 384 |
| | similaridade de nome | 23 |
| | distância | 23 |
| Relação | possible_same_entity | 379 |
| | unresolved | 11 |
| | distinct_entities | 4 |
| Revisão | pending | 390 |
| | rejected (CNPJ conflitante) | 4 |
| Fonte | same-source | 369 |
| | cross-source | 25 (6,3%) |

### Componentes reais
- 394 pares → **180 componentes conexos reais** (não 394)
- **434 ocorrências únicas** envolvidas (não 788)
- Maiores componentes: 9 registros/14 arestas (homônimos mapeando_axe)

### Auto-link seguro com dados atuais: **zero**
- 4 pares têm CNPJ nos dois lados — todos conflitantes
- 0 pares têm telefone/email nos dois lados
- 366 pares têm endereço nos dois lados — apenas 4 normalizam igual

---

## 9. Cobertura Nacional

| UF | Registros | % |
|---|---:|---:|
| BA | 2.143 | 24,31% |
| RS | 1.491 | 16,91% |
| SP | 1.379 | 15,64% |
| PE | 1.279 | 14,51% |
| PA | 1.098 | 12,46% |
| MG | 529 | 6,00% |
| RJ | 205 | 2,33% |
| PR | 123 | 1,40% |
| CE | 89 | 1,01% |
| SC–AC | 489 | 5,54% |
| Sem UF | 163 | 1,85% |

- **657 municípios** cobertos
- Estimativa Brasil: ~20 mil terreiros → cobertura de **44,1%** (antes de descontar duplicatas)
- **Lacunas graves:** Norte (exceto PA), Centro-Oeste, interior do Nordeste, AC, AL, AP, RO, RR, TO

---

## 10. Estratégia de Enriquecimento Google — Piloto 100

| Categoria | Quantidade | Critério |
|---|---:|---|
| Reconciliação | 40 | 22 extremos de 11 pares `unresolved` cross-source + 8 de 4 `collapsed_coordinate` + 10 de maiores componentes |
| Recuperação geográfica | 30 | Sem coordenadas/CNPJ, máx 3 por município, UFs sub-representadas |
| Identidade incompleta | 20 | Nomes curtos/genéricos, sem endereço, incluir SEFAZ |
| Controle | 10 | Endereço+coordenadas conhecidos (medir precisão) |

**Integração Google:**
- Resposta como nova ocorrência `google_places`, não atualização destrutiva
- Preservar `place_id`, consulta, data, hash da resposta
- Coordenadas Google começam como auxiliares
- Promover `place_id` apenas após validação de match
- Respeitar licenciamento API e regras de publicação

---

## 11. Prioridade por Campo (não por fonte)

| Campo | Prioridade |
|---|---|
| IDs nativos | Preservar todos em namespaces separados |
| Nome preferido | CEAO/Terreiros Brasil → Mapeando Axé → OSM/Google/SEFAZ; fantasia CNPJ só após vínculo |
| Razão social | CNPJ exclusivamente; nunca substituir nome religioso |
| Endereço culto | CEAO/Google/OSM/Terreiros/Mapeando; prioritizar mais recente + consistente |
| Endereço cadastral | CNPJ exclusivamente; estrutura própria |
| Município/UF | Declarado (Mapeando/Terreiros) → espacial (coordenadas) → SIAFI (CNPJ) |
| Coordenadas | Declarada/nativa → CEAO/Google/OSM → Mapeando geocoder → CNPJ geocoder (último) |
| CNPJ | Após validação de dígitos; conflito entre válidos bloqueia fusão |
| Telefone | CEAO; lista com DDD, tipo, status |
| Email/site | Permanecer null até fonte explícita |
| Fundação | CEAO (ano); separar de data cadastral CNPJ |
| Nação/categoria | CEAO + Terreiros Brasil (preservar ambos); crosswalk versionado |
| Rating/reviews | Google e CEAO separados; não calcular média |

---

## 12. Validações de Integridade Propostas

1. **Espacial:** lat/lon em par; faixa válida; point-in-polygon com IBGE; detectar coordenadas compartilhadas
2. **CNPJ:** 14 dígitos + verificadores; conflito bloqueia fusão
3. **Valores vazios:** normalizar `""`, `Não informado`, `N/A` → null
4. **Endereço:** CEP 8 dígitos; UF em domínio oficial; SIAFI ≠ IBGE em campos distintos
5. **Contato:** telefone como lista; email lowercase; URL HTTP(S)
6. **Datas:** CNPJ YYYYMMDD → ISO; CEAO YYYY; fundação ≠ abertura cadastral
7. **Taxonomia:** raw preservado; crosswalk versionado; `Não informado` = ausência
8. **Linhagem:** unicidade de source_record_key; contagem por fonte fecha em 8.815

---

## 13. Riscos Principais

1. **Promoção indevida de geocodificação auxiliar** como coordenada autoritativa
2. **Falsas fusões** por coordenadas colapsadas (Terreiros Brasil, CNPJ)
3. **Confusão endereço cadastral vs. local de culto**
4. **Confusão data cadastral vs. fundação religiosa**
5. **Cobertura inflada** por campos presentes mas vazios
6. **`Não informado` tratado como categoria**
7. **Perda de identidade nativa** (Google/OSM/SEFAZ no agregado)
8. **Fonte vencedora global** apagando divergências históricas
9. **Publicação acidental** de endereço/telefone/liderança sem política explícita
10. **Normalização destrutiva:** apagar diacríticos, title case, reordenar tokens

---

## 14. Próximos Passos

1. **D3** — Criar fila de revisão humana para os 394 candidatos (390 pending)
2. **D4** — Materializar entidades/ocorrências após revisão
3. **T3** — Piloto Google Places (100 entidades estratificadas)
4. Implementar algoritmo de normalização nominal com vocabulário controlado
5. Implementar matriz de prioridade por campo nos adaptadores
6. Adicionar validações de integridade no pipeline
7. Decodificar 19 entidades HTML em terreiros_brasil
8. Corrigir 39 UFs inválidas do CNPJ
9. Recuperar OSM ID nativo perdido no agregado