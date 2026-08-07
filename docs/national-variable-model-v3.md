# Proposta inicial de modelo nacional de variáveis v3

## Escopo e evidência

Este documento propõe um formato nacional comum a partir do inventário real de sete fontes. Ele não fecha o schema final e não altera o schema canônico existente. A referência empírica é `data/audit/v3/source_variable_matrix.csv`, produzida por `scripts/v3/inventory_source_variables.py`.

O inventário validou os hashes e as contagens declaradas em `config/source_manifests_v3.json` antes da análise. O total lógico bruto é 8.815 registros:

| Fonte lógica | Registros | Caminhos de campo inventariados |
|---|---:|---:|
| mapeando_axe | 3.923 | 16 |
| cnpj | 2.673 | 15 |
| terreiros_brasil | 260 | 14 |
| ceao | 1.155 | 28 |
| bahia_google | 550 | 20 |
| osm | 20 | 20 |
| sefaz | 234 | 16 |
| **Total** | **8.815** | **129 linhas fonte + caminho** |

O agregado Bahia tem 1.959 registros e foi separado pelo campo `fonte`: CEAO 1.155, Google 550, OSM 20 e SEFAZ 234. A separação é estrita, sem deduplicar, excluir ou copiar registros entre fontes.

## Regras obrigatórias

1. Todas as entidades nacionais devem expor os mesmos campos comuns.
2. Uma variável não coletada pela fonte deve ser representada por `null`. Ausência não autoriza preencher a partir de nome, endereço, coordenada, outra fonte ou regra heurística.
3. Imputação silenciosa é proibida. Um valor inferido precisa estar explicitamente marcado como inferido, com método, versão, data e revisão humana quando aplicável.
4. Valores distintos de fontes diferentes permanecem ligados à sua proveniência. Harmonização não apaga o valor declarado.
5. Normalização cria uma representação adicional. Ela não substitui nem reescreve o declarado.
6. Variáveis exclusivas úteis entram no formato comum. Estruturas de transporte e variáveis estritamente específicas permanecem no payload original.
7. Contatos, liderança e consultas de geocodificação são internos por padrão. Publicação exige controle explícito por campo e finalidade.
8. Esta etapa não escolhe entidade canônica, nome preferido, coordenada vencedora ou fonte mais confiável.
9. Resultados de geocodificação são dados auxiliares inferidos. Não provam identidade, não criam identificador da entidade e não substituem endereço ou coordenada declarada ou canônica.

## Estados de um valor

Cada valor harmonizado deve distinguir três estados:

- **declarado**: copiado da fonte, sem interpretação semântica. Pode receber limpeza estritamente representacional, desde que o original permaneça preservado.
- **normalizado**: derivado mecanicamente do declarado, com regra e versão registradas. Exemplos futuros incluem máscara de CEP, UF em caixa alta e representação padronizada de data.
- **inferido**: produzido por classificação, geocodificação, reconciliação ou outra regra analítica. Nunca deve ocupar um campo declarado e sempre exige método explícito.

Uma forma conceitual, ainda não normativa, é manter para cada contribuição `fonte`, `id_fonte`, `campo_original`, `valor_declarado`, `valor_normalizado`, `valor_inferido`, `metodo`, `data_coleta` e flags de qualidade/publicação. Os valores reais continuam no registro operacional, não nos artefatos de auditoria deste inventário.

## Grupos e campos nacionais propostos

### 1. Identificação e nome

- `nome.preferido`: futuro campo de apresentação, sempre `null` até uma etapa explícita de reconciliação escolhê-lo.
- `nome.declarado`: recebe `name`, `nome` e `nome_fantasia`, com contribuições separadas por fonte.
- `nome.juridico_declarado`: recebe `razao_social`.
- `nome.aliases`: lista futura, não formada automaticamente nesta etapa.
- `identificacao.descricao_declarada`: incorpora a descrição exclusiva útil de Terreiros do Brasil.

Não equiparar automaticamente nome fantasia, razão social e nome religioso.

### 2. Identificadores

- `identificadores.cnpj`
- `identificadores.ceao_id`
- `identificadores.osm_id`, reservado para um identificador nativo da entidade confirmado na fonte OSM
- `identificadores.google_place_id`, previsto no modelo, mas ausente no agregado Bahia atual
- `identificadores.sefaz_codigo`
- `identificadores.id_nativo`, sempre com namespace da fonte
- `proveniencia.fontes_relacionadas[].fonte` e `.id`

