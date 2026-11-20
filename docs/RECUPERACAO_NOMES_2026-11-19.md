# Recuperação de nomes do Ilê Axé Map — 19/11/2026

## Resultado auditado
- 1.238 ocorrências v3 com nome exato "Sem nome": 1.237 CNPJ e 1 de outra fonte.
- 1.016 nomes recuperados documentalmente no arquivo CNPJ geocodificado a partir de CEP unívoco e coordenadas concordantes.
- 221 registros CNPJ mais 1 registro de outra fonte permanecem com nome por identificar.
- 1.237 ocorrências CNPJ da v3 foram reduzidas a 700 grupos no algoritmo v4; **537 registros foram associados a outro ponto**, sem prova de identidade. O CSV destino_537.csv traz índice do agrupado e o representante, inclusive nomes recuperados em ambos.
- 61 casos apresentam UF divergente entre a base v3 e o cadastro CNPJ; a UF original não foi alterada.
- 66 "Não informado" CEAO e 24 "Terreiro Sem Nome" de outra fonte são placeholders adicionais fora das 1.238 ocorrências exatas em análise.

## Arquivos
- `antes_depois_1238.csv`: auditoria por ocorrência com nome antigo/novo e razão para pendência.
- `destino_537.csv`: rastreio individual das 537 incorporações anteriores, reconstruídas pela regra de agrupamento da v4.
- `pendencias_sem_chave.csv`: 222 registros não solucionados, preservados.
- `auditoria_recuperacao.json`: totais e regras.
- `terreiros_nacional_v4_9_candidata.geojson`: base de revisão, com 8.573 registros (8.036 - 700 agrupados + 1.237 ocorrências originais). Não é a base pública.

## Segurança da recuperação
O commit `a9b909230013ce37b24a0c91ebf617fabe7b102b` da main está intacto; a branch existente `correcao-nomes-auditoria-2026-11-19` serve de área de trabalho. Não modificar v3, v4 ou v4.8 publicados. Os novos IDs `rec_cnpj_v3_XXXXXX` representam ocorrências reconstruídas, e não validações de identidade real. O novo GeoJSON não é ligado ao site.

A correspondência do CEP foi feita **somente quando único tanto na v3 quanto na fonte CNPJ**, com coordenadas coincidentes e nome preenchido. O agrupamento por distância/nome genérico **não é evidência** de que dois terreiros sejam o mesmo.

**Pendências:** revisar as 222 ocorrências sem identificação e a geografia, validar a fonte registral com a comunidade e confirmar que os 1.016 nomes oficiais correspondem aos nomes de uso dos terreiros antes da publicação definitiva. Não fazer merge automático da base candidata.
