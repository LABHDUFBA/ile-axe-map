import json
import csv
import tempfile
import unittest
from pathlib import Path

from scripts.build_v2 import build_v2, classify_nation, classify_record


ROOT = Path(__file__).resolve().parents[1]


class NationClassificationTests(unittest.TestCase):
    def test_keto_is_preserved_as_declared(self):
        result = classify_nation("Keto")
        self.assertEqual(result["nacao_categoria"], "Keto")
        self.assertEqual(result["nacao_componentes"], [])

    def test_composite_nation_is_not_split_or_prioritized(self):
        result = classify_nation("Keto Angola")
        self.assertEqual(result["nacao_original"], "Keto Angola")
        self.assertEqual(result["nacao_categoria"], "Keto Angola")
        self.assertEqual(result["nacao_componentes"], [])
        self.assertIsNone(result["nacao_primaria"])

    def test_missing_nation_is_not_called_other(self):
        result = classify_nation(None)
        self.assertEqual(result["nacao_categoria"], "Não informado")
        self.assertEqual(result["nacao_componentes"], [])

    def test_alaketo_is_not_agglutinated_with_keto(self):
        self.assertEqual(classify_nation("Alaketo")["nacao_categoria"], "Alaketo")
        self.assertEqual(classify_nation("Keto")["nacao_categoria"], "Keto")

    def test_concatenated_label_is_preserved(self):
        result = classify_nation("KetoTapa")
        self.assertEqual(result["nacao_componentes"], [])
        self.assertEqual(result["nacao_categoria"], "KetoTapa")

    def test_only_repeated_whitespace_is_cleaned_for_display(self):
        result = classify_nation("  Keto   Angola  ")
        self.assertEqual(result["nacao_original"], "Keto   Angola")
        self.assertEqual(result["nacao_categoria"], "Keto Angola")

    def test_missing_declaration_is_not_inferred_from_name(self):
        result = classify_record({"nome": "Ilê Keto Angola"})
        self.assertEqual(result["nacao_categoria"], "Não informado")


