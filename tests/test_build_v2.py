import json
import csv
import tempfile
import unittest
from pathlib import Path

from scripts.build_v2 import build_v2, classify_nation, classify_record


ROOT = Path(__file__).resolve().parents[1]


class NationClassificationTests(unittest.TestCase):
    def test_keto_variant_is_classified_as_ketu(self):
        result = classify_nation("Keto")
        self.assertEqual(result["nacao_categoria"], "Ketu")
        self.assertEqual(result["nacao_componentes"], ["Ketu"])

    def test_composite_nation_preserves_all_components(self):
        result = classify_nation("Keto Angola")
        self.assertEqual(result["nacao_original"], "Keto Angola")
        self.assertEqual(result["nacao_componentes"], ["Ketu", "Angola"])
        self.assertIsNone(result["nacao_primaria"])

    def test_missing_nation_is_not_called_other(self):
        result = classify_nation(None)
        self.assertEqual(result["nacao_categoria"], "Não informado")
        self.assertEqual(result["nacao_componentes"], [])

    def test_unmapped_declared_nation_is_preserved(self):
        result = classify_nation("Ijexá")
        self.assertEqual(result["nacao_original"], "Ijexá")
        self.assertEqual(result["nacao_categoria"], "Outras declarações")

    def test_concatenated_keto_qualifier_is_tokenized(self):
        result = classify_nation("KetoTapa")
        self.assertEqual(result["nacao_componentes"], ["Ketu", "Tapa"])
        self.assertEqual(result["nacao_categoria"], "Ketu")

    def test_generic_matriz_in_name_does_not_mean_african_tradition(self):
        result = classify_record({"nome": "Central de Adubos - Matriz Juazeiro"})
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

            review_path = Path(tmp) / "revisao_humana_nacao_v2.csv"
            self.assertTrue(review_path.exists())
            with review_path.open(encoding="utf-8", newline="") as handle:
                review_rows = list(csv.DictReader(handle))
            self.assertTrue(review_rows)
            self.assertTrue(all(row["status_revisao"] == "pendente" for row in review_rows))
            self.assertEqual(
                sum(row["nacao_categoria"] == "Outras declarações" for row in review_rows),
                result["audit"]["classificacao_mapa"]["Outras declarações"],
            )

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
        self.assertNotIn("transition: transform .15s", html)
        self.assertNotIn("(matriz|african)", html)

    def test_about_panel_reports_v2_reconciliation(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("v2.0", html)
        self.assertIn("1.155 terreiros", html)
        self.assertIn("2.102 registros", html)
        self.assertIn("1.868", html)

    def test_methodology_documents_ceao_reconciliation(self):
        methodology = (ROOT / "metodologia.html").read_text(encoding="utf-8")
        self.assertIn("versão 2.0", methodology)
        self.assertIn("473 registros CEAO", methodology)
        self.assertIn("data/terreiros_v2.geojson", methodology)
        self.assertNotIn("Parte dessas ocorrências foi agregada", methodology)


if __name__ == "__main__":
    unittest.main()