`nominatim_osm_id` não contribui para `identificadores.osm_id`: ele identifica somente o objeto devolvido pelo geocodificador. Google e OSM não preservam seus IDs nativos no agregado atual, portanto eles devem ficar `null`, sem fabricação retrospectiva.

### 3. Localização e endereço

- `localizacao.endereco_declarado`
- `localizacao.logradouro_declarado`
- `localizacao.numero_declarado`
- `localizacao.complemento_declarado`, previsto, sem fonte contribuinte identificada
- `localizacao.bairro_declarado`
- `localizacao.municipio_declarado`
- `localizacao.uf_declarada`
- `localizacao.codigo_municipio_declarado`, candidato pendente de validação do domínio cadastral
- `localizacao.cep_declarado`
- `localizacao.latitude`
- `localizacao.longitude`
- `localizacao.precisao`, somente quando qualifica coordenada do registro integrado

As coordenadas `lat` e `lng` do agregado Bahia e de Terreiros do Brasil permanecem classificadas como coordenadas dos respectivos registros integrados, com sua origem documentada. Já `lat`, `lng` e `precision` do input CNPJ são saídas de geocodificação. `codigo_municipio` não é chamado de IBGE: seu domínio precisa ser confirmado antes de qualquer normalização.

### 4. Geocodificação auxiliar

- `geocodificacao.resultado.latitude`
- `geocodificacao.resultado.longitude`
- `geocodificacao.resultado.osm_id`
- `geocodificacao.resultado.osm_tipo`
- `geocodificacao.resultado.endereco`
- `geocodificacao.consulta`, interno por padrão
- `geocodificacao.status`
- `geocodificacao.precisao`
- `geocodificacao.confianca`
- `geocodificacao.tipo_endereco`

Esses campos recebem as saídas Nominatim de Mapeando Axé e as saídas de geocodificação do input CNPJ. A regra `inferido_geocodificacao` exige proveniência do processo. O resultado pode apoiar revisão e localização, mas não comprova que o objeto retornado é o terreiro, não substitui coordenada ou endereço da entidade e não fornece ID nativo da entidade.

### 5. Identidade religiosa

- `identidade_religiosa.tradicao_declarada`, previsto, sem contribuição inequívoca na matriz atual
- `identidade_religiosa.nacao_declarada`
- `identidade_religiosa.denominacao_declarada`, previsto, sem contribuição inequívoca na matriz atual
- `identidade_religiosa.categoria_declarada`
- `identidade_religiosa.linhagem_declarada`, previsto, sem campo identificado
- `identidade_religiosa.componentes`
- `identidade_religiosa.nacao_normalizada`
- `identidade_religiosa.categoria_normalizada`

`nacao` e `nacao_original` mantêm `identidade_religiosa.nacao_declarada` apenas como destino candidato e ficam em revisão. É preciso validar por fonte se representam declaração da organização, descrição editorial ou classificação de terceiro. Os campos `nacao_categoria`, `nacao_componentes`, `nacao_primaria` e `metodo_classificacao` do agregado Bahia são derivados e também permanecem em revisão.

### 6. Organização e história

- `organizacao.lideranca_declarada`
- `organizacao.regente_declarado`
- `organizacao.data_inicio_cadastral_declarada`, candidato em revisão
- `organizacao.ano_fundacao_declarado`
- `organizacao.situacao_cadastral`, previsto, sem campo inequívoco identificado

`data_inicio` da fonte CNPJ é preservada como data de início cadastral declarada e pendente. Ela nunca é tratada como fundação religiosa sem confirmação semântica da fonte. Liderança e regência são internas por padrão.

### 7. Patrimônio e reconhecimento

Campos nacionais previstos:

- `patrimonio.tombamento`
- `patrimonio.cadastro_reconhecimento`
- `patrimonio.protecao`
- `patrimonio.orgao`
- `patrimonio.ato_data`

Nenhuma variável inequívoca destes temas foi encontrada nas sete fontes atuais. Todos devem permanecer `null`. Não inferir reconhecimento a partir da presença no CEAO, SEFAZ ou outro cadastro.

### 8. Contato, mídia e controle de publicação