class BuildV2Tests(unittest.TestCase):
    def test_build_represents_every_ceao_record_and_keeps_other_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = build_v2(
                ROOT / "data/ceao/terreiros_ceao_complete.json",
                ROOT / "data/terreiros_all_sources.json",
                Path(tmp),
            )

            self.assertEqual(result["source_counts"], {
                "ceao": 1155,
                "google": 693,
                "osm": 20,
                "sefaz": 234,
            })
            self.assertEqual(result["total_records"], 2102)
            self.assertEqual(result["mappable_records"], 1868)

            all_sources = json.loads((Path(tmp) / "terreiros_all_sources_v2.json").read_text())
            ceao = [r for r in all_sources["terreiros"] if r["fonte"] == "ceao"]
            self.assertEqual(len(ceao), 1155)
            self.assertEqual(len({r["ceao_id"] for r in ceao}), 1155)
            self.assertTrue(all(r["geo_status"] == "in_bahia" for r in ceao))

            geojson = json.loads((Path(tmp) / "terreiros_v2.geojson").read_text())
            self.assertEqual(len(geojson["features"]), 1868)
            self.assertEqual(
                sum(f["properties"]["fonte"] == "ceao" for f in geojson["features"]),
                1155,
            )
            categories = [
                f["properties"]["nacao_categoria"]
                for f in geojson["features"]
                if f["properties"]["fonte"] == "ceao"
            ]
            self.assertIn("Keto", categories)
            self.assertIn("Alaketo", categories)
            self.assertIn("KetoTapa", categories)
            self.assertNotIn("Ketu", categories)
            self.assertEqual(categories.count("Não informado"), 3)

            review_path = Path(tmp) / "revisao_humana_nacao_v2.csv"
            self.assertTrue(review_path.exists())
            with review_path.open(encoding="utf-8", newline="") as handle:
                review_rows = list(csv.DictReader(handle))
            self.assertTrue(review_rows)
            self.assertTrue(all(row["status_revisao"] == "pendente" for row in review_rows))
            self.assertTrue(all(row["nacao_componentes"] == "[]" for row in review_rows))

    def test_build_excludes_curated_false_positives(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = build_v2(
                ROOT / "data/ceao/terreiros_ceao_complete.json",
                ROOT / "data/terreiros_all_sources.json",
                Path(tmp),
                ROOT / "data/exclusoes_curadas.csv",
            )

            self.assertEqual(result["source_counts"]["google"], 550)
            self.assertEqual(result["total_records"], 1959)
            self.assertEqual(result["mappable_records"], 1725)

            geojson = json.loads((Path(tmp) / "terreiros_v2.geojson").read_text())
            names = {feature["properties"].get("nome") for feature in geojson["features"]}
            excluded_names = {
                "Casa Rural - Materiais de Construção e Agro veterinária",
                "Casas Freire",
                "Rua Bahia, 457 Santo Antonio De Jesus",
                "Remanso BA",
                "Sítio Arqueológico Pilão Arcado Velho",
                "CRAS - Itaguaçu da Bahia",
                "Casa São Paulo",
                "Casa das Espumas",
                "R. Castro Alves, 169 - Cs A",
                "Casa do Campo",
                "Casa São Luiz Materiais De Construção",
                "Laticínios Santana Lauro de Freitas",
                "Condomínio Spazio Sunrise",
                "CASA DAS RESISTÊNCIAS",
            }
            self.assertTrue(names.isdisjoint(excluded_names))

    def test_build_does_not_overwrite_v1_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            v1 = output / "terreiros.geojson"
            v1.write_text("stable-v1")

            build_v2(
                ROOT / "data/ceao/terreiros_ceao_complete.json",
                ROOT / "data/terreiros_all_sources.json",
                output,
            )

            self.assertEqual(v1.read_text(), "stable-v1")
            self.assertTrue((output / "auditoria_v2.json").exists())


class SiteIntegrationTests(unittest.TestCase):
    def test_site_loads_validated_v2_and_uses_precomputed_category(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("fetch('data/terreiros_v2.geojson')", html)
        self.assertIn("p.nacao_categoria", html)
        self.assertIn("Não informado", html)
        self.assertIn("nationColor", html)
        self.assertIn("categoryCounts", html)
        self.assertNotIn("const categoryOrder = ['Ketu'", html)
        self.assertNotIn("transition: transform .15s", html)
        self.assertNotIn("keto|ketu|nago|alaketo|alaketu", html)

    def test_leaflet_clusters_have_accessible_circle_markers(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("L.markerClusterGroup({", html)
        self.assertIn("maxClusterRadius: 60", html)
        self.assertIn("L.circleMarker(", html)
        self.assertIn("radius: 8", html)
        self.assertIn("el.setAttribute('role', 'button')", html)
        self.assertNotIn("maplibregl", html)

    def test_map_opens_at_bahia_extent_without_animation(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("const BAHIA_BOUNDS = L.latLngBounds", html)
        self.assertIn("map.fitBounds(BAHIA_BOUNDS", html)
        self.assertIn("maxZoom: 12, animate: false", html)

    def test_map_stays_hidden_until_data_and_markers_are_stable(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("body:not(.map-ready) #map", html)
        self.assertIn("id=\"map-loading\"", html)
        self.assertIn("function revealStableMap()", html)
        self.assertLess(html.index("updateMarkers();", html.index("map.whenReady")), html.index("revealStableMap();", html.index("map.whenReady")))

    def test_light_theme_uses_liberty_basemap(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("https://tiles.openfreemap.org/styles/liberty", html)
        self.assertNotIn("https://tiles.openfreemap.org/styles/positron", html)

    def test_about_panel_reports_v2_reconciliation(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("v2.1", html)
        self.assertIn("1.155", html)
        self.assertIn("1.959 registros", html)
        self.assertIn("1.725", html)
        self.assertIn("fetch('data/auditoria_v2.json')", html)
        self.assertIn("fonte-ceao", html)
        self.assertIn("fonte-osm", html)
        self.assertIn("fonte-sefaz", html)
        self.assertIn("49 declarações do CEAO", html)

    def test_methodology_documents_ceao_reconciliation(self):
        methodology = (ROOT / "metodologia.html").read_text(encoding="utf-8")
        self.assertIn("versão 2.1", methodology)
        self.assertIn("473 registros CEAO", methodology)
        self.assertIn("data/terreiros_v2.geojson", methodology)
        self.assertIn("não converte Keto em Ketu", methodology)
        self.assertIn("nomes de estabelecimentos não são usados para inferir", methodology)
        self.assertNotIn("Parte dessas ocorrências foi agregada", methodology)


if __name__ == "__main__":
    unittest.main()
