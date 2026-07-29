# Nota técnico-metodológica

## Ilê Axé Map — Terreiros de Candomblé e espaços religiosos afro-brasileiros da Bahia

**Versão do conjunto de dados:** 1.3<br>
**Data de extração e integração:** 25 de julho de 2026<br>
**Responsabilidade:** Leonardo Fernandes Nascimento — Laboratório de Humanidades Digitais da Universidade Federal da Bahia (LABHD/UFBA)<br>
**Repositório:** <https://github.com/LABHDUFBA/ile-axe-map><br>
**Mapa:** <https://labhdufba.github.io/ile-axe-map/>

> **Nota de leitura.** O Ilê Axé Map não constitui um censo, um cadastro oficial nem um inventário exaustivo das comunidades religiosas afro-brasileiras da Bahia. Trata-se de uma infraestrutura cartográfica de pesquisa que integra registros oriundos de fontes públicas heterogêneas. Cada ponto representa um **registro consolidado**, com diferentes graus de completude e validação — não a certificação definitiva da existência, da identidade religiosa ou da situação atual de uma comunidade.

---

## 1. Finalidade e escopo

O **Ilê Axé Map** é um atlas digital de acesso público dedicado à reunião, à organização e à visualização de informações públicas sobre terreiros de candomblé e outros espaços religiosos afro-brasileiros relacionados à Bahia. O projeto procura reduzir a dispersão informacional entre bases institucionais, plataformas cartográficas e cadastros de natureza distinta, oferecendo uma camada integrada para consulta, pesquisa e documentação.

A proposta combina três objetivos:

1. **documental**, ao aproximar registros que se encontram fragmentados em diferentes fontes;
2. **analítico**, ao permitir a observação exploratória de distribuições territoriais, lacunas de cobertura e diferenças entre bases;
3. **infraestrutural**, ao disponibilizar dados e código em formatos inspecionáveis, passíveis de crítica, correção e atualização.

O universo empírico é formado por ocorrências recuperadas em quatro fontes: OpenStreetMap, Google Places, Centro de Estudos Afro-Orientais da Universidade Federal da Bahia (CEAO/UFBA) e levantamento da Secretaria Municipal da Reparação de Salvador, distribuído pela SEFAZ/Salvador. Essas fontes não foram produzidas com a mesma finalidade, no mesmo período ou segundo os mesmos critérios. Sua integração, portanto, não elimina as diferenças de origem: torna-as metodologicamente visíveis.

A unidade básica do projeto é o **registro de fonte**. Após normalização, comparação e deduplicação, um ou mais registros podem ser reunidos em uma única entrada consolidada. Essa operação é técnica e probabilística: comunidades distintas podem apresentar nomes semelhantes, enquanto a mesma comunidade pode aparecer com grafias, endereços ou coordenadas diferentes.

---

## 2. Síntese quantitativa da versão 1.3

Os números abaixo foram apurados a partir dos artefatos efetivamente preservados no repositório e da contagem dos registros contidos nos arquivos — e não apenas dos metadados declarativos de versões anteriores.

### 2.1. Composição por fonte

| Fonte | Registros materializados antes da consolidação entre fontes | Registros na base consolidada v1.3 | Registros com coordenadas na camada cartográfica |
|---|---:|---:|---:|
| OpenStreetMap | 44 | 20 | 20 |
| Google Places | 1.408 | 693 | 693 |
| CEAO/UFBA | 1.155 | 682 | 682 |
| SEMUR — SEFAZ/Salvador | 635 | 234 | 0 |
| **Total** | **3.242** | **1.629** | **1.395** |

A coluna inicial descreve as ocorrências persistidas nos artefatos que antecederam a consolidação entre fontes. Ela não deve ser confundida com o número transitório de respostas produzidas pelas APIs durante a coleta. A coluna intermediária registra a fonte principal do registro sobrevivente após a deduplicação; ela não preserva, na versão atual, toda a cadeia de sobreposições entre fontes.

Os totais de **1.629 registros consolidados** e **1.395 feições publicadas** foram recalculados diretamente dos arrays presentes no commit auditado. Os blocos de metadados internos de `data/terreiros_all_sources.json` e `data/terreiros.geojson` ainda conservam contagens de etapas anteriores e não devem ser utilizados como retrato da versão corrente.

