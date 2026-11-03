import json
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]


def test_mapa_temporario_v2_embute_geojson_completo():
    html_path = BASE / "tmp_national_map_v2.html"
    geojson_path = BASE / "data" / "unified" / "validation_all_sources_v2.geojson"

    assert html_path.exists()
    html = html_path.read_text(encoding="utf-8")
    prefix = "const GEOJSON = "
    start = html.index(prefix) + len(prefix)
    end = html.index(";\n", start)
    embedded = json.loads(html[start:end])
    source = json.loads(geojson_path.read_text(encoding="utf-8"))

    assert len(embedded["features"]) == len(source["features"]) == 5757
    assert "Validação Nacional Atualizada" in html


def test_contador_nao_e_limitado_pela_lista_de_200_itens():
    html = (BASE / "tmp_national_map_v2.html").read_text(encoding="utf-8")
    assert "let totalMatching = 0;" in html
    assert "document.getElementById('stat-total').textContent = totalMatching;" in html
