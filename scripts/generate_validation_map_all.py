#!/usr/bin/env python3
"""Gera mapa HTML de validação com todos os registros validados das 3 fontes."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
GEOJSON_FILE = BASE / "data" / "unified" / "validation_all_sources_v2.geojson"
OUTPUT = BASE / "tmp_national_map_v2.html"

geojson_str = GEOJSON_FILE.read_text(encoding="utf-8")

html = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ilê Axé Map — Validação Nacional Atualizada</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@400;600;700&family=Hanken+Grotesk:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
:root {
  --color-night: #1a0f0a;
  --color-parchment: #f0e6d2;
  --color-cream: #fff8ed;
  --color-brass: #c4700f;
  --color-gold: #e8a838;
  --color-accent: #8b2c1c;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Hanken Grotesk', sans-serif; background: var(--color-cream); color: var(--color-night); overflow: hidden; }
#map { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 0; }

#rail {
  position: absolute; top: 0; left: 0; width: 360px; height: 100vh; z-index: 1000;
  background: rgba(255, 248, 237, 0.95); backdrop-filter: blur(20px);
  border-right: 1px solid rgba(26, 15, 10, 0.1);
  display: flex; flex-direction: column; overflow: hidden;
  transition: transform 0.3s ease;
}
#rail.collapsed { transform: translateX(-340px); }
.rail-header { padding: 24px 24px 16px; border-bottom: 1px solid rgba(26,15,10,0.08); }
.rail-header h1 {
  font-family: 'Fraunces', serif; font-size: 26px; font-weight: 700;
  color: var(--color-brass); letter-spacing: 0.05em; margin-bottom: 4px;
}
.rail-header .subtitle { font-size: 14px; color: rgba(26,15,10,0.6); margin-bottom: 12px; }
.stats { display: flex; gap: 16px; flex-wrap: wrap; }
.stat { font-size: 13px; color: rgba(26,15,10,0.7); }
.stat strong { color: var(--color-accent); font-weight: 600; }

.search-box { padding: 16px 24px 8px; }
.search-box input {
  width: 100%; padding: 10px 14px; border: 1px solid rgba(26,15,10,0.15);
  border-radius: 8px; font-family: 'Hanken Grotesk', sans-serif; font-size: 14px;
  background: var(--color-cream); color: var(--color-night); outline: none;
}
.search-box input:focus { border-color: var(--color-brass); }

.filters { padding: 8px 24px 16px; border-bottom: 1px solid rgba(26,15,10,0.08); }
.filter-group { margin-bottom: 12px; }
.filter-label {
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em;
  color: rgba(26,15,10,0.5); margin-bottom: 6px; font-weight: 600;
}
.filter-pills { display: flex; flex-wrap: wrap; gap: 6px; }
.pill {
  padding: 5px 12px; border-radius: 20px; border: 1px solid rgba(26,15,10,0.15);
  font-size: 12px; cursor: pointer; transition: all 0.2s; background: transparent;
  color: rgba(26,15,10,0.7); display: flex; align-items: center; gap: 6px;
}
.pill .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.pill.active { background: var(--color-night); color: var(--color-cream); border-color: var(--color-night); }
.pill:hover:not(.active) { background: rgba(26,15,10,0.05); }

.list-container { flex: 1; overflow-y: auto; }
.list-item {
  padding: 12px 24px; border-bottom: 1px solid rgba(26,15,10,0.05);
  cursor: pointer; transition: background 0.15s;
}
.list-item:hover { background: rgba(196,112,15,0.08); }
.list-item .name { font-size: 14px; font-weight: 500; color: var(--color-night); margin-bottom: 2px; }
.list-item .meta { font-size: 12px; color: rgba(26,15,10,0.55); }
.source-tag {
  display: inline-block; padding: 2px 8px; border-radius: 10px;
  font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
}
.source-mapeando_axe { background: #e8a838; color: #fff; }
.source-receita_federal_cnpj { background: #557EB5; color: #fff; }
.source-terreirosdobrasil { background: #8b2c1c; color: #fff; }

#detail {
  position: absolute; bottom: 0; left: 360px; right: 0; z-index: 999;
  background: rgba(255, 248, 237, 0.97); backdrop-filter: blur(20px);
  border-top: 1px solid rgba(26,15,10,0.1); padding: 20px 28px;
  transform: translateY(100%); transition: transform 0.3s ease;
  max-height: 40vh; overflow-y: auto;
}
#detail.show { transform: translateY(0); }
#detail .close { position: absolute; top: 12px; right: 20px; cursor: pointer; font-size: 20px; color: rgba(26,15,10,0.4); }
#detail h2 { font-family: 'Fraunces', serif; font-size: 22px; color: var(--color-brass); margin-bottom: 8px; padding-right: 30px; }
#detail .detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 24px; margin-top: 12px; }
#detail .field { font-size: 13px; }
#detail .field-label { color: rgba(26,15,10,0.5); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }
#detail .field-value { color: var(--color-night); margin-top: 2px; }

#toggle-rail {
  position: absolute; top: 50%; left: 360px; z-index: 1001;
  background: rgba(255,248,237,0.9); backdrop-filter: blur(10px);
  border: 1px solid rgba(26,15,10,0.1); border-left: none;
  border-radius: 0 8px 8px 0; width: 24px; height: 48px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: left 0.3s ease; font-size: 14px; color: rgba(26,15,10,0.4);
}
#toggle-rail.collapsed { left: 20px; }

.leaflet-container { background: #FAF7F2; font-family: 'Hanken Grotesk', sans-serif; }
.leaflet-control-attribution { background: rgba(255,248,237,0.8) !important; font-size: 10px; color: rgba(26,15,10,0.5) !important; }
.leaflet-popup-content-wrapper { background: var(--color-cream); border-radius: 8px; }

@media (max-width: 768px) {
  #rail { width: 100%; height: 50vh; }
  #rail.collapsed { transform: translateY(-48vh); }
  #toggle-rail { left: 0; top: 50vh; width: 100%; height: 24px; border-radius: 8px 8px 0 0; }
  #toggle-rail.collapsed { top: calc(50vh - 24px); }
  #detail { left: 0; }
}
</style>
</head>
<body>
<div id="map"></div>
<div id="rail">
  <div class="rail-header">
    <h1>ILÊ AXÉ MAP</h1>
    <div class="subtitle">Validação Nacional Atualizada · Terreiros do Brasil</div>
    <div class="stats">
      <span class="stat"><strong id="stat-total">0</strong> pontos</span>
      <span class="stat"><strong>3</strong> fontes</span>
      <span class="stat"><strong>100%</strong> validados</span>
    </div>
  </div>
  <div class="search-box">
    <input type="text" id="search" placeholder="Buscar terreiro...">
  </div>
  <div class="filters">
    <div class="filter-group">
      <div class="filter-label">Classificação</div>
      <div class="filter-pills" id="filter-classes"></div>
    </div>
    <div class="filter-group">
      <div class="filter-label">Fonte</div>
      <div class="filter-pills" id="filter-sources"></div>
    </div>
  </div>
  <div class="list-container" id="list"></div>
</div>
<div id="toggle-rail" onclick="toggleRail()">&#8249;</div>
<div id="detail">
  <span class="close" onclick="closeDetail()">&#10005;</span>
  <div id="detail-content"></div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const GEOJSON = ''' + geojson_str + ''';

const CLASS_INFO = {
  confirmado: { color: "#2d8f49", label: "Confirmado" },
  confirmado_proximo: { color: "#7ec850", label: "Confirmado (próximo)" },
  google_melhor: { color: "#e8a838", label: "Google melhor" },
  novo_google: { color: "#c4700f", label: "Novo (Google)" },
  novo_google_possivel: { color: "#d4841a", label: "Novo (possível)" },
  nominatim_melhor: { color: "#557EB5", label: "Nominatim melhor" },
  divergente_inconclusivo: { color: "#8b2c1c", label: "Divergente" },
  proximo_nome_diferente: { color: "#a0522d", label: "Próximo, nome diferente" },
  nao_encontrado: { color: "#555555", label: "Não encontrado" },
  match_ruim: { color: "#cc3333", label: "Match ruim" }
};

const SOURCE_INFO = {
  mapeando_axe: { label: "Mapeando Axé", color: "#e8a838" },
  receita_federal_cnpj: { label: "CNPJ/Receita", color: "#557EB5" },
  terreirosdobrasil: { label: "Terreiros BR", color: "#8b2c1c" }
};

const map = L.map('map', { zoomControl: false }).setView([-12, -40], 4);
L.control.zoom({ position: 'topright' }).addTo(map);
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; OSM &copy; CARTO', subdomains: 'abcd', maxZoom: 19
}).addTo(map);

const markers = [];
let activeFilters = { classes: new Set(), sources: new Set() };
const allFeatures = GEOJSON.features;

Object.keys(CLASS_INFO).forEach(k => activeFilters.classes.add(k));
Object.keys(SOURCE_INFO).forEach(k => activeFilters.sources.add(k));

allFeatures.forEach((feat, idx) => {
  const props = feat.properties;
  const coords = feat.geometry.coordinates;
  const cls = props.classification || "nao_encontrado";
  const clsInfo = CLASS_INFO[cls] || { color: "#999", label: cls };
  const marker = L.circleMarker([coords[1], coords[0]], {
    radius: 5, fillColor: clsInfo.color, color: clsInfo.color,
    weight: 1, opacity: 0.8, fillOpacity: 0.7
  });
  marker.featureIndex = idx;
  marker.bindTooltip('<strong>' + props.nome + '</strong><br>' + clsInfo.label, { direction: 'top', offset: [-5, -5] });
  marker.on('click', () => showDetail(idx));
  markers.push(marker);
});

function renderFilters() {
  const cc = {}, sc = {};
  allFeatures.forEach(f => {
    const c = f.properties.classification || "nao_encontrado";
    const s = f.properties.source || "";
    cc[c] = (cc[c]||0)+1; sc[s] = (sc[s]||0)+1;
  });
  const fc = document.getElementById('filter-classes');
  fc.innerHTML = '';
  Object.keys(CLASS_INFO).sort((a,b)=>(cc[b]||0)-(cc[a]||0)).forEach(k => {
    if(!cc[k]) return;
    const p = document.createElement('div');
    p.className = 'pill' + (activeFilters.classes.has(k)?' active':'');
    p.innerHTML = '<span class="dot" style="background:'+CLASS_INFO[k].color+'"></span>'+CLASS_INFO[k].label+' ('+cc[k]+')';
    p.onclick = () => toggleFilter('classes',k);
    fc.appendChild(p);
  });
  const fs = document.getElementById('filter-sources');
  fs.innerHTML = '';
  Object.keys(SOURCE_INFO).forEach(k => {
    if(!sc[k]) return;
    const p = document.createElement('div');
    p.className = 'pill' + (activeFilters.sources.has(k)?' active':'');
    p.innerHTML = '<span class="dot" style="background:'+SOURCE_INFO[k].color+'"></span>'+SOURCE_INFO[k].label+' ('+sc[k]+')';
    p.onclick = () => toggleFilter('sources',k);
    fs.appendChild(p);
  });
}

function toggleFilter(type,key) {
  const s = activeFilters[type];
  if(s.has(key)) s.delete(key); else s.add(key);
  updateMap(); renderFilters(); renderList(document.getElementById('search').value);
}

function updateMap() {
  markers.forEach(m => {
    const p = allFeatures[m.featureIndex].properties;
    const c = p.classification||"nao_encontrado";
    const s = p.source||"";
    const v = activeFilters.classes.has(c) && activeFilters.sources.has(s);
    if(v && !map.hasLayer(m)) map.addLayer(m);
    if(!v && map.hasLayer(m)) map.removeLayer(m);
  });
}

function renderList(search) {
  search = search || '';
  const list = document.getElementById('list');
  list.innerHTML = '';
  let rendered = 0;
  let totalMatching = 0;
  for(let i=0; i<allFeatures.length; i++) {
    const p = allFeatures[i].properties;
    const c = p.classification||"nao_encontrado";
    const s = p.source||"";
    if(!activeFilters.classes.has(c)||!activeFilters.sources.has(s)) continue;
    if(search && !p.nome.toLowerCase().includes(search.toLowerCase())) continue;
    totalMatching++;
    if(rendered >= 200) continue;
    const ci = CLASS_INFO[c]||{label:c};
    const si = SOURCE_INFO[s]||{label:s};
    const d = document.createElement('div');
    d.className = 'list-item';
    d.innerHTML = '<div class="name">'+p.nome+'</div><div class="meta"><span class="source-tag source-'+s+'">'+si.label+'</span> '+ci.label+' &middot; '+(p.cidade||'')+' '+(p.uf||'')+'</div>';
    d.onclick = () => { showDetail(i); const co=allFeatures[i].geometry.coordinates; map.setView([co[1],co[0]],16,{animate:true}); };
    list.appendChild(d);
    rendered++;
  }
  document.getElementById('stat-total').textContent = totalMatching;
}

function showDetail(idx) {
  const p = allFeatures[idx].properties;
  const c = p.classification||"nao_encontrado";
  const ci = CLASS_INFO[c]||{label:c,color:"#999"};
  const si = SOURCE_INFO[p.source]||{label:p.source};
  const co = allFeatures[idx].geometry.coordinates;
  let html = '<h2>'+p.nome+'</h2><div class="detail-grid">'+
    '<div class="field"><div class="field-label">Fonte</div><div class="field-value">'+si.label+'</div></div>'+
    '<div class="field"><div class="field-label">Classificação</div><div class="field-value"><span style="color:'+ci.color+';font-weight:600">'+ci.label+'</span></div></div>'+
    '<div class="field"><div class="field-label">Cidade/UF</div><div class="field-value">'+(p.cidade||'—')+' / '+(p.uf||'—')+'</div></div>'+
    '<div class="field"><div class="field-label">Coordenadas</div><div class="field-value">'+co[1].toFixed(4)+', '+co[0].toFixed(4)+'</div></div>';
  if(p.google_name) html += '<div class="field"><div class="field-label">Google Places</div><div class="field-value">'+p.google_name+'</div></div>';
  if(p.google_address) html += '<div class="field"><div class="field-label">Endereço Google</div><div class="field-value">'+p.google_address+'</div></div>';
  if(p.google_lat) html += '<div class="field"><div class="field-label">Google Coords</div><div class="field-value">'+p.google_lat.toFixed(4)+', '+p.google_lng.toFixed(4)+'</div></div>';
  if(p.google_dist_m!=null) html += '<div class="field"><div class="field-label">Distância N→G</div><div class="field-value">'+Math.round(p.google_dist_m)+'m</div></div>';
  if(p.google_sim!=null) html += '<div class="field"><div class="field-label">Similaridade nome</div><div class="field-value">'+(p.google_sim*100).toFixed(0)+'%</div></div>';
  html += '</div>';
  document.getElementById('detail-content').innerHTML = html;
  document.getElementById('detail').classList.add('show');
}

function closeDetail() { document.getElementById('detail').classList.remove('show'); }
function toggleRail() {
  const r=document.getElementById('rail'), t=document.getElementById('toggle-rail');
  r.classList.toggle('collapsed'); t.classList.toggle('collapsed');
  t.innerHTML = r.classList.contains('collapsed')?'&#8250;':'&#8249;';
}

document.getElementById('search').addEventListener('input', e => renderList(e.target.value));
renderFilters(); updateMap(); renderList();
</script>
</body>
</html>'''

OUTPUT.write_text(html, encoding="utf-8")
print(f"Mapa: {OUTPUT} ({OUTPUT.stat().st_size // 1024}KB)")
print(f"Pontos: {len(json.loads(geojson_str)['features'])}")