### 2.2. Fluxo de processamento

```text
3.242 ocorrências materializadas nas quatro fontes
        │
        ├── normalização e deduplicação entre fontes
        ▼
2.158 registros consolidados
        │
        ├── remoção heurística de 499 falsos positivos prováveis
        ▼
1.659 registros após a limpeza semântica
        │
        ├── remoção de 30 registros externos ao recorte operacional
        ▼
1.629 registros na base consolidada v1.3
        │
        ├── 1.395 registros com coordenadas no recorte operacional da Bahia
        └──   234 registros SEMUR sem coordenadas extraídas
```

O total de **1.629 registros** não equivale a 1.629 terreiros presencialmente verificados. Ele expressa o resultado atual de um pipeline de integração, deduplicação e filtragem. Os **1.395 pontos cartográficos** correspondem ao subconjunto com coordenadas que permaneceu após a aplicação do recorte territorial operacional.

---

## 3. Fontes e procedimentos de aquisição

### 3.1. OpenStreetMap

O OpenStreetMap (OSM) é uma base geográfica colaborativa e aberta. A coleta foi realizada por meio da **Overpass API**, com uma consulta composta por diferentes combinações de atributos e expressões nominais relacionadas ao universo de interesse. Entre os critérios empregados estão:

- `amenity=place_of_worship` associado a `religion=candomblé`;
- `amenity=place_of_worship` associado a `religion=afro_brazilian`;
- `denomination=candomblé`;
- nomes contendo expressões como *terreiro*, *candomblé*, *ilê axé*, *ilê asé* e *centro de umbanda*.

O coletor versionado consulta apenas objetos do tipo **nó** (`node`). Caminhos (`way`) e relações (`relation`) não integram essa rotina. O script converte os resultados para GeoJSON e preserva, quando disponíveis, identificador OSM, nome, categoria, denominação, endereço, telefone, sítio eletrônico e demais etiquetas de origem.

A camada pré-consolidação arquivada contém **44 registros OSM**; após a comparação com as demais fontes e a etapa de filtragem, **20 registros** permanecem na versão 1.3. Como o OpenStreetMap é continuamente editado, a repetição da consulta em outra data pode produzir resultados diferentes.

### 3.2. Google Places

A coleta no Google Places foi estruturada como uma busca textual multipassagem, combinando expressões relacionadas a terreiros e religiões afro-brasileiras com referências territoriais a municípios e localidades baianas. Entre as expressões registradas nos dados recuperados estão *terreiro de candomblé*, *candomblé*, *ilê*, *ilê asé*, *abassá*, *inzo*, *casa de santo*, *centro de candomblé* e *centro religioso afro-brasileiro*.

A camada persistida antes da consolidação contém **1.408 identificadores `place_id` distintos**. Os registros incluem, quando retornados pelo serviço, nome, endereço, coordenadas, categorias da plataforma, avaliação, número de avaliações, situação operacional, localidade e expressão de busca associada.

Após a deduplicação entre fontes, a filtragem de falsos positivos prováveis e a remoção de ocorrências externas ao recorte operacional, **693 registros atribuídos ao Google Places** permanecem na base consolidada.

A interface de busca do Google Places favorece entidades com presença digital e tende a incorporar estabelecimentos que apenas compartilham palavras frequentes com o vocabulário religioso — por exemplo, “casa”, “axé”, “santo” ou nomes de municípios. Por essa razão, os resultados dessa fonte foram submetidos a uma etapa específica de controle semântico, descrita na Seção 5.

O repositório preserva os resultados incorporados, mas não contém, na versão auditada, o script completo de coleta, os logs de paginação nem o histórico integral das requisições. A reprodução exata dessa etapa é, portanto, limitada.

### 3.3. CEAO/UFBA

A base pública **Mapeamento dos Terreiros de Salvador**, vinculada ao Centro de Estudos Afro-Orientais da UFBA, constitui a fonte de maior densidade histórico-descritiva do projeto. Seu universo declarado é a cidade de Salvador. As páginas preservadas utilizam uma estimativa populacional de 2005 e organizam os mapas históricos até o intervalo 2001–2006; esses marcadores situam temporalmente o levantamento, mas não permitem atribuir a todos os registros uma única data de observação. A extração digital para o Ilê Axé Map ocorreu em 2026 e não deve ser confundida com a produção original das informações.

