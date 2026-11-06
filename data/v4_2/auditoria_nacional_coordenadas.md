# Auditoria Nacional de Coordenadas — Ilê Axé Map v4.2
Data: 06/11/2026 · Base: `data/v4_2/terreiros_nacional_v4_2.geojson` (8.036 registros) · Referência: centróides IBGE (5.571 municípios)

## Resumo executivo

A auditoria de coordenadas contra município/UF declarados revelou que o problema de geocodificação é **nacional e concentrado em PE**, não restrito a Salvador/BA. O mapa público (com "Ocultar localizações aproximadas" ativo) expõe hoje cerca de **2.700 registros visíveis não-validáveis ou divergentes** — a maior parte herda geocodes fracos da v2 e do lote Mapeando Axé (CSV).

## Classificação por distância registro ↔ centróide do município declarado

| Categoria | Total | Visíveis (padrão) | Fontes principais | Causa provável |
|---|---:|---:|---|---|
| >400 km (outro estado) | 83 | 13 | Mapeando Axé (81) | Geocode de outro estado atribuído a registro de PE |
| 150–400 km (grave) | 83 | 25 | Mapeando Axé (81) | Idem; inclui Cuiabá→Ananindeua, Teresina→Belém |
| 60–150 km (suspeito) | 41 | 9 | Mapeando Axé (32) | Centróide de cidade vizinha ou fronteira |
| Município não casado com IBGE | 1.847 | 1.132 | herdado_v2 (1.108) | Campo `municipio` contém bairro (Plataforma, Paripe...) |
| Sem município/UF | 3.062 | 1.544 | CNPJ (1.932) | Cache Nominatim não populou município |
| ≤60 km (coerente) | 2.920 | — | — | Válido |
| `coordenada_agua` (v4.2) | 174 | 0 | herdado_v2 (169) + CEAP (5) | Já ocultos por padrão |

## Achados por fonte

- **Mapeando Axé (CSV)**: 81 dos 83 ">400 km" e 81 dos 83 "150–400 km" — lote de PE geocodificado com coordenadas de outros estados (Padre Carneiro, Caxias do Sul, Cuiabá, Teresina...). Recomenda-se re-geocodificar o lote inteiro ou marcá-lo `geo_status=geocode_divergente`.
- **herdado_v2 (BA)**: 1.108 não-casados por bairro no campo município; 622 sem município. Os 169 em água vieram daí. Campo `municipio` precisa de normalização bairro→município.
- **CNPJ/Receita Federal**: 1.932 sem município (660 já `fonte_propria_receita_federal_cnpj`); re-geocodificação necessária.
- **CEAP**: 5 registros em água já ocultos na v4.2.
- **OSM alta confiança**: 113 sem município — re-geocodificar.

## Planos de correção (onadas)

**Onda 1 — PE Mapeando Axé (~166 registros far/grave/suspeito visíveis ou não)**: re-geocodificar por nome+município com Places API (New) do Google. Os que não resolverem → `geo_status=geocode_divergente` + ocultos por padrão. Custo: ~US$ 0,83/1.000 calls Places Text Search.
**Onda 2 — herdado_v2 BA (~1.730 não-validáveis)**: normalizar município (bairro→município via tabela de bairros de Salvador) e re-geocodificar; os não-resolvidos → ocultos com status explícito.
**Onda 3 — CNPJ sem município (1.932)**: re-geocodificar por endereço→coords (Geocoding API) com validação de classe de precisão forte; sem endereço usável → ocultar com status.

## Gates para a v4.3

1. Zero registros visíveis com coordenada >60 km do centróide do município declarado.
2. Zero registros visíveis sem município validado (ocultos por status explícito até re-geocodificação).
3. Toda promoção de versão roda a auditoria municipal automaticamente (`scripts/audit_municipal.py`, a criar).
4. Sanitização por chave E valor (padrão v4.2) mantida.
5. Auditoria de água (ray-casting) e municipal como gates de release.

## Pendências de credenciais

- API key do Google (tipo "Chave de API", não OAuth client) com Geocoding API + Places API (New) habilitadas e faturamento ativo. OAuth client secret exposto no chat: rotacionar.
