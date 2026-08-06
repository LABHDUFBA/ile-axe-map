# Source record v3

`source-record-v3` é o contrato intermediário interno entre cada registro-fonte e a futura reconciliação canônica. Cada ocorrência gera um registro, sem deduplicação, fusão ou exclusão nesta etapa. O schema normativo está em `schemas/source-record-v3.schema.json`.

## Identidade estável

`normalize_source_id` aceita somente `string` não vazia, após remover espaços das extremidades, ou inteiro não booleano. Zeros à esquerda de IDs textuais são preservados. Valores nulos, booleanos, floats, vazios e estruturais são rejeitados para evitar IDs ambíguos.

`make_source_record_key(fonte, id_fonte)` produz `<fonte>:<id_codificado>`. O ID usa percent-encoding dos bytes UTF-8 com `urllib.parse.quote(..., safe="")`. Assim, `:`, `%`, `/` e Unicode não criam chaves ambíguas. A operação inversa usa a primeira `:` como separador e `urllib.parse.unquote` no restante.

Quando a fonte não oferece ID nativo, `synthetic_source_id` calcula SHA-256 sobre JSON canônico no formato `{"fonte": ..., "partes": [...]}`. Cada parte carrega uma tag explícita de tipo e seu valor original. São aceitos texto não vazio, inteiro não booleano, float finito, booleano e nulo. Estruturas e floats não finitos são rejeitados. A serialização usa UTF-8, chaves ordenadas e separadores compactos. Isso preserva tipos e fronteiras: `1`, `"1"`, `1.0` e `true` geram hashes distintos, assim como `("ab", "c")` e `("a", "bc")`.

## Estrutura e validação

O helper `build_base_source_record` monta todos os objetos e campos obrigatórios. Ele não infere tradição, nação ou denominação. `nome_original` aceita somente texto não vazio após trim ou nulo. `data_coleta` aceita somente uma data real em `YYYY-MM-DD` ou nulo. Coordenadas principais devem estar ambas presentes ou ambas nulas, ser finitas, não booleanas e respeitar as faixas globais. Coordenadas alternativas sempre exigem latitude e longitude globais válidas, fonte não vazia e precisão textual ou nula. Overrides parciais de `flags_auditoria` são mesclados com as cinco flags padrão; chaves desconhecidas e valores não booleanos são rejeitados.

O registro retornado não compartilha referências mutáveis com os argumentos. `dados_originais`, coordenadas alternativas, flags e demais valores são copiados profundamente, portanto mutações posteriores no payload de entrada não alteram o registro.

O JSON Schema valida CNPJ somente como `string|null`. O builder chama `valid_cnpj` para todo CNPJ não nulo. A função aceita máscara padrão ou 14 dígitos e verifica os dois dígitos verificadores. Os demais identificadores aceitam somente texto ou nulo.

Validações de `date` e `uri` exigem `jsonschema.Draft202012Validator` com `jsonschema.FormatChecker()`. URLs aceitas são somente HTTP(S) absolutas com hostname não vazio. Domínios, IPv4, `localhost`, portas, userinfo não vazio, caminho, query, fragmento e IPv6 entre colchetes são aceitos sem consultar DNS.

## Privacidade

`dados_originais` preserva o objeto recebido da fonte, inclusive campos arbitrários e aninhados. Ele pode conter dados sensíveis. Tanto `dados_originais` quanto o futuro `data/canonical/v3/source_records.jsonl` são **internos** e nunca devem ser publicados ou versionados. Fixtures e testes devem usar somente payloads sintéticos.
