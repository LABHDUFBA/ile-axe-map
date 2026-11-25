# API do Ilê Axé Map (Cloudflare Worker)

Serve a camada v5 **por recorte geográfico e por página**, em vez de um GeoJSON
único baixável. O dado vive no KV do Cloudflare, fora do repositório público.

## Onde isso roda (a pergunta "onde instalo?")

Não se instala em servidor nenhum. O que existe é:

1. **Um CLI nesta máquina** (`wrangler`, já instalado em `api/worker/node_modules`) — é ele que
   envia o código. Nada fica rodando aqui.
2. **Uma conta Cloudflare** (plano free serve) — dona do Worker e do KV. O código roda na borda
   da Cloudflare, em centenas de pontos, com 100 mil requisições/dia grátis.
3. **Um endereço público** para a API. O mais simples é o subdomínio que a Cloudflare dá de
   graça (`ile-axe-api.<sua-conta>.workers.dev`); o mais elegante é uma rota no domínio que você
   já controla (`api.metodosdigitais...`), o que exige o domínio estar na Cloudflare.

## Publicar (uma vez)

```bash
cd api/worker
npx wrangler login                                   # abre o navegador, autoriza a conta
npx wrangler kv namespace create TERREIROS           # devolve o id
# colar o id em wrangler.toml → [[kv_namespaces]] id
cd ../..
python3 scripts/kv_payload_v5.py                     # gera data/v5/kv_payload.json (fora do Git)
cd api/worker
npx wrangler kv key put v5 --binding=TERREIROS --path=../../data/v5/kv_payload.json --remote
npx wrangler deploy
```

Cada nova versão da camada: rodar o payload, repetir o `kv key put` e o site passa a ler o
build novo sem tocar no repositório.

## Rotas

| Rota | O que faz |
|---|---|
| `GET /api/v5/meta` | versão, número de entidades, fontes, impressão digital do build, licença |
| `GET /api/v5/points?bbox=lon1,lat1,lon2,lat2&limit=250&offset=0` | pontos dentro do recorte, paginados |
| `GET /api/v5/record/<entity_id>` | uma ficha completa |

Limites: recorte máximo de 4° por eixo (`MAX_SPAN_DEG`), no máximo 500 feições por resposta
(`MAX_LIMIT`). Não existe rota que devolva a coleção inteira — de propósito.

## Testar sem conta Cloudflare

```bash
cd api/worker
npx wrangler kv key put v5 --binding=TERREIROS --path=../../data/v5/kv_payload.json --local
npx wrangler dev --local --port 8787
curl "http://127.0.0.1:8787/api/v5/meta"
curl "http://127.0.0.1:8787/api/v5/points?bbox=-38.60,-13.05,-38.35,-12.85&limit=3"
```

## CORS e proteção

- CORS restrito a `ALLOWED_ORIGINS` (site, mais `localhost` para desenvolvimento). Origem
  desconhecida recebe a origem autorizada e o navegador bloqueia a leitura — não é barreira
  criptográfica, é barreira de uso casual.
- Rate limit por IP: ativar a binding `[[ratelimits]]` no `wrangler.toml`. Sem ela a API
  funciona igual, só não limita.
- Impressão digital: `meta.build` (sha256 curto do arquivo) vai em toda resposta e sobrevive à
  cópia. Se aparecer num site de terceiros, a origem está provada.

## Privacidade

O payload passa por allowlist de campos (`scripts/kv_payload_v5.py`): só o que a interface
desenha vai para o KV. Endereço, contato, dirigente e campos internos de auditoria ficam de
fora, mesmo que existam na camada do repositório.