- `contato.telefone_declarado`
- `contato.email_declarado`, previsto, sem campo identificado
- `contato.site_declarado`, previsto, sem campo identificado
- `midia.imagem_principal_url`
- `midia.miniatura_url`
- `publicacao.permitir_contato`
- `publicacao.permitir_lideranca`
- `publicacao.permitir_localizacao_precisa`
- `publicacao.permitir_midia`

Telefone foi inventariado, mas não deve ser publicado por padrão. URLs de fotos entram como variáveis comuns úteis, ainda sujeitas a direitos, persistência do link e política de publicação.

### 9. Proveniência e qualidade

- `proveniencia.fonte`
- `proveniencia.id_fonte`
- `proveniencia.url_registro`
- `proveniencia.descricao_fonte`
- `proveniencia.data_coleta`
- `proveniencia.metodo_recuperacao`
- `qualidade.status_geografico`
- `qualidade.metodo_classificacao`
- `qualidade.avaliacao_fonte`
- `qualidade.quantidade_avaliacoes_fonte`
- `qualidade.flags`

Rating e quantidade de avaliações são métricas específicas de plataforma. Podem ocupar campos nacionais de qualidade com proveniência, mas sua comparabilidade e validade temporal precisam de revisão.

## Achados da matriz

- Foram identificadas 129 combinações de fonte e caminho original, correspondentes a 50 campos nacionais candidatos após agrupamento semântico. O JSON separa contribuições aprovadas de pendentes e preserva regra e status de cada fonte-campo.
- Os inputs são majoritariamente planos. O único array aninhado observado no conjunto Bahia é `fontes[]`, inventariado com marcador `[]` determinístico.
- `rating` apresenta `int` e `float` em Google e CEAO. O modelo futuro deve aceitar número sem perder a representação original.
- Existem 24 combinações fonte-campo presentes na estrutura, mas sem nenhum valor preenchido. Presença estrutural não deve ser confundida com coleta efetiva.
- A avaliação recursiva de vazio não alterou essas contagens no snapshot: listas e objetos estruturais observados ou contêm algum valor real, ou já estavam vazios. `false` e `0` continuam preenchidos.
- SEFAZ possui `lat` e `lng` estruturais sem preenchimento no snapshot. Esses campos nacionais permanecem `null` para seus registros.
- Campos úteis exclusivos encontrados incluem descrição, método de recuperação, imagens, consulta de geocodificação, confiança e tipo de endereço do geocodificador.
- Os contêineres `fontes` e `fontes[]` são preservados no payload original; somente seus filhos semânticos são candidatos ao formato comum.

## Lacunas e decisões para revisão humana

1. Definir o protocolo de escolha de `nome.preferido` sem apagar nomes concorrentes.
2. Confirmar se `codigo_municipio` é sempre código IBGE e qual versão territorial se aplica.
3. Distinguir data de abertura cadastral, início de atividade e fundação religiosa.
4. Determinar se `nacao`, `nacao_original` e `categoria_raw` são declarações da organização, descrições editoriais ou classificações de terceiros em cada fonte.
5. Auditar a origem e a regra dos campos derivados do agregado Bahia antes de reutilizá-los.
6. Definir autoridade e prioridade entre coordenadas originais e geocodificadas.
7. Recuperar IDs nativos de Google e OSM somente a partir das fontes correspondentes, nunca por inferência no agregado.
8. Definir escalas e validade temporal de confiança, rating e avaliações.
9. Estabelecer política de consentimento e publicação para telefone, liderança, coordenada precisa e imagens.
10. Definir campos de patrimônio com fontes especializadas, pois a matriz atual não os coleta.
11. Decidir se descrição e mídia fazem parte do núcleo nacional ou de extensões comuns opcionais. Mesmo opcionais, devem existir como `null` em todas as entidades se adotadas.
12. Só após essas decisões converter a proposta em schema final e adapters.

## Reprodutibilidade e privacidade

O CSV e o JSON de cobertura contêm somente caminhos de campos, tipos, contagens, percentuais, hashes e mapeamentos semânticos. Eles não contêm nomes, endereços, telefones, CNPJs, coordenadas nem exemplos de payload. O script ordena fontes, caminhos, tipos e chaves JSON, usa seis casas decimais para cobertura e termina arquivos com quebra de linha, permitindo reprodução byte a byte.