Foram materializados **1.155 registros**, acompanhados, em diferentes níveis de completude, por campos como:

- nome da comunidade;
- liderança religiosa;
- nação ou tradição declarada;
- orixá ou entidade regente;
- ano de fundação;
- endereço, bairro e CEP;
- telefone;
- coordenadas geográficas;
- imagens em miniatura e em maior resolução.

No arquivo estruturado, **1.135 registros possuem referências preenchidas nos campos `foto_thumb` e `foto_grande`**, enquanto o repositório conserva **1.081 miniaturas fotográficas** obtidas durante a coleta. Referência remota e arquivo efetivamente preservado são, portanto, métricas distintas. Após a consolidação com as demais bases, **682 registros com atribuição principal ao CEAO/UFBA** permanecem na versão 1.3.

A redução entre os 1.155 registros de origem e os 682 registros atribuídos ao CEAO na base final não significa, por si só, exclusão de 473 comunidades. Parte dessas ocorrências foi agregada a registros considerados equivalentes durante a deduplicação, e a contagem final por fonte corresponde apenas à procedência principal preservada no registro sobrevivente.

### 3.4. SEMUR — SEFAZ/Salvador

A quarta fonte é um mapa cartográfico da **Secretaria Municipal da Reparação de Salvador (SEMUR)**, publicado em 2020 e distribuído pela infraestrutura geográfica da SEFAZ/Salvador. A lista nominal foi extraída por reconhecimento óptico de caracteres e revisão estrutural, resultando em **635 pares de código e nome**.

O documento original apresenta informação cartográfica em sistema UTM, fuso 24S, referida ao SIRGAS 2000. Essas coordenadas não foram extraídas para a versão atual. Em consequência, os registros SEMUR participam da base consolidada e do processo de deduplicação nominal, mas não aparecem como pontos no mapa interativo. Após a comparação com as demais fontes, **234 registros SEMUR sem coordenadas** permanecem na base v1.3.

A diferença entre contagens apresentadas em documentos derivados e a lista OCR deve ser tratada como questão de proveniência, não resolvida por simples inferência. A versão atual adota como referência operacional os 635 registros efetivamente estruturados no arquivo de origem preservado no repositório.

---

## 4. Normalização, integração e deduplicação

### 4.1. Padronização mínima

As quatro fontes utilizam esquemas distintos. O pipeline converte os registros para uma estrutura comum, preservando tanto quanto possível os campos originais. Entre as operações de normalização estão:

- uniformização dos campos de nome e fonte;
- conversão das coordenadas para longitude e latitude em WGS 84 quando já disponíveis em formato compatível;
- tratamento de caixa, acentuação e espaços para fins de comparação nominal;
- manutenção de atributos específicos de cada provedor, como `place_id`, identificadores OSM, identificadores CEAO e códigos SEMUR;
- geração de uma camada GeoJSON destinada à interface cartográfica e de um JSON consolidado que também comporta registros sem coordenadas.

A normalização utilizada para comparação não deve substituir a grafia pública ou histórica dos nomes. A diversidade ortográfica — *Ilê/Ilé/Ylê*, *Axé/Asé/Axê*, *Ketu/Keto*, entre outras variações — pode expressar tradições, escolhas institucionais e histórias próprias. Sempre que possível, o valor exibido deve permanecer fiel à fonte considerada principal.

### 4.2. Critérios de correspondência

A deduplicação combina proximidade geográfica e semelhança nominal. Segundo a documentação metodológica do pipeline, dois registros podem ser tratados como candidatos à mesma entidade quando ocorre pelo menos uma das seguintes condições:

1. distância inferior a 50 metros entre as coordenadas disponíveis;
2. igualdade dos nomes após normalização;
3. inclusão substancial de uma forma nominal na outra, desde que a sequência comparada tenha mais de cinco caracteres.

Quando há correspondência, procura-se conservar o registro com maior densidade informacional e incorporar campos complementares da outra ocorrência. Esse procedimento reduziu **3.242 ocorrências de fonte a 2.158 registros consolidados**, isto é, reuniu 1.084 ocorrências consideradas redundantes.

