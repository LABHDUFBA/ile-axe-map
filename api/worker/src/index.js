/**
 * Ilê Axé Map — API de leitura da camada v5.
 *
 * Por que existe: o GitHub Pages entrega o GeoJSON inteiro num único GET, o que
 * transforma o mapa num arquivo baixável em um comando. Aqui a mesma camada é
 * servida por recorte geográfico e por página, com limite de tamanho por resposta
 * e — quando a binding de rate limit está ativa — com quota por IP.
 *
 * O dataset fica no KV (`TERREIROS`), fora do repositório público.
 *
 * Rotas:
 *   GET /api/v5/meta
 *   GET /api/v5/points?bbox=lon1,lat1,lon2,lat2&limit=250&offset=0
 *   GET /api/v5/record/<entity_id>
 *
 * Nenhuma rota devolve a coleção completa: o recorte máximo é MAX_SPAN_DEG.
 */

const VERSION_KEY = 'v5';
const CACHE_MS = 5 * 60 * 1000;

let cache = { data: null, at: 0, build: null };

function corsHeaders(request, env) {
  const origin = request.headers.get('Origin') || '';
  const allowed = String(env.ALLOWED_ORIGINS || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
  const ok = allowed.includes(origin);
  return {
    'Access-Control-Allow-Origin': ok ? origin : allowed[0] || 'null',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
    Vary: 'Origin',
  };
}

function json(body, status, headers, extra = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store',
      ...headers,
      ...extra,
    },
  });
}

async function loadDataset(env) {
  const now = Date.now();
  if (cache.data && now - cache.at < CACHE_MS) return cache;
  const raw = await env.TERREIROS.get(VERSION_KEY, { type: 'json', cacheTtl: 300 });
  if (!raw) throw new Error('camada ausente no KV');
  const features = raw.features || [];
  const index = new Map();
  for (const f of features) {
    const id = f.properties && f.properties.entity_id;
    if (id) index.set(id, f);
  }
  cache = { data: raw, at: now, build: raw.build || null, index };
  return cache;
}

function parseBbox(raw) {
  if (!raw) return null;
  const parts = raw.split(',').map(Number);
  if (parts.length !== 4 || parts.some(() => false)) return null;
  if (parts.some((n) => !Number.isFinite(n))) return null;
  const [lon1, lat1, lon2, lat2] = parts;
  if (lat1 >= lat2 || lon1 >= lon2) return null;
  if (Math.abs(lat1) > 90 || Math.abs(lat2) > 90) return null;
  if (Math.abs(lon1) > 180 || Math.abs(lon2) > 180) return null;
  return { lon1, lat1, lon2, lat2 };
}

function intParam(raw, fallback, min, max) {
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n)) return fallback;
  return Math.min(Math.max(n, min), max);
}

async function throttle(request, env) {
  if (!env.LIMITER) return null;
  const ip = request.headers.get('CF-Connecting-IP') || 'anon';
  try {
    const { success } = await env.LIMITER.limit({ key: ip });
    if (!success) return json({ erro: 'limite de requisições atingido' }, 429, corsHeaders(request, env));
  } catch (_) {
    /* binding indisponível: segue sem throttling em vez de derrubar a API */
  }
  return null;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const cors = corsHeaders(request, env);

    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });
    if (request.method !== 'GET') return json({ erro: 'método não permitido' }, 405, cors);

    const limited = await throttle(request, env);
    if (limited) return limited;

    try {
      if (url.pathname === '/api/v5/meta' || url.pathname === '/api/v5/meta/') {
        const { data, build } = await loadDataset(env);
        const meta = data.meta || {};
        return json(
          {
            versao: VERSION_KEY,
            entidades: (data.features || []).length,
            build,
            atualizado_em: meta.atualizado_em || null,
            fontes: meta.fontes || null,
            licenca: meta.licenca || null,
            aviso:
              'Camada servida por recorte geográfico. A coleção completa não é oferecida por esta API; pedidos de acesso integral passam pela curadoria do LABHD/UFBA.',
          },
          200,
          cors,
        );
      }

      if (url.pathname === '/api/v5/points' || url.pathname === '/api/v5/points/') {
        const bbox = parseBbox(url.searchParams.get('bbox'));
        if (!bbox) {
          return json(
            { erro: 'parâmetro bbox obrigatório no formato lon1,lat1,lon2,lat2' },
            400,
            cors,
          );
        }
        const maxSpan = Number(env.MAX_SPAN_DEG || 4);
        if (bbox.lon2 - bbox.lon1 > maxSpan || bbox.lat2 - bbox.lat1 > maxSpan) {
          return json(
            { erro: `recorte grande demais; máximo de ${maxSpan}° por eixo` },
            400,
            cors,
          );
        }

        const limit = intParam(url.searchParams.get('limit'), Number(env.DEFAULT_LIMIT || 250), 1, Number(env.MAX_LIMIT || 500));
        const offset = intParam(url.searchParams.get('offset'), 0, 0, 1e7);

        const { data, build } = await loadDataset(env);
        const dentro = [];
        for (const f of data.features || []) {
          const g = f.geometry;
          if (!g || !Array.isArray(g.coordinates)) continue;
          const [lon, lat] = g.coordinates;
          if (lon >= bbox.lon1 && lon <= bbox.lon2 && lat >= bbox.lat1 && lat <= bbox.lat2) dentro.push(f);
        }
        dentro.sort((a, b) => String(a.properties.entity_id || '').localeCompare(String(b.properties.entity_id || '')));
        const page = dentro.slice(offset, offset + limit);
        const proximo = offset + limit < dentro.length ? offset + limit : null;

        return json(
          {
            type: 'FeatureCollection',
            features: page,
            meta: {
              versao: VERSION_KEY,
              build,
              total_na_area: dentro.length,
              devolvidos: page.length,
              offset,
              proximo_offset: proximo,
            },
          },
          200,
          cors,
          { 'Cache-Control': 'public, max-age=60' },
        );
      }

      const m = url.pathname.match(/^\/api\/v5\/record\/([A-Za-z0-9_-]+)\/?$/);
      if (m) {
        const { index, build } = await loadDataset(env);
        const feat = index.get(m[1]);
        if (!feat) return json({ erro: 'registro não encontrado' }, 404, cors);
        return json({ ...feat, meta: { versao: VERSION_KEY, build } }, 200, cors);
      }

      return json(
        {
          erro: 'rota desconhecida',
          rotas: ['/api/v5/meta', '/api/v5/points?bbox=...', '/api/v5/record/<entity_id>'],
        },
        404,
        cors,
      );
    } catch (err) {
      return json({ erro: 'falha interna', detalhe: String(err && err.message ? err.message : err) }, 500, cors);
    }
  },
};
