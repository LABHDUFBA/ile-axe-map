# Ilê Axé Map — encerramento técnico dos 179 casos restantes

**Data:** 19/11/2026
**Repositório de trabalho:** `1aifa/ile-axe-map`
**Branch:** `correcao-nomes-auditoria-2026-11-19`
**Validação GitHub Actions:** https://github.com/1aifa/ile-axe-map/actions/runs/44561074940

## Resultado
- **178 nomes adicionais recuperados** no CSV CNPJ geocodificado original.
- **1.237 de 1.237 registros CNPJ originalmente sem nome agora nomeados documentalmente:** primeira passagem 1.016, segunda 43, terceira 178.
- **0 CNPJ sem nome.**
- **1 registro de outra fonte permanece sem nome oficial fornecido pela fonte**: v3 índice 7488; Mapeando Axé 2010, `source_record_id=130`.
- **537 registros anteriormente agrupados** reconstituídos como pontos separados; agora os 537 têm nomes CNPJ documentais.
- **8.573 pontos na base candidata** (não publicada).
- **105 divergências de UF** entre registros antigos e fonte CNPJ; mantida a UF original.
- Na terceira passagem, 81/178 coordenadas concordaram com a fonte e **97/178 divergiram**, permanecendo sem correção automática. A identidade foi reconstruída pela ordenação da fonte, não pela geolocalização.

## Método para os 178 casos
O segmento da v3 com índices 1271 a 3712 contém 2.442 registros CNPJ. O arquivo original `data/cnpj/geocoding/terreiros_cnpj_geocoded.csv` contém 2.673 registros. A sequência de CEPs dos 2.442 forma uma subsequência exata da origem, preservada após filtragens/exclusões. O script reconstrói o alinhamento independentemente da esquerda para a direita e da direita para a esquerda. Somente são atribuídos nomes quando ambos chegam à mesma linha da fonte. 

**Controles:** 2.440 posições são unívocas. As outras 2 são posições de registros que já tinham nome, não pertencem aos 178 pendentes. **1.203 controles de registros nomeados e de posição unívoca** tiveram concordância literal com razão social ou nome fantasia da fonte. Todos os 178 restantes possuem posição única, CNPJ distinto e nome preenchido. Os 1.059 recuperados antes também foram confrontados com a ordem original, sem discordância de nome.

A recuperação resulta em **nomes documentais candidatos**, não substitui a revisão do nome de uso, da categoria de casa/associação, da geografia e a validação comunitária.

## Último caso sem nome oficial
**Índice v3:** 7488
**Fonte:** `data/mapeando_axe/processed/mapeando_axe_2010_geocoded_complete.json` — registro de origem `130`
**Nome da casa no registro de origem:** vazio
**Liderança declarada:** Iracema Pereira dos Reis
**Regentes registrados:** Dona Conceição e Sapa Encantada
**Endereço declarado:** Rua Magalhães Barata, 130, Vila Nova — Ilha de Cotijuba, Belém, PA
**Atenção geográfica:** geocodificação de rua cai em Outeiro, enquanto endereço menciona Cotijuba
**Ação de curadoria:** consulta direta à comunidade, à fonte Mapeando Axé ou pesquisa primária para identificar o nome utilizado. Não criar nome de casa a partir da pessoa dirigente. O registro permanece localizável por liderança, referência da fonte e endereço nos metadados.

## Arquivos resultantes
- `data/v4_9_candidata/terreiros_nacional_v4_9_candidata.geojson`
- `data/v4_9_candidata/antes_depois_1238.csv`
- `data/v4_9_candidata/destino_537.csv`
- `data/v4_9_candidata/recuperacao_sequencial_178.csv`
- `data/v4_9_candidata/pendencias_sem_chave.csv` (1 registro)
- `data/v4_9_candidata/identidade_sem_nome_oficial_mapeando_axe_130.json`
- `data/v4_9_candidata/auditoria_recuperacao.json`
- `scripts/recuperar_nomes_v49_alinhamento_original.py`

## Preservação e publicação
- `main` permanece no commit `a9b909230013ce37b24a0c91ebf617fabe7b102b`.
- Snapshot da versão candidata anterior à terceira passagem: `snapshot-v49-antes-alinhamento-final-2026-11-19`, commit `50cdfdaf942b7c0ce2ebec398c62aba24804d4f1`.
- A versão candidata **não está publicada**, nem deve ser mesclada automaticamente.
- Há ainda **90 rótulos genéricos fora do escopo exato de 1.238** (`Não informado` CEAO 66 e `Terreiro Sem Nome` outra fonte 24), que requerem auditoria própria.