A equivalência produzida por esse método é uma hipótese operacional. A proximidade espacial não garante identidade institucional, sobretudo em territórios com forte concentração de comunidades religiosas; nomes semelhantes também podem designar casas distintas, linhagens relacionadas ou mudanças históricas de denominação. Inversamente, mudanças de endereço, abreviações e diferenças ortográficas podem impedir a reunião de registros que se referem à mesma comunidade.

### 4.3. Proveniência após a fusão

Na versão 1.3, o campo `fonte` indica a procedência principal do registro sobrevivente. Ele não funciona como uma relação exaustiva de todas as fontes que contribuíram para aquela entrada. Consequentemente, as contagens por fonte descrevem a **atribuição final de proveniência**, e não o grau real de sobreposição entre as bases.

Uma modelagem futura deverá preservar a relação muitos-para-muitos entre entidades consolidadas e registros de origem, com identificadores, datas de acesso, decisões de correspondência e histórico de alterações. Essa mudança permitiria auditar cada fusão sem depender apenas do registro final.

---

## 5. Controle de qualidade e falsos positivos

### 5.1. Por que filtrar

Buscas textuais em plataformas de lugares recuperam entidades que compartilham palavras com o campo religioso, mas não correspondem ao escopo do projeto. Hotéis, restaurantes, lojas, equipamentos públicos, igrejas cristãs, centros kardecistas, monumentos, acidentes geográficos e nomes de municípios podem aparecer porque contêm expressões como “casa”, “santo”, “axé”, “centro”, “terreiro” ou referências territoriais empregadas na consulta.

O controle de falsos positivos foi aplicado apenas aos registros atribuídos ao **Google Places** e ao **OpenStreetMap**. As entradas CEAO e SEMUR, provenientes de levantamentos institucionalmente orientados ao tema, não passaram pelo mesmo filtro nominal automatizado. Essa diferença de tratamento não equivale a uma auditoria independente da qualidade ou da atualidade desses registros.

### 5.2. Procedimento aplicado

A limpeza ocorreu em duas camadas:

1. **varredura inicial de nomes**, que classificou os registros Google consolidados em candidatos religiosos, casos ambíguos e falsos positivos prováveis;
2. **aplicação de listas de inclusão e exclusão**, com correspondência por substring, sem diferenciação entre maiúsculas e minúsculas.

A primeira varredura identificou **323 falsos positivos prováveis**. A segunda camada removeu outros **176 registros** por regras nominais adicionais, totalizando **499 exclusões**: 498 registros Google e um registro OSM. A lista integral das exclusões, acompanhada da regra acionada, está disponível em `data/falsos_positivos_removidos.json`.

Antes da exclusão, o algoritmo consulta uma lista de termos protetivos associados a possíveis terreiros — como referências a orixás, inquices, voduns, nações, “casa de santo”, “terreiro”, “ilê”, “axé”, “abassá”, “inzo”, “tenda” e expressões correlatas. Apenas na ausência desses sinais são aplicadas as regras de exclusão.

### 5.3. Estatuto da validação

A filtragem reduz ruído evidente, mas não constitui validação etnográfica, verificação presencial ou classificação supervisionada por especialistas. A versão atual não dispõe de:

- amostra-ouro rotulada de forma independente;
- dupla codificação humana;
- medida de concordância entre avaliadores;
- estimativas de precisão, revocação ou taxa residual de falsos positivos;
- validação presencial das entidades mantidas;
- revisão comunitária sistemática.

Por essa razão, as exclusões devem ser entendidas como **decisões heurísticas auditáveis**, e os registros remanescentes como candidatos com graus variados de confiança. As listas de termos podem produzir tanto falsos positivos quanto falsos negativos, especialmente diante da polissemia religiosa, das variações linguísticas e da diversidade de formas de autodenominação.

---

## 6. Georreferenciamento e controle territorial

### 6.1. Origem das coordenadas

As coordenadas publicadas foram herdadas das fontes OSM, Google Places e CEAO/UFBA. Não houve, na versão 1.3, geocodificação dos 234 registros SEMUR remanescentes. A camada cartográfica contém, portanto, **1.395 feições pontuais**.

