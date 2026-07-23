Rebuild the index.html file in this repository to be a polished, production-quality interactive map site inspired by thecastlemap.com (Castle Map atlas), but adapted for terreiros de candomblé (ilê axé) da Bahia.

## Castle Map design reference (copy the structure/feel, NOT the colors):

### Fonts
- Display/headings: Fraunces (serif) via Google Fonts
- Body/UI: Hanken Grotesk (sans) via Google Fonts

### Layout
- Full-screen MapLibre GL JS map (dark theme)
- Top-left panel (glassmorphism): title "ILÊ AXÉ MAP", subtitle "Terreiros de Candomblé da Bahia", stats count, filter buttons
- Top-right: language toggle (PT/EN) + dark/light mode toggle
- Bottom-left: attribution + data source links
- Click marker → detail panel slides in from left with info
- Hover marker → tooltip with name + nação

### Castle Map CSS patterns to replicate:
- CSS custom properties for theme colors:
  --color-night, --color-parchment, --color-cream, --color-brass, --color-gold
- Glassmorphism panels: background #0c141c/90, backdrop-blur-xl, border white/10, rounded-2xl, shadow
- Custom map controls styling: backdrop-blur, rounded-10px, dark bg, invert icons
- Custom cursor (SVG data URI) on map canvas
- Filter pills: rounded-full, border, active state with bg highlight
- Smooth transitions on all interactive elements
- MapLibre attribution: dark bg, parchment text, small font
- Responsive: mobile shows panel at bottom, desktop shows panel at left

### Castle Map JS patterns:
- Load GeoJSON from data/terreiros.geojson
- Classify each feature into a "nação" category (Ketu, Angola, Jeje, Candomblé, Matriz Africana, Outro) based on religion/denomination tags
- Color-coded markers per nação
- Filter buttons that show/hide markers by nação
- Stats: total count display
- Click marker → detail panel with all properties
- Download link for GeoJSON
- Link to OpenStreetMap for each terreiro

## BUT use these DIFFERENT colors (warm Afro-Bahian palette, NOT Castle Map's teal):
- --color-night: #1a0f0a (deep warm brown-black, like dark earth)
- --color-parchment: #f0e6d2 (warm cream)
- --color-cream: #fff8ed (warm white)
- --color-brass: #c4700f (burnt orange/amber — warm Afro-Brazilian)
- --color-gold: #e8a838 (golden amber — warm gold)
- --color-accent: #8b2c1c (terracotta red — Bahian terracotta)

### Map tiles
Use OpenFreeMap dark style (same as Castle Map):
```
https://tiles.openfreemap.org/styles/dark
```
With MapLibre GL JS v4.7.1 from unpkg.

### Marker colors per nação:
- Ketu: #e8a838 (gold)
- Angola: #c4700f (amber)
- Jeje: #8b2c1c (terracotta)
- Candomblé: #d4841a (orange)
- Matriz Africana: #a0522d (sienna)
- Outro: #7a6a5a (warm gray)

### Detail panel fields (from GeoJSON properties):
- name → Nome
- _nacao → Nação
- religion → Religião
- denomination → Denominação
- amenity → Tipo
- addr:street → Rua
- addr:housenumber → Número
- addr:suburb → Bairro
- addr:city → Cidade
- addr:postcode → CEP
- phone → Telefone
- start_date → Fundação
- Coordinates
- Link to OSM

### Title and branding:
- Title: "ILÊ AXÉ MAP" (Fraunces, tracking-wide, gold color)
- Subtitle: "Terreiros de Candomblé da Bahia" (Hanken Grotesk, parchment/70)
- Stats: "{count} terreiros mapeados" (small, parchment/50)
- Footer: "Dados: OpenStreetMap · LABHD/UFBA · Download GeoJSON"

## Requirements
1. Single index.html file — all CSS inline in <style>, all JS inline in <script>
2. Must work on GitHub Pages (relative paths, no build step)
3. Mobile responsive
4. Dark mode only (no light mode toggle needed, but keep the toggle button as decoration if you want)
5. No framework dependencies — vanilla JS + MapLibre GL JS from CDN
6. Load data from data/terreiros.geojson (relative path)
7. Make it look as polished and professional as thecastlemap.com
8. Do NOT modify data/terreiros.geojson or any other file — only index.html

Write the complete index.html file now.