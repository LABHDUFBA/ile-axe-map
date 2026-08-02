# Mapeando o Axé, coleta de 2010

Fonte: <https://www.mapeandoaxe.org.br/cd/paginas/terreiros.htm>

Coleta realizada em 2 de agosto de 2026 para o experimento de expansão do Ilê Axé Map. Estes dados permanecem separados da base publicada da Bahia.

## Escopo

O projeto declara 4.045 casas pesquisadas entre maio e agosto de 2010:

- Região Metropolitana de Belém: 1.089
- Região Metropolitana de Belo Horizonte: 353
- Região Metropolitana de Porto Alegre: 1.342
- Região Metropolitana de Recife: 1.261

O conteúdo atualmente disponível no site é menor:

| Publicação | Fichas |
|---|---:|
| Página geral | 3.923 |
| Belém | 1.078 |
| Belo Horizonte | 339 |
| Porto Alegre | 1.260 |
| Recife | 1.245 |
| Soma das páginas regionais | 3.922 |

A ficha `Casa Espírita Pai Xangô`, de Eldorado do Sul, aparece apenas na página geral. A UF publicada é `CE`, incompatível com o município gaúcho. O valor original foi preservado e não corrigido silenciosamente.

## Arquivos

- `raw/paginas/`: HTML original e páginas institucionais.
- `raw/script/`: JavaScript original usado pela listagem.
- `raw/fotos/`: fotografias referenciadas, coletadas com retomada e intervalo conforme o `robots.txt`.
- `processed/mapeando_axe_2010_complete.json`: transcrição completa, incluindo e-mails publicados na fonte.
- `processed/mapeando_axe_2010.csv`: projeção pública sem e-mails.
- `processed/mapeando_axe_2010.geojson`: projeção pública sem e-mails e com `geometry: null`.
- `processed/manifest.json`: contagens, hash da página principal e divergências.
- `processed/validation_report.json`: completude e duplicidades.
- `photo_urls.txt`: URLs únicas das fotografias.

## Campos extraídos

- nome da casa;
- liderança;
- religião;
- nação ou linha, preservada literalmente;
- regente, preservado literalmente;
- ano de fundação;
- endereço completo original;
- endereço, município, UF e CEP analisados separadamente;
- e-mail, apenas no arquivo completo;
- URLs das fotografias;
- identificador sequencial e URL da fonte.

## Limitações

- O site não fornece latitude ou longitude. Por isso, o GeoJSON usa `geometry: null`.
- O identificador da página é sequencial e não deve ser tratado como identificador institucional estável.
- Nomes repetidos na mesma cidade não foram deduplicados automaticamente.
- Há 151 grupos com mesmo nome normalizado e cidade, mas nenhuma duplicata integral em todos os campos.
- E-mails e nomes de liderança são dados pessoais. A projeção pública remove e-mails. Qualquer integração futura deve aplicar minimização deliberada.
- O total declarado de 4.045 corresponde ao universo pesquisado, não ao número de fichas atualmente publicadas.

## Proveniência

Os arquivos brutos são mantidos para auditoria. Transformações são executadas por `scripts/scrape_mapeandoaxe.py` e verificadas em `tests/test_scrape_mapeandoaxe.py`. Nenhum registro desta coleta foi incorporado automaticamente ao mapa de produção.