O projeto não atribui a todas as coordenadas o mesmo grau de precisão. Dependendo da fonte, um ponto pode representar a entrada do imóvel, o centro de uma edificação, uma posição fornecida por plataforma colaborativa ou uma localização aproximada. A presença de coordenadas não deve ser interpretada automaticamente como confirmação da posição exata da comunidade.

### 6.2. Recorte operacional da Bahia

Para a checagem inicial foi utilizado um retângulo geográfico aproximado com os seguintes limites:

```text
longitude: -46,7 a -37,3
latitude:  -18,4 a  -8,5
```

Esse *bounding box* funciona como teste de plausibilidade e enquadramento visual; ele não substitui o polígono administrativo oficial do estado. Na camada v1.3, **1.395 pontos** estão dentro do retângulo operacional e possuem o marcador `geo_status: in_bahia`. Os **234 registros SEMUR** permanecem sem coordenadas.

Uma etapa anterior continha 30 pontos do Google Places fora desse recorte. Eles foram removidos da base consolidada e da camada publicada no commit `5b6b5bb`, permanecendo recuperáveis no histórico do repositório para fins de auditoria. Na versão corrente, não há feições externas ao recorte operacional.

### 6.3. Interpretação espacial

A distribuição de pontos expressa simultaneamente a geografia das comunidades e a geografia das fontes. Concentrações urbanas podem resultar de maior presença digital, cobertura institucional mais intensa, facilidade de georreferenciamento ou campanhas localizadas de mapeamento. Áreas com poucos registros não devem ser interpretadas como áreas com poucos terreiros sem evidência adicional.

O mapa é adequado para exploração, localização de registros e formulação de hipóteses. Não é, isoladamente, uma base amostral válida para estimar prevalência, densidade, crescimento ou ausência territorial.

---

## 7. Categorias de navegação

A interface produz uma categoria derivada para permitir filtros e diferenciação visual. Essa classificação é calculada no navegador e não substitui os campos originais das fontes.

Quando o registro possui o campo `nacao`, a interface procura expressões associadas a Ketu/Nagô, Angola, Jeje, Umbanda, Candomblé e matriz africana. Na ausência desse campo, o classificador examina conjuntamente nome, religião, denominação e tipo de equipamento. Registros sem correspondência lexical são reunidos em **“Outro”**.

Essas categorias têm função exclusivamente instrumental. Elas não devem ser tomadas como taxonomia antropológica exaustiva, identidade religiosa certificada ou classificação autorizada pelas comunidades. Grafias não previstas pelo vocabulário podem ser encaminhadas para “Outro”, e casas com pertencimentos múltiplos podem ser reduzidas a uma única categoria em razão da ordem das regras. A análise substantiva deve recorrer aos campos de origem e, quando possível, à autodeclaração da comunidade.

---

## 8. Ética, segurança e governança dos dados

Terreiros e comunidades religiosas afro-brasileiras são historicamente expostos a racismo religioso, violência, invasões, estigmatização e destruição patrimonial. Essa condição altera o estatuto ético da cartografia. O fato de um dado estar publicamente acessível em sua fonte original não torna sua agregação automaticamente isenta de risco: uma interface unificada reduz o custo de localização, cruzamento e reutilização das informações.

A versão atual reúne nomes, coordenadas e, em parte dos registros, endereços, lideranças, telefones e imagens provenientes de fontes públicas. A publicação desses elementos deve observar os princípios de finalidade, necessidade, proporcionalidade, segurança e respeito à autodeterminação informacional. A inclusão no mapa não deve ser interpretada como consentimento individual ou comunitário ao projeto, nem como autorização para abordagem, visita, vigilância ou exploração comercial.

A governança responsável do atlas deve compreender:

1. **canal de correção e retirada**, por meio do qual comunidades possam solicitar atualização, ocultação ou remoção de informações;
2. **revisão de granularidade**, avaliando quando coordenadas exatas devem ser substituídas por localização aproximada ou agregação territorial;
3. **minimização de dados pessoais**, especialmente para nomes de lideranças, telefones e endereços residenciais;
4. **registro das decisões**, incluindo motivo, data e responsável por alterações sensíveis;
5. **consulta comunitária**, incorporando representantes das tradições mapeadas à definição das regras de publicação;
6. **avaliação periódica de risco**, considerando que mudanças no contexto político e tecnológico podem alterar os efeitos da exposição.

