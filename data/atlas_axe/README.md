# Atlas do Axé (Amazonas) — fonte externa incorporada em 24/11/2026

## O que é
Plataforma "Atlas do Axé — Terreiros e Templos do Amazonas" (app web/PWA, publicado no
Lovable), com **177 casas de matriz africana** em **10 municípios do AM**, sendo 152 em
Manaus. Camadas previstas: casas de axé e comércio de artigos religiosos (a segunda com
2 registros "a confirmar"); "profissionais da cultura criativa" ainda não publicada.

- Site: <https://atlasdoaxe.lovable.app/>
- Dados: server function pública `GET /_serverFn/1465697dfd8c8cb40d565648cbc66d2d3a8c4e398eb8d504d9e573abf898aa5b`
  (exige apenas o header `x-tsr-serverFn: true`); resposta em serialização própria do
  TanStack Start, decodificada por `scripts/ingest_atlas_axe.py`.
- `atualizadoEm` declarado: 24/11/2026 21:18 UTC.

## Arquivos
| arquivo | conteúdo |
|---|---|
| `raw_payload.json` | resposta crua do endpoint (fidelidade/proveniência) — **gitignored: contém nome de dirigente** |
| `casas.json` | payload decodificado (177 registros, 15 campos) — **gitignored** |
| `atlas_axe.geojson` | camada normalizada no esquema do Ilê Axé Map (`versao: v5_staging`), sem dados pessoais |

## Campos da fonte
`id, nome, lideranca, tradicao, nacao, categoria, municipio, uf, bairro, lat, lng,
precisao, situacao, autoriza, mapsUrl`

Distribuições:
- tradição: Candomblé 74 · Umbanda 70 · não especificado 24 · Tambor de Mina 7 · Umbanda e Mina 2
- categoria: terreiro/templo 174 · loja de artigos (a confirmar) 2 · associação/entidade 1
- precisão declarada: alta (ponto do Google Maps) 157 · aproximada pelo endereço 9 · baixa (≈100 m) 7 · sem coordenada 4
- `situacao`: "A verificar" em **100%** dos registros — a própria fonte declara que os dados estão em verificação junto às casas.

## Regra de inclusão (decisão de 24/11/2026)
O mapa é de **casas de axé**, não de comércio religioso. Ficam fora da camada normalizada
as categorias de loja (`EXCLUIR_CATEGORIAS` em `scripts/ingest_atlas_axe.py`):
- *Casa São José* — loja de artigos religiosos (a confirmar)
- *Tenda Pai Xangô Compensa* — loja de artigos religiosos (a confirmar)

Os dois registros continuam no payload bruto (recuperáveis) e a exclusão é reversível por
parâmetro. Resultado: **175 registros na camada** (171 com coordenada), dos quais 1 é
"Associação / entidade" — mantido, pendente de decisão.

## Proveniência e limites (leitura crítica)
1. **Origem declarada:** "planilhas do projeto", atualizadas manualmente. Não há indicação
   pública de quem mantém a planilha, metodologia de coleta ou consentimento por casa.
2. **Coordenadas:** a maioria tem precisão "alta (ponto do Google Maps)" e `mapsUrl` aponta
   para busca por lat/lng — padrão compatível com geocodificação/verificação via Google,
   não necessariamente com endereço confirmado pela casa.
3. **Estado do dado:** tudo "a verificar" → tratar como *lista de candidatos*, não como
   cadastro validado.
4. **Dados pessoais:** não há telefone/e-mail/endereço completo no payload; existe `lideranca`
   (nome do dirigente). Política do projeto (v4.7): nome de dirigente não entra em camada
   publicável — o campo foi removido do GeoJSON e o payload bruto fica **fora do Git**
   (`.gitignore`), apenas local.
5. **Sem licença de uso declarada.** Uso acadêmico com atribuição; não redistribuir a
   camada bruta sem contato com a equipe do Atlas.

## Situação frente à base v4.8
- Base v4.8 tem **8 registros no AM** (5 CNPJ + 3 CEAP, vários com coordenada de município repetida).
- Auditoria conservadora (`scripts/audit_new_sources_v5.py`): **173 dos 175 são novos**;
  2 casam com a base (ILÊ AXÉ BARÁ LONÃ; Ilê Axé de Dan).
- Impacto: o AM passa de 8 para ~181 registros — a maior lacuna regional da base atual.
- Staging resultante: 8.036 + 173 (AM) + 8 (DF) = **8.217**.

## Reproduzir
```bash
python3 scripts/ingest_atlas_axe.py        # coleta + normaliza
python3 scripts/audit_new_sources_v5.py    # auditoria contra v4.8 + staging
```
