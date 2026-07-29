import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_google_review import build_google_review


ROOT = Path(__file__).resolve().parents[1]


class GoogleReviewQueueTests(unittest.TestCase):
    def test_builds_complete_prioritized_queue_without_excluding_raw_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "revisao_google.json"
            result = build_google_review(
                ROOT / "data/terreiros_all_sources.json",
                ROOT / "data/falsos_positivos_suspeitos.json",
                ROOT / "data/exclusoes_curadas.csv",
                output,
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            rows = payload["registros"]

            self.assertEqual(result["total"], 693)
            self.assertEqual(len(rows), 693)
            self.assertEqual(len({row["review_id"] for row in rows}), 693)
            self.assertEqual(result["ambiguos"], 133)
            self.assertEqual(result["excluidos_curados"], 143)
            self.assertEqual(sum(row["status_revisao"] == "falso_positivo" for row in rows), 143)
            self.assertEqual(sum(row["sugestao"] == "ambíguo" for row in rows), 133)
            self.assertTrue(all(row["fonte"] == "google" for row in rows))
            self.assertTrue(all(row["google_maps_url"].startswith("https://www.google.com/maps/search/") for row in rows))
            self.assertTrue(all(row["street_view_url"].startswith("https://www.google.com/maps/@?api=1") for row in rows))

    def test_automatic_ambiguity_never_becomes_a_review_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "revisao_google.json"
            build_google_review(
                ROOT / "data/terreiros_all_sources.json",
                ROOT / "data/falsos_positivos_suspeitos.json",
                ROOT / "data/exclusoes_curadas.csv",
                output,
            )

            rows = json.loads(output.read_text(encoding="utf-8"))["registros"]
            suggested = [row for row in rows if row["sugestao"] == "ambíguo"]
            self.assertTrue(suggested)
            self.assertTrue(all(row["status_revisao"] in {"pendente", "falso_positivo"} for row in suggested))
            self.assertTrue(any(row["status_revisao"] == "pendente" for row in suggested))


class GoogleReviewPageTests(unittest.TestCase):
    def test_page_supports_review_persistence_and_csv_roundtrip(self):
        html = (ROOT / "revisao-google.html").read_text(encoding="utf-8")

        self.assertIn("data/revisao_google.json", html)
        self.assertIn("terreiro-map-revisao-google-v1", html)
        self.assertIn("Manter", html)
        self.assertIn("Falso positivo", html)
        self.assertIn("Pendente", html)
        self.assertIn("Exportar CSV", html)
        self.assertIn("Importar CSV", html)
        self.assertIn("localStorage.setItem", html)
        self.assertIn("google_maps_url", html)
        self.assertIn("street_view_url", html)

    def test_page_explains_that_automatic_suggestions_are_not_decisions(self):
        html = (ROOT / "revisao-google.html").read_text(encoding="utf-8")

        self.assertIn("Sugestões automáticas não removem registros", html)
        self.assertIn("A exclusão definitiva só ocorre após confirmação", html)


if __name__ == "__main__":
    unittest.main()
