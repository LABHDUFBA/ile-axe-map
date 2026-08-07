# Dicionário de dados v3

Este documento descreve o formato nacional comum e experimental da entidade canônica v3. O contrato executável usa JSON Schema Draft 2020-12 em `schemas/terreiro-v3.schema.json`. O catálogo determinístico de campos fica em `config/national_fields_v3.json`.

## Regras do contrato nacional

- Todos os grupos e todas as chaves nacionais são obrigatórios. Objetos estruturais usam `additionalProperties: false`.
- Um slot não coletado deve existir com valor `null`. A chave nunca pode ser omitida, preenchida com string vazia, inventada ou inferida silenciosamente.
- Em arrays nacionais anuláveis, `null` significa **não coletado** e `[]` significa **coletado explicitamente sem itens**. Essa distinção vale, por exemplo, para `nome.aliases`, `identidade_religiosa.componentes`, `proveniencia.fontes_relacionadas` e `qualidade.flags`.
- `entity_id` é a exceção técnica à anulabilidade: permanece obrigatório, não vazio e no formato `trr_<id estável>`, preservando a identidade aprovada na T1.
- `fontes` e `valores_originais` permanecem listas não vazias. `valores_originais[].dados` é o único payload livre e preserva integralmente o registro recebido.
- Contato, liderança, regência, consulta de geocodificação, mídia e coordenada precisa são internos ou controlados. `publicacao.*` precisa de decisão explícita. `null` não concede publicação e nenhum dado é publicável por padrão.
- O schema reserva slots. Um adapter futuro só poderá preenchê-los por mapeamento aprovado e contribuição rastreável. Os mapeamentos `revisar` da matriz/cobertura continuam pendentes e não viram fatos.

## Grupos obrigatórios

| Grupo | Finalidade |
|---|---|
| `entity_id` | Identidade canônica estável. |
| `identificadores` | Identificadores nativos ou confirmados por fonte. |
| `nome` e `identificacao` | Nomes declarados, futuros valores reconciliados e descrição. |
| `localizacao` | Endereço e coordenada próprios da entidade. |
| `geocodificacao` | Resultado auxiliar de geocodificador, sem substituir localização. |
| `identidade_religiosa` | Declarações, normalizações e classificação revisável. |
| `organizacao` | Liderança, regência, situação e história. |
| `patrimonio` | Tombamento, reconhecimento e proteção. |
| `contato` e `midia` | Dados internos ou de publicação controlada. |
| `publicacao` | Consentimentos explícitos por categoria sensível. |
| `fontes` e `proveniencia` | Origem dos registros e metadados da recuperação. |
| `qualidade` | Avaliações geográficas, classificação e sinais de qualidade. |
| `contribuicoes_campos` | Valores concorrentes com proveniência por campo. |
| `valores_originais` | Payload original completo e interno. |
| `revisao` | Situação e registro de revisão humana. |

## Estados e escolha de valores

- **declarado**: copiado da fonte sem interpretação semântica.
- **normalizado**: representação adicional produzida por regra mecânica versionada.
- **inferido**: produzido por geocodificação, classificação ou outra regra analítica, sempre com método explícito.
- **canônico**: valor eventualmente escolhido por uma etapa futura de reconciliação. Este contrato não elege valor canônico.

`contribuicoes_campos[]` preserva valores concorrentes sem sobrescrita. Cada item exige `campo_nacional`, `fonte`, `id_fonte`, `campo_original`, `estado`, `valor` não nulo e `publicavel`; `metodo`, `versao`, `data_coleta`, `qualidade` e `status` existem e podem ser `null`. `campo_nacional` só aceita caminhos do catálogo. O array pode ser vazio enquanto não houver contribuições materializadas.

`fontes[].campos_contribuidos` também usa os caminhos do catálogo. Isso registra que uma fonte contribuiu para um slot, mas não significa que o valor foi eleito canônico.

## Geocodificação auxiliar

`localizacao.latitude` e `localizacao.longitude` pertencem à entidade integrada. `geocodificacao.resultado.latitude` e `.longitude` pertencem ao objeto devolvido pelo geocodificador. Da mesma forma, `geocodificacao.resultado.osm_id` identifica apenas o resultado auxiliar e nunca pode preencher automaticamente `identificadores.osm_id`. Consulta, método, versão e estado inferido devem permanecer rastreáveis.

## História cadastral e religiosa

