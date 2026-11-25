# Ilê Axé Map

Mapa aberto de terreiros de candomblé e espaços religiosos afro-brasileiros no Brasil.
**Versão 5.0** — camada de 25 de novembro de 2026.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24529233.svg)](https://doi.org/10.5281/zenodo.24529233)

Base arquivada no Zenodo (acesso restrito, licença CC BY-NC 4.0): DOI **10.5281/zenodo.24529233**.
Este é o *concept DOI* — cita a versão mais recente. Para citar exatamente a v5, use 10.5281/zenodo.24529234.

- **Mapa:** https://labhdufba.github.io/ile-axe-map/
- **Nota técnico-metodológica:** https://labhdufba.github.io/ile-axe-map/metodologia.html
- **Como colaborar:** https://labhdufba.github.io/ile-axe-map/colaborar.html

## Dataset v5

8.215 entidades, resultado da consolidação de fontes públicas heterogêneas. Os totais por
fonte contam registros por ocorrência: uma entidade presente em duas fontes aparece nas duas
linhas, e por isso a soma excede o total.

| Fonte | Registros |
|---|---|
| Mapeando Axé | 3.814 |
| CNPJ/Receita Federal | 1.951 |
| CEAO/UFBA | 1.111 |
| Google Places (Places API e Geocoding API) | 748 |
| CEAP — Mapa do Axé | 280 |
| SEMUR/SEFAZ-Salvador | 223 |
| Atlas do Axé (Amazonas) | 172 |
| OpenStreetMap | 133 |
| AXÉS/LHS-UnB (Distrito Federal) | 7 |

Sobre a fonte SEMUR/SEFAZ-Salvador: o cadastro da rede municipal de terreiros (886 registros,
atualizado em 2020) é publicado pela Prefeitura de Salvador no GeoSalvador —
<https://www.sefaz.salvador.ba.gov.br/geosalvador/home/item.html?id=1ff59c26223c43769751b874b8316e11>.
A publicação municipal é de **uso irrestrito, com duas condições**: vedada a comercialização dos
dados e obrigatória a citação da Prefeitura Municipal do Salvador como fonte. O PDF cartográfico
usado no OCR não fica no repositório: consulte o original no link acima.

A interface carrega `data/v5/terreiros_nacional_v5.geojson`. As versões anteriores ficam
preservadas em `data/v4_8/` e nos demais diretórios `data/v*`, de modo que qualquer publicação
é reversível. `data/v5_staging/` é histórico do processo, substituído pela v5.

### O que o mapa não faz

- Não é censo, cadastro oficial nem inventário exaustivo: cada ponto é um registro consolidado,
  com graus diferentes de completude e validação.
- Não infere nação, tradição ou orixá a partir de nome, endereço ou vizinhança. Campo vazio
  permanece vazio e aparece como "ficha incompleta" na interface.
- Não publica nome de dirigente, telefone, e-mail, redes sociais nem endereço completo.
- Não publica localização aproximada sem avisar: aproximações ficam ocultas por padrão e o
  painel de detalhe declara a precisão do ponto (`geo_status`).

## Estrutura

```text
├── index.html              mapa, painel Sobre e fichas
├── colaborar.html          canal de contribuição
├── metodologia.html        nota técnico-metodológica (versão vigente)
├── data/
│   ├── v5/                 camada publicada + auditoria da integração
│   ├── v4_8/               versão anterior (rollback)
│   ├── atlas_axe/          camada normalizada do Amazonas + README de proveniência
│   ├── axes_unb/           camada normalizada do DF + README de proveniência
│   └── ...                 fontes e artefatos por versão
├── scripts/                coleta, geocodificação, auditoria e build
├── tests/                  testes das etapas de build e coleta
└── docs/                   roteiro do formulário, notas operacionais
```

## Regerar a camada publicada

```bash
python3 scripts/ingest_atlas_axe.py     # Atlas do Axé (AM)
python3 scripts/ingest_axes_unb.py      # AXÉS/LHS-UnB (DF)
python3 scripts/build_v5.py             # v4.8 + fontes novas → data/v5/
python3 -m unittest discover -s tests -v
```

`scripts/build_v5.py` lê a base anterior e não a altera; a auditoria da integração fica em
`data/v5/auditoria_v5.json`, e as regras de merge estão em `data/v5/README.md`.

## Acesso aos dados

A base completa está depositada no Zenodo com **metadados públicos e arquivos restritos**: o registro é citável e o DOI resolve, mas o download exige solicitação, atendida pela curadoria do LABHD/UFBA para pesquisa, ensino e formulação de políticas públicas, com atribuição e sem uso comercial (CC BY-NC 4.0). A restrição existe para impedir a republicação da base como produto próprio — não para limitar pesquisa. O mapa interativo segue público.

A leitura programática é feita por uma API com recorte geográfico e paginação (`api/worker/`), que não oferece rota de download integral.

## Privacidade e proteção de dados

O repositório é público, então a política é aplicada na origem: payloads brutos das fontes que
trazem contatos, dirigentes ou endereços completos ficam **fora do Git** (ver `.gitignore`), e as
camadas publicadas não contêm esses campos. Pedidos de correção, inclusão ou exclusão são
atendidos por `ileaxemap@gmail.com`; a exclusão não exige justificativa e tem compromisso de
tratamento em até 7 dias. Critérios na
[Seção 8.1 da metodologia](https://labhdufba.github.io/ile-axe-map/metodologia.html#81-canal-de-solicitacao).

## Stack

- Leaflet 1.9.4 + Leaflet.markercluster 1.5.3 (via CDN)
- HTML, CSS e JavaScript sem etapa de build
- GitHub Pages

As páginas `revisao-google.html`, `nacional.html` e os arquivos `validation_*.html` são
ferramentas históricas de curadoria e permanecem no repositório como registro do processo.

## Equipe

- **Coordenação:** Leonardo Nascimento
- **Pesquisadores:** Eric Brasil · Luciana Duccini · Ricardo Andrade · Rosana Moore
- **Estudantes:** Caroline Barros · Daniel Sena · Lidia Belas · Taíse Cruz
- **Design gráfico:** Ícaro Bernardes
- **Apoio e autoria:** Darlan Gomes ([@abacostecnologia](https://www.instagram.com/abacostecnologia/)) · Ábaco

## Citação

> NASCIMENTO, Leonardo Fernandes et al. **Ilê Axé Map: base consolidada de terreiros de candomblé
> e espaços religiosos afro-brasileiros no Brasil**. Versão 5. DOI: 10.5281/zenodo.24529233.
> Salvador: LABHD/UFBA, 2026. Disponível em: https://labhdufba.github.io/ile-axe-map/.

## Responsabilidade

Laboratório de Humanidades Digitais da Universidade Federal da Bahia (LABHD/UFBA).
Contato: ileaxemap@gmail.com.
