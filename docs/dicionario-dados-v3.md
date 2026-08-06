# Dicionário de dados v3

Este documento descreve a entidade canônica de terreiro usada na unificação nacional v3. O contrato executável está em `schemas/terreiro-v3.schema.json` e usa JSON Schema Draft 2020-12.

## Convenções

- Todos os objetos canônicos rejeitam propriedades não declaradas.
- Campos anuláveis aceitam `null` quando a informação não está disponível.
- Todas as chaves listadas nos objetos canônicos são obrigatórias, inclusive quando o campo é anulável.
- `entity_id` segue `trr_<identificador estável>`. O trecho após `trr_` pode conter letras, números, `_` e `-`.
- Cada entidade registra ao menos uma fonte.
- Datas de coleta, quando disponíveis, usam uma data de calendário válida no formato `AAAA-MM-DD`. Fontes legadas sem essa informação usam `null`.
- `confianca` varia de 0 a 1, inclusive.

## Campos da entidade

### Identificação canônica

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `entity_id` | string | sim | Identificador canônico estável, por exemplo `trr_ceao_123`. |

### `nome`

| Campo | Tipo | Anulável | Descrição |
|---|---|---:|---|
| `preferido` | string não vazia | não | Nome escolhido para exibição e referência canônica. |
| `aliases` | array de strings não vazias | não | Outras grafias ou nomes associados, sem duplicatas. |
| `normalizado_match` | string não vazia | não | Forma normalizada usada somente para comparação e reconciliação. |

### `localizacao`

| Campo | Tipo | Anulável | Descrição |
|---|---|---:|---|
| `latitude` | número entre -90 e 90 | sim | Latitude em graus decimais. |
| `longitude` | número entre -180 e 180 | sim | Longitude em graus decimais. |
| `fonte_coordenada` | string | sim | Fonte da coordenada adotada. |
| `precisao` | string | sim | Qualificação da precisão espacial informada pelo processo de origem. |
| `uf` | string com 2 letras maiúsculas | sim | Sigla da unidade federativa. |
| `municipio` | string | sim | Nome do município. |
| `codigo_ibge_municipio` | string com 7 dígitos | sim | Código IBGE do município, preservando zeros à esquerda. |
| `bairro` | string | sim | Bairro ou localidade equivalente. |
| `cep` | string | sim | CEP conforme recebido ou normalizado pelo pipeline. |
| `endereco_original` | string | sim | Endereço textual antes da decomposição em campos. |
| `status_territorial` | enum | não | Resultado da avaliação territorial. |

Valores de `status_territorial`:

- `intersecao_ibge`: a coordenada intersecta o polígono territorial esperado.
- `fora_poligono`: há coordenada, mas ela não intersecta o polígono esperado.
- `sem_coordenada`: latitude e longitude não estão disponíveis e devem ser `null`.

`intersecao_ibge` e `fora_poligono` exigem latitude e longitude numéricas. Nenhum status aceita apenas uma coordenada. Além disso, `intersecao_ibge` exige `uf` com duas letras maiúsculas, `municipio` não vazio e `codigo_ibge_municipio` com sete dígitos.

### `identidade_religiosa`

| Campo | Tipo | Anulável | Descrição |
|---|---|---:|---|
| `tradicao_declarada` | string | sim | Tradição conforme declaração da fonte. |
| `nacao_declarada` | string | sim | Nação conforme declaração da fonte, sem substituir o valor original. |
| `componentes` | array de strings não vazias | não | Componentes identificados em uma declaração composta. |
| `categoria_analitica` | string | sim | Categoria derivada para análise. |
| `metodo` | enum | não | Método que produziu a categoria analítica. |
| `revisao_humana` | enum | não | Situação da revisão humana da classificação. |

Valores de `metodo`:

- `declarado`
- `normalizado_declaracao`
- `inferido_nome`
- `ausente`

Valores de `revisao_humana`:

- `aprovado`
- `pendente`
- `nao_aplicavel`

Quando `metodo` é `ausente`, `tradicao_declarada`, `nacao_declarada` e `categoria_analitica` devem ser `null`, `componentes` deve ser vazio e `revisao_humana` deve ser `nao_aplicavel`. Quando `metodo` é `inferido_nome`, `categoria_analitica` deve ser uma string não vazia e `revisao_humana` deve ser `pendente` ou `aprovado`.

### `identificadores`

| Campo | Tipo | Anulável | Descrição |
|---|---|---:|---|
| `cnpj` | string | sim | CNPJ associado ao terreiro. |
| `ceao_id` | string | sim | Identificador no cadastro do CEAO. |
| `osm_id` | string | sim | Identificador do elemento no OpenStreetMap. |
| `google_place_id` | string | sim | Place ID do Google. |

