# Source record v3

`source-record-v3` é o contrato intermediário interno entre cada registro-fonte e a futura reconciliação canônica. Cada ocorrência gera um registro, sem deduplicação, fusão ou exclusão nesta etapa. O schema normativo está em `schemas/source-record-v3.schema.json`.

## Identidade estável

`normalize_source_id` remove somente espaços nas extremidades e converte escalares para texto. Zeros à esquerda de IDs textuais são preservados. Valores nulos, vazios e estruturais são rejeitados.

`make_source_record_key(fonte, id_fonte)` produz `<fonte>:<id_codificado>`. O ID usa percent-encoding dos bytes UTF-8 com `urllib.parse.quote(..., safe="")`. Assim, `:`, `%`, `/` e Unicode não criam chaves ambíguas. A operação inversa usa a primeira `:` como separador e `urllib.parse.unquote` no restante.

Quando a fonte não oferece ID nativo, `synthetic_source_id` calcula SHA-256 sobre JSON canônico no formato `{"fonte": ..., "partes": [...]}`. As partes são normalizadas individualmente, a serialização usa UTF-8, chaves ordenadas e separadores compactos. Isso preserva fronteiras, portanto `("ab", "c")` não colide com `("a", "bc")`. É obrigatória ao menos uma parte, e nenhuma pode ser vazia, nula ou estrutural.

## Estrutura e validação

O helper `build_base_source_record` monta todos os objetos e campos obrigatórios. Ele não infere tradição, nação ou denominação. Coordenadas principais devem estar ambas presentes ou ambas nulas. Coordenadas alternativas sempre exigem latitude e longitude globais válidas, fonte não vazia e precisão textual ou nula.

O JSON Schema valida CNPJ somente como `string|null`. Adaptadores devem chamar `valid_cnpj`, que aceita CNPJ com máscara padrão ou 14 dígitos e verifica os dois dígitos verificadores.

Validações de `date` e `uri` exigem `jsonschema.Draft202012Validator` com `jsonschema.FormatChecker()`.

## Privacidade

`dados_originais` preserva o objeto recebido da fonte, inclusive campos arbitrários e aninhados. Ele pode conter dados sensíveis. Tanto `dados_originais` quanto o futuro `data/canonical/v3/source_records.jsonl` são **internos** e nunca devem ser publicados ou versionados. Fixtures e testes devem usar somente payloads sintéticos.
