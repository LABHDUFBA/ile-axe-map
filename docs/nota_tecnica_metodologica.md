# Nota Técnica Metodológica — Base Unificada de Terreiros

## 1. Objetivo

Construir uma base de dados georreferenciada, deduplicada e validada de terreiros de candomblé e matrizes africanas no Brasil, a partir de três fontes complementares.

## 2. Fontes de Dados

### 2.1 Mapeando Axé (2010)

- **Origem:** Pesquisa acadêmica "Mapeamento dos Terreiros de Candomblé da Bahia" — LABHD/UFBA
- **Registros:** 3.923
- **Cobertura geográfica:** Nacional, com concentração na Bahia
- **Campos:** Nome, endereço, bairro, cidade, UF, CEP, nação (Ketu, Angola, Jeje, etc.), liderança, ano de fundação
- **Data de coleta:** 2010 (dados podem estar desatualizados)
- **Geocodificação:** Nominatim/OpenStreetMap (2 passadas)
  - Passada 1: endereço completo → 1.717 matches (43,8%)
  - Passada 2: query simplificada (sem bairro/CEP) → +1.084 matches (total 2.721; 69,4%)
  - Precisão: 263 house_number, 2.458 street
- **Validação cruzada:** Google Places API (Text Search) com filtro de qualidade
  - Filtro: mesma cidade/UF + similaridade de nome (token set ratio ≥ 60%)
  - 1.795 registros validados (45,8% do total); 2.128 pendentes (cron diário)
  - Classificação em 10 categorias (confirmado, google_melhor, nominatim_melhor, etc.)
- **Limitações:** Dados de 2010 — endereços podem ter mudado; 1.202 registros sem coordenada

### 2.2 Terreiros do Brasil (terreirosdobrasil.com.br)

- **Origem:** Plataforma web de mapeamento colaborativo (WordPress + plugin Classified Listings)
- **Registros:** 260
- **Cobertura geográfica:** 12 UFs; CE (70), SP (24), BA (23), RN (7), PE (4)
- **Campos:** Nome, nação (Ketu, Umbanda, Angola, etc.), endereço, cidade, UF, descrição, link
- **Método de coleta:** API REST WordPress (`/wp-json/wp/v2/rtcl_listing`) + scrape de páginas individuais
- **Geocodificação:** Nominatim (endereço extraído do `<li>` na página individual)
  - 259/260 com coordenadas (99,6%)
  - 1 sem coords (anúncio não-terreiro)
- **Limitações:**
  - Coords do Google Maps embed não extraíveis do HTML estático (são injetadas via JS)
  - 122 registros com endereço em formato internacional ("State of X, Brazil") — regex ampliado na v3
  - Mistura de terreiros com anúncios comerciais (velas, venda de animais, workshops)
  - Plataforma colaborativa — dados auto-declarados, sem verificação documental

### 2.3 CNPJ / Receita Federal

- **Origem:** Consulta pública de CNPJ (Receita Federal do Brasil)
- **Registros:** 2.673
- **Cobertura geográfica:** 15+ UFs; SP (1.355 = 50,7%), RS (231), RJ (204), MG (189), BA (161)
- **Campos:** CNPJ, razão social, nome fantasia, CEP, logradouro, número, bairro, UF, código município, data de início de atividade, natureza jurídica, CNAE
- **Critério de seleção:** CNAE 9491000 (Atividades de organizações religiosas) + filtro por termos (terreiro, candomblé, umbanda, axé, ilê, tenda, roça, etc.) no nome
- **Situação cadastral:** 100% ativos (código 02)
- **Geocodificação:** Nominatim (3 estratégias em cascata)
  1. Endereço completo (tipo + logradouro + número + bairro + CEP + UF)
  2. CEP + UF
  3. Bairro + UF
- **Limitações:**
  - CNPJ inclui entidades jurídicas que podem não ser terreiros físicos (associações, institutos)
  - Endereço do CNPJ pode ser do contador/representante, não do terreiro
  - SP sobrerrepresentado (50,7%) — pode refletir formalização maior no estado

## 3. Pipeline de Unificação

### 3.1 Normalização

1. **Nome:** uppercase, remoção de acentos para comparação, preservação do original
2. **Endereço:** padronização (tipo logradouro abreviado → completo)
3. **Nação:** mapeamento para taxonomia unificada (Ketu, Angola, Jeje, Umbanda, Jurema, Omoloko, Tambor de Mina, Efon, Nago, Iseshe, Outro)
4. **Coordenadas:** WGS84 (lat/lng)
5. **UF:** sigla de 2 letras

### 3.2 Deduplicação

Estratégia em 3 níveis:

1. **Match exato:** mesmo CNPJ (fonte CNPJ vs CNPJ) — eliminar duplicata
2. **Match por proximidade:** registros a <100m de distância + similaridade de nome ≥70% (token set ratio) — marcar como possível duplicata
3. **Match por endereço:** mesmo CEP + mesmo número + logradouro similar — marcar como possível duplicata

Prioridade de fonte quando duplicata:
- CNPJ/Receita Federal (endereço verificado, CNPJ ativo)
- Mapeando Axé (dados acadêmicos validados)
- Terreiros do Brasil (auto-declarado)

### 3.3 Geocodificação

- **Fonte primária:** Nominatim/OpenStreetMap (custo zero, dados abertos)
- **Validação:** Google Places API (Text Search) com filtro de qualidade (cidade/UF + similaridade de nome)
- **Precisão:** house_number > street > suburb > city
- **Cache local:** JSONL para retomabilidade

### 3.4 Saída

- **GeoJSON:** FeatureCollection com Point geometry, propriedades padronizadas
- **CSV:** tabela plana com todas as colunas
- **Mapa:** MapLibre GL JS, tema dark, paleta Afro-Baiana (padrão Ilê Axé Map)

## 4. Taxonomia de Nações

| Código | Nome | Descrição |
|---|---|---|
| ketu | Ketu | Candomblé Ketu (Nagô-Yorubá) |
| angola | Angola | Candomblé Angola (Banto) |
| jeje | Jeje | Candomblé Jeje (Fon-Ewe) |
| efon | Efon | Candomblé Efon |
| nago | Nago | Nago (Yorubá não-Ketu) |
| umbanda | Umbanda | Umbanda |
| jurema | Jurema | Jurema (Catimbó) |
| omoloko | Omoloko | Omoloko |
| tambor_mina | Tambor de Mina | Tambor de Mina |
| iseshe | Iseshe | Ìṣẹ̀ṣe (tradição Yorubá) |
| outro | Outro | Não classificado |

## 5. Considerações Éticas

- **Liderança e contato:** NÃO incluídos no GeoJSON público (proteção de dados pessoais)
- **CNPJ:** Incluído apenas para fins de deduplicação; não exposto no mapa público
- **Endereço:** Exibido no mapa, mas sem coordenadas de precisão sub-meter (respeitando privacidade)
- **Fontes:** Todas públicas e/ou de consulta pública

## 6. Métricas de Qualidade

| Métrica | Meta | Status atual |
|---|---|---|
| Cobertura total (3 fontes) | ≥6.000 únicos | 6.856 bruto |
| Geocodificação | ≥80% com coords | Em curso |
| Validação Google Places | ≥50% validados | 45,8% (cron ativo) |
| Deduplicação | <5% duplicatas | Pendente |
| Precisão geográfica | ≥60% house_number/street | 69,4% (Mapeando Axé) |

---

**Versão:** 1.0 | **Data:** 2026-08-03 | **Autor:** LABHD/UFBA