`organizacao.data_inicio_cadastral_declarada` não é sinônimo de `organizacao.ano_fundacao_declarado`. A primeira preserva uma data cadastral ainda sujeita a revisão semântica; a segunda representa fundação religiosa declarada. Nenhum adapter pode copiar uma para a outra sem regra aprovada.

## Catálogo do formato nacional

`status` tem três valores: `aprovado`, `revisar` e `reservado_sem_fonte`. O último mantém um slot comum em todas as entidades mesmo sem fonte contribuinte atual. A coluna de publicação usa `publico`, `interno` ou `controlado`; ela classifica o slot e não concede publicação de um valor concreto.

| Caminho | Tipo lógico | Nullable | Status | Publicação |
|---|---|---:|---|---|
| `contato.email_declarado` | string | sim | reservado_sem_fonte | interno |
| `contato.site_declarado` | string | sim | reservado_sem_fonte | interno |
| `contato.telefone_declarado` | string | sim | aprovado | interno |
| `entity_id` | string | não | aprovado | publico |
| `geocodificacao.confianca` | number | sim | aprovado | publico |
| `geocodificacao.consulta` | string | sim | revisar | interno |
| `geocodificacao.precisao` | string | sim | aprovado | publico |
| `geocodificacao.resultado.endereco` | string | sim | aprovado | publico |
| `geocodificacao.resultado.latitude` | number | sim | aprovado | publico |
| `geocodificacao.resultado.longitude` | number | sim | aprovado | publico |
| `geocodificacao.resultado.osm_id` | string | sim | aprovado | publico |
| `geocodificacao.resultado.osm_tipo` | string | sim | aprovado | publico |
| `geocodificacao.status` | string | sim | aprovado | publico |
| `geocodificacao.tipo_endereco` | string | sim | revisar | publico |
| `identidade_religiosa.categoria_analitica` | string | sim | reservado_sem_fonte | publico |
| `identidade_religiosa.categoria_declarada` | string | sim | aprovado | publico |
| `identidade_religiosa.categoria_normalizada` | string | sim | revisar | publico |
| `identidade_religiosa.componentes` | array | sim | revisar | publico |
| `identidade_religiosa.denominacao_declarada` | string | sim | reservado_sem_fonte | publico |
| `identidade_religiosa.linhagem_declarada` | string | sim | reservado_sem_fonte | publico |
| `identidade_religiosa.metodo` | enum | sim | reservado_sem_fonte | publico |
| `identidade_religiosa.nacao_declarada` | string | sim | revisar | publico |
| `identidade_religiosa.nacao_normalizada` | string | sim | revisar | publico |
| `identidade_religiosa.revisao_humana` | enum | sim | reservado_sem_fonte | publico |
| `identidade_religiosa.tradicao_declarada` | string | sim | reservado_sem_fonte | publico |
| `identificacao.descricao_declarada` | string | sim | aprovado | publico |
| `identificadores.ceao_id` | string | sim | aprovado | publico |
| `identificadores.cnpj` | string | sim | aprovado | publico |
| `identificadores.google_place_id` | string | sim | reservado_sem_fonte | publico |
| `identificadores.id_nativo` | string | sim | aprovado | publico |
| `identificadores.osm_id` | string | sim | reservado_sem_fonte | publico |
| `identificadores.sefaz_codigo` | string | sim | aprovado | publico |
| `localizacao.bairro` | string | sim | reservado_sem_fonte | publico |
| `localizacao.bairro_declarado` | string | sim | aprovado | publico |
| `localizacao.cep` | string | sim | reservado_sem_fonte | publico |
| `localizacao.cep_declarado` | string | sim | aprovado | publico |
| `localizacao.codigo_ibge_municipio` | string | sim | reservado_sem_fonte | publico |
| `localizacao.codigo_municipio_declarado` | string | sim | revisar | publico |
| `localizacao.complemento_declarado` | string | sim | reservado_sem_fonte | controlado |
| `localizacao.endereco_declarado` | string | sim | aprovado | controlado |
| `localizacao.endereco_original` | string | sim | reservado_sem_fonte | controlado |
| `localizacao.fonte_coordenada` | string | sim | reservado_sem_fonte | publico |
| `localizacao.latitude` | number | sim | aprovado | controlado |
| `localizacao.logradouro_declarado` | string | sim | aprovado | controlado |
| `localizacao.longitude` | number | sim | aprovado | controlado |
| `localizacao.municipio` | string | sim | reservado_sem_fonte | publico |
| `localizacao.municipio_declarado` | string | sim | aprovado | publico |
| `localizacao.numero_declarado` | string | sim | aprovado | controlado |
| `localizacao.precisao` | string | sim | aprovado | publico |
| `localizacao.status_territorial` | enum | sim | reservado_sem_fonte | publico |
| `localizacao.uf` | string | sim | reservado_sem_fonte | publico |
| `localizacao.uf_declarada` | string | sim | aprovado | publico |
| `midia.imagem_principal_url` | string | sim | aprovado | controlado |
| `midia.miniatura_url` | string | sim | aprovado | controlado |
| `nome.aliases` | array | sim | reservado_sem_fonte | publico |
| `nome.declarado` | string | sim | aprovado | publico |
| `nome.juridico_declarado` | string | sim | aprovado | publico |
| `nome.normalizado_match` | string | sim | reservado_sem_fonte | publico |
| `nome.preferido` | string | sim | reservado_sem_fonte | publico |
| `organizacao.ano_fundacao_declarado` | string | sim | aprovado | publico |
| `organizacao.data_inicio_cadastral_declarada` | string | sim | revisar | publico |
| `organizacao.lideranca_declarada` | string | sim | aprovado | interno |
| `organizacao.regente_declarado` | string | sim | aprovado | interno |
| `organizacao.situacao_cadastral` | string | sim | reservado_sem_fonte | publico |
| `patrimonio.ato_data` | string | sim | reservado_sem_fonte | publico |
| `patrimonio.cadastro_reconhecimento` | string | sim | reservado_sem_fonte | publico |
| `patrimonio.orgao` | string | sim | reservado_sem_fonte | publico |
| `patrimonio.protecao` | string | sim | reservado_sem_fonte | publico |
| `patrimonio.tombamento` | string | sim | reservado_sem_fonte | publico |
| `proveniencia.data_coleta` | string | sim | reservado_sem_fonte | publico |
| `proveniencia.descricao_fonte` | string | sim | aprovado | publico |
| `proveniencia.fonte` | string | sim | aprovado | publico |
| `proveniencia.fontes_relacionadas[].fonte` | string | sim | aprovado | publico |
| `proveniencia.fontes_relacionadas[].id` | string | sim | aprovado | publico |
| `proveniencia.id_fonte` | string | sim | reservado_sem_fonte | publico |
| `proveniencia.metodo_recuperacao` | string | sim | aprovado | publico |
| `proveniencia.url_registro` | string | sim | aprovado | publico |
| `publicacao.permitir_contato` | boolean | sim | reservado_sem_fonte | controlado |
| `publicacao.permitir_lideranca` | boolean | sim | reservado_sem_fonte | controlado |
| `publicacao.permitir_localizacao_precisa` | boolean | sim | reservado_sem_fonte | controlado |
| `publicacao.permitir_midia` | boolean | sim | reservado_sem_fonte | controlado |
| `qualidade.avaliacao_fonte` | number | sim | revisar | publico |
| `qualidade.confianca` | number | sim | reservado_sem_fonte | publico |
| `qualidade.flags` | array | sim | reservado_sem_fonte | publico |
| `qualidade.grupo_reconciliacao` | string | sim | reservado_sem_fonte | publico |
| `qualidade.metodo_classificacao` | string | sim | revisar | publico |
| `qualidade.quantidade_avaliacoes_fonte` | integer | sim | revisar | publico |
| `qualidade.status_geografico` | string | sim | aprovado | publico |
| `qualidade.status_validacao_geografica` | enum | sim | reservado_sem_fonte | publico |
| `revisao.data` | string | sim | reservado_sem_fonte | publico |
| `revisao.observacoes` | string | sim | reservado_sem_fonte | publico |
| `revisao.responsavel` | string | sim | reservado_sem_fonte | publico |
| `revisao.status` | enum | sim | reservado_sem_fonte | publico |

## Proveniência original e privacidade

Cada item de `valores_originais` contém exatamente `fonte`, `id_fonte` e `dados`. O par (`fonte`, `id_fonte`) vincula o payload à origem. Integridade referencial e unicidade entre listas continuam responsabilidades do builder/adapter, pois não são expressas de forma simples no JSON Schema.

`valores_originais`, contatos, liderança, regência, consultas de geocodificação e demais dados sensíveis não devem ser exportados diretamente para GeoJSON, HTML ou outra saída pública. A publicação deve selecionar somente campos autorizados e verificar os controles de `publicacao` e `publicavel` da contribuição.

O catálogo contém apenas caminhos, tipos, estados e pares fonte/campo original extraídos da cobertura. Não contém nomes, endereços, contatos, identificadores, coordenadas nem outros valores reais.