Solicitações de correção, atualização ou retirada podem ser encaminhadas a **leofn@ufba.br**. Uma política pública de governança, com prazos, critérios e modalidades de resposta, deverá acompanhar as próximas versões.

---

## 9. Reprodutibilidade e artefatos públicos

A reprodutibilidade da versão 1.3 é **parcial**. O repositório permite inspecionar a camada publicada, os registros consolidados, os arquivos de origem preservados para CEAO e SEMUR, a consulta OSM e as regras de detecção e remoção de falsos positivos. Contudo, não estão integralmente disponíveis os scripts que produziram a coleta Google Places, a extração CEAO, o OCR SEMUR e a consolidação inicial entre as quatro fontes.

### 9.1. Principais artefatos

| Caminho | Função |
|---|---|
| `data/terreiros.geojson` | Camada carregada pela interface; 1.395 pontos na versão 1.3 |
| `data/terreiros_all_sources.json` | Base consolidada com 1.629 registros, incluindo 234 sem coordenadas |
| `data/terreiros_all.geojson` | Instantâneo intermediário anterior à limpeza de falsos positivos |
| `data/falsos_positivos_suspeitos.json` | Resultado da varredura semântica inicial |
| `data/falsos_positivos_removidos.json` | Lista auditável das 499 exclusões |
| `data/ceao/terreiros_ceao_complete.json` | Registros estruturados derivados do CEAO/UFBA |
| `data/sefaz/sefaz_terreiros_complete.json` | Lista SEMUR extraída do documento cartográfico |
| `data/sefaz/sefaz_salvador_map.pdf` | Documento cartográfico de referência preservado no repositório |
| `scripts/collect_osm.py` | Consulta e conversão dos dados do OpenStreetMap |
| `scan_fp.py` | Varredura de falsos positivos prováveis |
| `clean_fp.py` | Aplicação das listas de inclusão e exclusão |
| `refine_and_clean.py` | Rotinas complementares de normalização e controle geográfico |

### 9.2. Condições para reprodução integral

Uma versão plenamente reprodutível deverá acrescentar:

- scripts completos de coleta e paginação do Google Places;
- código de extração das páginas CEAO;
- procedimento documentado de OCR e revisão do mapa SEMUR;
- implementação versionada da deduplicação entre fontes;
- ambiente computacional fixado, com dependências e versões;
- dicionário de dados;
- identificadores estáveis para registros de origem e entidades consolidadas;
- testes automatizados de consistência entre metadados, arquivos e interface;
- licença ou política de reutilização definida de forma compatível com a proveniência heterogênea dos dados.

Na versão auditada, não foi localizado um instrumento único de licenciamento para o conjunto agregado. Acesso público, gratuidade de consulta e licença de redistribuição são condições distintas; as possibilidades de reutilização devem ser verificadas fonte a fonte e formalizadas para o dataset derivado.

Por envolver serviços dinâmicos e bases editáveis, reprodução não significa necessariamente obter os mesmos resultados em uma nova consulta. O objetivo apropriado é tornar repetíveis as operações, registrar as versões das fontes e explicar toda divergência entre execuções.

---

## 10. Limitações

A interpretação do Ilê Axé Map deve considerar, no mínimo, as seguintes limitações:

- **cobertura não probabilística:** as fontes não derivam de plano amostral comum;
- **viés de visibilidade digital:** comunidades com presença em plataformas, cadastros ou projetos institucionais têm maior chance de aparecer;
- **assimetria territorial:** Salvador e áreas com levantamentos específicos estão mais densamente documentadas;
- **heterogeneidade temporal:** a data de integração não corresponde à data de produção nem à atualidade de cada registro;
- **incerteza ontológica:** um “lugar” de plataforma, uma ficha institucional e uma comunidade religiosa não são unidades automaticamente equivalentes;
- **incerteza posicional:** as coordenadas possuem precisão variável e não foram todas verificadas;
- **deduplicação probabilística:** falsos agrupamentos e duplicatas residuais são possíveis;
- **validação sem padrão-ouro:** a limpeza textual não mede precisão ou revocação;
- **proveniência simplificada:** o registro final preserva uma fonte principal, não toda a rede de contribuições;
- **categorias derivadas:** os filtros da interface dependem de regras lexicais e não substituem a autodeclaração;
- **234 registros não cartografados:** a ausência de coordenadas SEMUR reduz a cobertura visual de Salvador;
- **30 ocorrências fora do recorte:** esses pontos demandam revisão territorial específica;
- **risco de reidentificação e exposição:** a agregação pode ampliar riscos já enfrentados pelas comunidades.