### `fontes[]`

O array deve conter ao menos um item. Cada item possui:

| Campo | Tipo | Anulável | Descrição |
|---|---|---:|---|
| `fonte` | string não vazia | não | Nome estável da fonte, por exemplo `ceao`, `osm` ou `google`. |
| `id_fonte` | string não vazia | não | Identificador do registro dentro da fonte. |
| `url` | string | sim | URL de consulta ou referência do registro. |
| `campos_contribuidos` | array de caminhos canônicos | não | Campos folha canônicos contribuídos pela fonte, sem duplicatas. |
| `data_coleta` | string `AAAA-MM-DD` ou `null` | sim | Data de calendário válida em que o registro foi coletado; fontes legadas podem não informar a data. |

Os únicos valores aceitos em `campos_contribuidos` são:

- `entity_id`
- `nome.preferido`, `nome.aliases`, `nome.normalizado_match`
- `localizacao.latitude`, `localizacao.longitude`, `localizacao.fonte_coordenada`, `localizacao.precisao`, `localizacao.uf`, `localizacao.municipio`, `localizacao.codigo_ibge_municipio`, `localizacao.bairro`, `localizacao.cep`, `localizacao.endereco_original`, `localizacao.status_territorial`
- `identidade_religiosa.tradicao_declarada`, `identidade_religiosa.nacao_declarada`, `identidade_religiosa.componentes`, `identidade_religiosa.categoria_analitica`, `identidade_religiosa.metodo`, `identidade_religiosa.revisao_humana`
- `identificadores.cnpj`, `identificadores.ceao_id`, `identificadores.osm_id`, `identificadores.google_place_id`
- `qualidade.status_validacao_geografica`, `qualidade.confianca`, `qualidade.flags`, `qualidade.grupo_reconciliacao`

Objetos contêiner, campos de proveniência em `fontes[]`, `valores_originais` e caminhos inexistentes não são contribuições canônicas válidas.

### `qualidade`

| Campo | Tipo | Anulável | Descrição |
|---|---|---:|---|
| `status_validacao_geografica` | enum | não | Síntese da validação geográfica. |
| `confianca` | número entre 0 e 1 | não | Confiança agregada na entidade reconciliada. |
| `flags` | array de strings não vazias | não | Sinais de qualidade ou pendências, sem duplicatas. |
| `grupo_reconciliacao` | string | sim | Identificador do grupo de registros considerado na reconciliação. |

Valores de `status_validacao_geografica`:

- `confirmado`
- `provavel`
- `inconclusivo`

Entidades com `status_territorial` igual a `sem_coordenada` devem usar `status_validacao_geografica` igual a `inconclusivo`. O valor `confirmado` exige latitude e longitude numéricas.

### `valores_originais`

`valores_originais` é uma lista não vazia que preserva campos que existem nas fontes, mas não pertencem ao contrato canônico. Isso evita liberar propriedades arbitrárias no topo ou nos demais objetos da entidade. Cada item possui exatamente três chaves:

| Campo | Tipo | Anulável | Descrição |
|---|---|---:|---|
| `fonte` | string não vazia | não | Nome estável da fonte. |
| `id_fonte` | string não vazia | não | Identificador do registro dentro da fonte. |
| `dados` | objeto JSON livre | não | Conteúdo interno recebido da origem, com propriedades e estruturas arbitrárias. |

O vínculo com o registro de origem é definido pelo par (`fonte`, `id_fonte`). Assim, uma entidade pode preservar dois ou mais registros da mesma fonte, desde que tenham identificadores distintos. A unicidade desse par é verificada pelo builder, pois JSON Schema não expressa unicidade composta de forma simples. Exemplo:

```json
{
  "valores_originais": [
    {
      "fonte": "ceao",
      "id_fonte": "123",
      "dados": {
        "NOME": "Ilê Axé Exemplo",
        "NACAO": "Keto"
      }
    },
    {
      "fonte": "ceao",
      "id_fonte": "456",
      "dados": {
        "NOME": "Outra ficha vinculada à mesma entidade"
      }
    }
  ]
}
```

A preservação nesse campo não implica que o valor original foi escolhido para um campo canônico. A contribuição efetiva é registrada em `fontes[].campos_contribuidos`.

`valores_originais` é conteúdo interno de proveniência e jamais deve ser exportado diretamente para o GeoJSON ou HTML público. Toda publicação deve selecionar apenas campos autorizados e filtrar contatos, dados pessoais e demais campos sensíveis presentes em `dados`.
