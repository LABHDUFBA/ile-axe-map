# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Público principal:** comunidades de terreiro e pessoas afetadas — usam o mapa para verificar se sua comunidade está representada, correta e tratada com respeito; podem pedir inclusão, alteração ou **exclusão** (esta sem exigência de justificativa, prazo de 7 dias, por qualquer pessoa afetada ou representante).
- **Públicos secundários:** pesquisadores (sociologia, religião, estudos afro-diaspóricos), jornalistas, gestores de política pública e estudantes interessados na distribuição territorial dos espaços religiosos afro-brasileiros.
- Contexto de uso típico: navegação por interesse e afeto, não por tarefa burocrática; inclui acesso por celular em conexões variadas.

## Product Purpose

O Ilê Axé Map é um atlas público, gratuito e de código aberto dos terreiros de candomblé e espaços religiosos afro-brasileiros do Brasil. Sua finalidade é dar **visibilidade sociotécnica** a comunidades historicamente invisibilizadas nos mapas oficiais, com proveniência transparente de cada registro e um canal público de correção pelas próprias comunidades. O sucesso significa: cobertura confiável, zero exposição de dados pessoais, uso real por pesquisadores e solicitações comunitárias processadas dentro dos prazos.

## Positioning

É o único mapa nacional de terreiros que combina: (a) triagem metodológica auditável por fonte e evidência, (b) modelagem entidade ↔ ocorrência com proveniência explícita, e (c) política assimétrica de solicitações em que a exclusão tem prioridade e menor atrito que a inclusão — o mapa existe para servir às comunidades, não para maximizar registros.

## Operating Context

- Publicado via GitHub Pages em `labhdufba.github.io/ile-axe-map/` a partir do repo `LABHDUFBA/ile-axe-map` (branch `main`); site público único é `index.html` (v4 nacional), `nacional.html` apenas redireciona.
- Ciclo de release obrigatório: build candidata → auditoria por código → revisão do Leonardo → deploy → verificação em produção com cache-busting. Nenhuma mudança vai direto à produção.
- Idioma: português do Brasil em toda a interface e documentação.
- O dataset é servido apenas via fetch interno da página; o método de publicação preserva os dados brutos sensíveis localmente (gitignored).

## Capabilities and Constraints

- **Versão pública atual: v4.1** — `data/v4_1/terreiros_nacional_v4_1.geojson`, 8.036 entidades em todo o Brasil; filtros por fonte, nação e UF; ocultação de localizações aproximadas ativada por padrão.
- Fontes com rank de confiabilidade: CEAO/UFBA (prioridade de coordenada), OpenStreetMap (ODbL, triagem religião explícita), CNPJ/dados abertos da Receita (evidência textual religiosa + geocode de precisão forte), CEAP (fonte comunitária com crédito), solicitação comunitária.
- **Vedações de privacidade (inegociáveis):** o GeoJSON público jamais contém CNPJ, razão social, endereço, CEP, telefone, e-mail ou query de geocodificação; nenhum link público de download do dataset; IDs pessoais crus nunca aparecem em relatórios públicos.
- **Recorte territorial:** Brasil (nacional desde a v4). Toda adição exige evidência religiosa explícita; metadados religiosos conflitantes implicam exclusão, nunca "correção".
- Canal de solicitações: Google Form (placeholder até Leonardo criar o form real — nunca inventar URL) + e-mail leofn@ufba.br; respostas em planilha privada; decisões registradas em artefato de auditoria interno sem dados pessoais.
- Cores dos filtros servem à navegação e não representam parentesco entre tradições; declarações de nação permanecem literais (Keto, Alaketo, Jêje Nagô, compostos), sem inferência por nome.

## Brand Commitments

- Nome: **Ilê Axé Map** (grafar "LABHDUFBA" para o laboratório, nunca "INOVALab").
- Tom: respeitoso, claro e acessível; linguagem não-excludente; nada de exotização da religião afro-brasileira.
- Logo LABHDUFBA (`assets/labhd-logo.webp`) e favicon próprio.

## Evidence on Hand

- GeoJSON público v4.1 com 8.036 entidades e auditoria por fonte; metodologia publicada em `metodologia.html` (deve sempre refletir a release vigente).
- `docs/nota_tecnica_metodologica.md`, `docs/roteiro-google-form.md`, `README.md` e `METODOLOGIA.md` no repo.
- Ausências a não fabricar: nenhuma estatística de público, depoimento de comunidade ou patrocínio existe; não citar números além dos das auditorias versionadas.

## Product Principles

1. **As comunidades primeiro:** o mapa presta contas às pessoas que representa; exclusão tem menos atrito que inclusão.
2. **Proveniência acima de volume:** um registro só entra com evidência religiosa explícita e geocode forte; melhor faltar do que falsificar presença.
3. **Privacidade por construção:** sanitização por código e por valor (regex), não por conferência visual.
4. **Auditoria antes de público:** nenhuma versão é promovida sem gates automatizados e revisão do Leonardo.
5. **A interface serve à navegação afetiva:** performance em celular e clareza vencem sofisticação visual.

## Accessibility & Inclusion

- Público majoritariamente mobile, incluindo conexões lentas: performance e legibilidade em telas pequenas são requisito de inclusão, não refinamento.
- Contraste e hierarquia tipográfica adequados para leitura prolongada na metodologia; alvo prático WCAG 2.1 AA nos controles do mapa.
