# Recuperação de nomes CNPJ — segunda passagem (19/11/2026)

## Resultado da revisão automatizada
- A v3 continha **1.238** ocorrências com nome exato `Sem nome`: 1.237 da origem CNPJ e 1 de outra fonte.
- Primeira passagem: **1.016** nomes documentais candidatos identificados.
- Segunda passagem: **43** nomes adicionais entre CEPs não unívocos, aceitos apenas quando a combinação **CEP + coordenadas** aparece exclusivamente na fonte geocodificada e entre *todos* os registros de origem CNPJ da v3, sem conflito na mesma coordenada.
- Nova contagem: **1.059 CNPJ nomeados** e **178 CNPJ pendentes**. Incluindo a fonte não CNPJ, **179 pendências no escopo**.
- Total v4.9 candidata permanece **8.573** pontos, com **537 registros que foram agrupados indevidamente reconstituídos individualmente**.
- Entre as 43 novas correspondências, **5** possuem UF divergente. A UF original foi mantida, para revisão.

## Rastreabilidade
- `scripts/build_v4_9_nomes.py`: reconstrução original, sempre a partir da v3 e v4.8.
- `scripts/completar_nomes_v49_correspondencia.py`: segunda passagem, sobre o GeoJSON reconstruído.
- `data/v4_9_candidata/antes_depois_1238.csv`: evidência individual de recuperação.
- `data/v4_9_candidata/destino_537.csv`: representantes e agrupamentos reconstituídos.
- `data/v4_9_candidata/pendencias_sem_chave.csv`: somente pendências restantes.
- `data/v4_9_candidata/auditoria_recuperacao.json`: números e critérios.
- `data/v4_9_candidata/terreiros_nacional_v4_9_candidata.geojson`: base experimental.

## Segurança e publicação
A branch `snapshot-v49-antes-segunda-recuperacao-2026-11-19` preserva o trabalho anterior no commit `1b1953ad2351376bf5ebb687bf3dbcc1b75cc5e7`.
O mapa público e a branch `main` não foram modificados por este trabalho.

**Não publicar/mesclar automaticamente.** A coincidência de coordenadas em dados geocodificados não equivale a identificação comunitária. Todos os 1.059 nomes são candidatos documentais e devem ser revisados segundo a fonte, e discrepâncias de UF/localização requerem atenção. Não forçar atribuições nos 179 registros sem identidade comprovada.