Essas limitações não anulam o valor documental do conjunto; elas definem o campo de inferências que ele pode sustentar legitimamente.

---

## 11. Atualização e controle de versão

O conjunto de dados deve adotar versionamento explícito. Cada nova publicação deverá registrar:

- data de extração e data de lançamento;
- fontes consultadas e suas versões, quando disponíveis;
- registros adicionados, alterados, fundidos e removidos;
- mudanças nas regras de deduplicação e classificação;
- decisões de correção ou retirada solicitadas pelas comunidades;
- alterações na granularidade espacial;
- testes de consistência executados;
- responsável pela revisão.

### Prioridades para a próxima versão

1. documentar e testar automaticamente a regra territorial para evitar a reintrodução de registros externos ao recorte operacional;
2. reconciliar os metadados internos com as contagens efetivas dos arquivos e da interface;
3. corrigir e ampliar o vocabulário das categorias de navegação;
4. criar proveniência muitos-para-muitos entre registros de origem e entidades consolidadas;
5. realizar validação humana estratificada, com protocolo e medida de concordância;
6. avaliar a geocodificação responsável dos registros SEMUR, preservando incerteza e proteção espacial;
7. publicar política de correção, retirada e minimização de dados sensíveis;
8. completar os scripts ausentes e fixar o ambiente de reprodução.

---

## 12. Uso e citação

O conjunto é indicado para:

- pesquisa exploratória e formulação de hipóteses;
- estudos sobre cobertura e desigualdade entre infraestruturas de dados;
- documentação de proveniência e história de bases cartográficas;
- desenvolvimento de métodos de integração, deduplicação e auditoria de dados culturais.

Não se recomenda utilizá-lo, sem validação adicional, para:

- estimar o número total de terreiros na Bahia;
- inferir ausência de comunidades em determinado território;
- produzir ranking de municípios ou tradições;
- tomar decisões administrativas ou policiais sobre comunidades específicas;
- realizar visitas, contatos ou intervenções sem mediação ética;
- redistribuir dados pessoais ou coordenadas fora da finalidade de pesquisa.

### Citação sugerida

> NASCIMENTO, Leonardo Fernandes; LABORATÓRIO DE HUMANIDADES DIGITAIS DA UFBA. **Ilê Axé Map: terreiros de candomblé e espaços religiosos afro-brasileiros da Bahia**. Versão 1.3. Salvador: Universidade Federal da Bahia, 2026. Disponível em: <https://labhdufba.github.io/ile-axe-map/>. Acesso em: dia mês ano.

Ao utilizar registros específicos, recomenda-se citar também a fonte de origem correspondente — OpenStreetMap, Google Places, CEAO/UFBA ou SEMUR/SEFAZ — e informar a versão do conjunto consultado.

---

## 13. Referências e fontes

- **Centro de Estudos Afro-Orientais da Universidade Federal da Bahia.** *Mapeamento dos Terreiros de Salvador*. Disponível em: <https://terreiros.ceao.ufba.br/>.
- **OpenStreetMap contributors.** *OpenStreetMap*. Disponível em: <https://www.openstreetmap.org/>.
- **Overpass API.** Interface de consulta ao OpenStreetMap. Disponível em: <https://overpass-api.de/>.
- **Prefeitura Municipal de Salvador — Secretaria Municipal da Reparação.** Mapa cartográfico de terreiros de Salvador, 2020. Documento distribuído pela infraestrutura geográfica da SEFAZ/Salvador.
- **Google.** *Google Places*. Fonte de registros de lugares consultada no processo de coleta.
- **Laboratório de Humanidades Digitais da UFBA.** Repositório do projeto. Disponível em: <https://github.com/LABHDUFBA/ile-axe-map>.

---

*Documento revisto a partir dos arquivos públicos da versão 1.3, commit `be63bf88046276d10ade2e27b220550de8288182`, auditado em 25 de julho de 2026.*
