# AXÉS — plataforma do LHS/UnB (DF) — fonte externa incorporada em 24/11/2026

## O que é
Plataforma "AXÉS" (comunidades, acervo, "sobre"), ligada ao Laboratório de Habilidades
Sociais da UnB, com cadastro autodeclarado de casas de matriz africana. Endpoint público
lista **8 comunidades, todas no Distrito Federal** (Ceilândia, Recanto das Emas,
Sobradinho II, Núcleo Bandeirante, Paranoá, Brasília, Tororó).

- Site: <https://lhs.unb.br/axes-social/communities>
- Dados: `GET https://lhs.unb.br/axes/communities` (JSON paginado: `communities`, `total`, `page`)
- Coleta: 24/11/2026. Registros criados entre jun/2026 e ago/2026.

## Arquivos
| arquivo | conteúdo |
|---|---|
| `raw_communities.json` | payload cru (telefone, e-mail, endereço e nome do dirigente) — **gitignored, só local** |
| `axes_unb.csv` | tabela normalizada **sem** telefone/e-mail/endereço/dirigente (só booleanos de disponibilidade e a região administrativa) |
| `axes_unb.geojson` | camada normalizada, `versao: v5_staging`, sem dados pessoais |
| `geocode_cache.json` | respostas do Nominatim usadas na geocodificação (contém os endereços) — **gitignored** |

## Campos da fonte
`id, name, description, creatorId, numberOfMembers, privacyType, foundationYear,
leadershipName, religion, nation, fullAddress, locationType, membersCount,
matrixLineage, foundationHistory, socialProjects, phone, email, websiteOrSocialMedia,
createdAt, updatedAt, show* (flags de exibição), creator`

Riqueza qualitativa alta: **8/8** com história de fundação, **6/8** com projetos sociais,
**8/8** com ano de fundação, **8/8** com dirigente e linha religiosa.

## Proveniência e limites
1. **Cadastro autodeclarado** (a própria casa cria a comunidade; há usuário criador
   identificado por `creatorId`/`creator.name`). Não é diretório comercial.
2. **Sem coordenadas no payload.** Geocodificação aproximada por Nominatim a partir de
   endereços livres: 1 obteve nível de endereço; 6 caíram em centroide de região
   administrativa (fraco); 1 sem coordenada. **Nenhuma coordenada desta camada deve ser
   publicada como localização exata** sem verificação.
3. **Um registro é a própria plataforma** ("Atlas dos Terreiros", Campus Darcy Ribeiro,
   criado em 2026) — marcado `categoria: projeto/plataforma`, a excluir de camadas publicáveis.
4. **Dados pessoais:** telefone (8/8), e-mail (7/8) e redes (6/8) publicados pela plataforma,
   além de endereço completo e nome do dirigente. Política do Ilê Axé Map (v4.7): nada disso
   entra em camadas publicáveis. O CSV só registra `publica_contato: true/false` e a região
   administrativa; o payload bruto e o cache de geocodificação ficam **fora do Git** (`.gitignore`).
5. **Sem licença de uso declarada**; uso acadêmico com atribuição e contato prévio com a equipe.

## Situação frente à base (v5)
- A v4.8 tinha **7 registros no DF**; nenhuma das 8 comunidades casa por nome com eles.
- Na v5 (`scripts/build_v5.py`), entram **7 entidades**: as 8 comunidades menos o registro da
  própria plataforma ("Atlas dos Terreiros", categoria `projeto/plataforma`).
- **Todas as 7 entram ocultas por padrão**, porque a fonte não fornece coordenadas: 6 estão em
  centróide de região administrativa e 1 no centróide do município. Aparecem quando o usuário
  desmarca "Ocultar localizações aproximadas" — e o painel de detalhe diz isso explicitamente.
- Valor principal não é volume: são **fichas descritivas** (história, projetos sociais,
  linhagem) que servem de modelo de campo e de fonte qualitativa para verbetes.

## Reproduzir
```bash
python3 scripts/ingest_axes_unb.py         # coleta + normaliza + geocodifica (Nominatim, 1 req/s)
python3 scripts/audit_new_sources_v5.py    # auditoria contra v4.8
```
