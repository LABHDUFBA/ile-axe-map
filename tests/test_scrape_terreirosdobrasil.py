"""Testes unitários para o scraper de terreirosdobrasil.com.br"""
import json
import os
import sys
from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from scrape_terreirosdobrasil import (
    normalize_nacao,
    extract_coords_from_html,
    extract_address_from_html,
    extract_description_from_html,
    extract_category_from_html,
    parse_listing,
    scrape_all_listings,
    to_geojson,
    to_csv,
)


class TestNormalizeNacao:
    def test_ketu(self):
        assert normalize_nacao("Candomblé Ketu") == "Ketu"

    def test_angola(self):
        assert normalize_nacao("Candomblé Angola") == "Angola"

    def test_jeje(self):
        assert normalize_nacao("Candomblé Jeje") == "Jeje"

    def test_umbanda(self):
        assert normalize_nacao("Umbanda") == "Umbanda"

    def test_jurema(self):
        assert normalize_nacao("Jurema Sagrada") == "Jurema"

    def test_nago(self):
        assert normalize_nacao("Nàgó") == "Nago"

    def test_tambor_mina(self):
        assert normalize_nacao("Tambor de Mina") == "Tambor de Mina"

    def test_efon(self):
        assert normalize_nacao("Èfọ́n") == "Efon"

    def test_omoloko(self):
        assert normalize_nacao("Omolokô") == "Omoloko"

    def test_unknown(self):
        assert normalize_nacao("Outra Coisa") == "Outro"

    def test_empty(self):
        assert normalize_nacao("") == "Outro"


class TestExtractCoords:
    def test_coords_from_data_attr(self):
        html = '<div data-lat="-12.9714" data-lng="-38.5014"></div>'
        lat, lng = extract_coords_from_html(html)
        assert lat == -12.9714
        assert lng == -38.5014

    def test_coords_from_json(self):
        html = '{"lat": -5.7841695, "lng": -35.1999708}'
        lat, lng = extract_coords_from_html(html)
        assert lat == -5.7841695
        assert lng == -35.1999708

    def test_coords_from_gmaps_url(self):
        html = 'https://maps.google.com/?q=-5.7841695,-35.1999708'
        lat, lng = extract_coords_from_html(html)
        assert lat == -5.7841695
        assert lng == -35.1999708

    def test_no_coords(self):
        html = '<html><body>sem coords</body></html>'
        lat, lng = extract_coords_from_html(html)
        assert lat is None
        assert lng is None

    def test_coords_negative(self):
        html = '"lat":-23.5505,"lng":-46.6333'
        lat, lng = extract_coords_from_html(html)
        assert lat == -23.5505
        assert lng == -46.6333


class TestExtractAddress:
    def test_address_from_li(self):
        html = '<li>R. Núbia Mendes, Itaparica - BA, 44460-000, Brasil</li>'
        addr = extract_address_from_html(html)
        assert "Itaparica" in addr
        assert "BA" in addr

    def test_no_address(self):
        html = '<html><body>sem endereço</body></html>'
        addr = extract_address_from_html(html)
        assert addr == ""


class TestExtractDescription:
    def test_description_from_quote(self):
        html = '<blockquote>Terreiro localizado em Itaparica</blockquote>'
        desc = extract_description_from_html(html)
        assert "Terreiro" in desc

    def test_description_from_p(self):
        html = '<p class="description">Casa de axé fundada em 2011</p>'
        desc = extract_description_from_html(html)
        assert "Casa de axé" in desc

    def test_no_description(self):
        html = '<html></html>'
        desc = extract_description_from_html(html)
        assert desc == ""


class TestExtractCategory:
    def test_category_from_breadcrumb(self):
        html = '<li><a>Candomblé Ketu</a></li>'
        cat = extract_category_from_html(html)
        assert "Ketu" in cat

    def test_no_category(self):
        html = '<html></html>'
        cat = extract_category_from_html(html)
        assert cat == ""


class TestParseListing:
    def test_parse_complete(self):
        api_item = {
            "id": 4995,
            "title": {"rendered": "Ilê Axé Odé Omín"},
            "link": "https://www.terreirosdobrasil.com.br/cadastro/ile-axe-ode-omin/",
            "content": {"rendered": '<div data-lat="-5.784" data-lng="-35.199">R. Núbia Mendes, Itaparica - BA</div>'},
        }
        result = parse_listing(api_item)
        assert result["id"] == 4995
        assert result["nome"] == "Ilê Axé Odé Omín"
        assert result["link"] == "https://www.terreirosdobrasil.com.br/cadastro/ile-axe-ode-omin/"
        assert result["lat"] == -5.784
        assert result["lng"] == -35.199
        assert result["source"] == "terreirosdobrasil.com.br"

    def test_parse_without_coords(self):
        api_item = {
            "id": 100,
            "title": {"rendered": "Teste"},
            "link": "https://www.terreirosdobrasil.com.br/cadastro/teste/",
            "content": {"rendered": "<p>sem coords</p>"},
        }
        result = parse_listing(api_item)
        assert result["lat"] is None
        assert result["lng"] is None
        assert result["nome"] == "Teste"


class TestToGeoJSON:
    def test_geojson_structure(self):
        listings = [
            {"id": 1, "nome": "Terreiro A", "lat": -12.0, "lng": -38.0, "nacao": "Ketu", "cidade": "Salvador", "uf": "BA", "link": "http://x", "source": "terreirosdobrasil.com.br"},
        ]
        gj = to_geojson(listings)
        assert gj["type"] == "FeatureCollection"
        assert len(gj["features"]) == 1
        assert gj["features"][0]["geometry"]["type"] == "Point"
        assert gj["features"][0]["geometry"]["coordinates"] == [-38.0, -12.0]
        assert gj["features"][0]["properties"]["nome"] == "Terreiro A"

    def test_geojson_skips_no_coords(self):
        listings = [
            {"id": 1, "nome": "Sem coords", "lat": None, "lng": None, "link": "", "source": "terreirosdobrasil.com.br"},
            {"id": 2, "nome": "Com coords", "lat": -5.0, "lng": -35.0, "link": "", "source": "terreirosdobrasil.com.br"},
        ]
        gj = to_geojson(listings)
        assert len(gj["features"]) == 1


class TestToCSV:
    def test_csv_header(self, tmp_path):
        listings = [
            {"id": 1, "nome": "A", "lat": -12.0, "lng": -38.0, "nacao": "Ketu", "cidade": "Salvador", "uf": "BA", "endereco": "R. X", "link": "http://x", "source": "terreirosdobrasil.com.br", "descricao": ""},
        ]
        out = tmp_path / "test.csv"
        to_csv(listings, str(out))
        content = out.read_text()
        assert "id,nome,nacao" in content
        assert "Salvador" in content


class TestScrapeAll:
    @patch("scrape_terreirosdobrasil.requests.get")
    def test_scrape_pagination(self, mock_get):
        page1 = MagicMock(status_code=200)
        page1.json.return_value = [
            {"id": 1, "title": {"rendered": "A"}, "link": "http://a", "content": {"rendered": "<p>" + "x" * 150 + "</p>"}},
        ]
        page1.headers = {"X-WP-Total": "1", "X-WP-TotalPages": "1"}

        # Mock da página individual
        detail_page = MagicMock(status_code=200, text="<html><body>sem dados</body></html>")

        mock_get.side_effect = [page1, detail_page]
        with patch("scrape_terreirosdobrasil.load_cache", return_value={}):
            results = scrape_all_listings()
        assert len(results) == 1
        assert results[0]["nome"] == "A"