import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "scrape_mapeandoaxe.py"


def load_module():
    spec = importlib.util.spec_from_file_location("scrape_mapeandoaxe", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_html_preserves_fields_and_photo_urls():
    module = load_module()
    html = """
    <html><head><meta charset="ISO-8859-1"></head><body>
      <div class="group" id="7">
        <div class="title">Ilê Axé Exemplo</div>
        <div class="imagem" id="img_7"><img src="../images/terreiros/terreiros/42_1.jpg"></div>
        <div onclick="Mudar_imagem('img_7',2,'../images/terreiros/terreiros/42_2.jpg')"></div>
        <div class="texto">
          <div class="rotulo">Liderança</div><div class="conteudo">Mãe Exemplo</div>
          <div class="rotulo">Religião</div><div class="conteudo" id="rel_7">Candomblé</div>
          <div class="rotulo">Nação / Linha</div><div class="conteudo" id="nac_7">Ketu, Umbanda</div>
          <div class="rotulo">Regente</div><div class="conteudo" id="reg_7">Oxum</div>
          <div class="rotulo">Fundação</div><div class="conteudo" id="fun_7">1998</div>
          <div class="rotulo">Endereço<br></div>
          <div class="conteudo">Rua Um, 10, Centro<br><span id="cid_7">Belém</span> - PA - CEP 66000-000<br>contato@example.org<br></div>
        </div>
      </div>
      <div class="group" id="nenhum">Nenhum resultado</div>
    </body></html>
    """.encode("iso-8859-1")

    records = module.parse_html(
        html,
        "https://www.mapeandoaxe.org.br/cd/paginas/terreiros.htm",
    )

    assert len(records) == 1
    record = records[0]
    assert record["source_record_id"] == "7"
    assert record["name"] == "Ilê Axé Exemplo"
    assert record["leadership"] == "Mãe Exemplo"
    assert record["religion"] == "Candomblé"
    assert record["nation_line_raw"] == "Ketu, Umbanda"
    assert record["regent_raw"] == "Oxum"
    assert record["foundation_raw"] == "1998"
    assert record["address_raw"] == "Rua Um, 10, Centro"
    assert record["address_full_raw"] == "Rua Um, 10, Centro Belém - PA - CEP 66000-000 contato@example.org"
    assert record["city"] == "Belém"
    assert record["state"] == "PA"
    assert record["postcode"] == "66000-000"
    assert record["email"] == "contato@example.org"
    assert record["photo_urls"] == [
        "https://www.mapeandoaxe.org.br/cd/images/terreiros/terreiros/42_1.jpg",
        "https://www.mapeandoaxe.org.br/cd/images/terreiros/terreiros/42_2.jpg",
    ]


def test_malformed_postcode_is_not_promoted():
    module = load_module()
    html = """
    <div class="group" id="1"><div class="title">Casa sem CEP</div>
      <div class="texto"><div class="rotulo">Endereço</div>
      <div class="conteudo">Rua Dois<br><span id="cid_1">Belém</span> - PA - CEP -0<br></div></div>
    </div>
    """.encode("iso-8859-1")
    record = module.parse_html(html, "https://example.org/terreiros.htm")[0]
    assert record["postcode"] == ""
    assert "CEP -0" in record["address_full_raw"]


def test_public_feature_omits_contact_and_has_null_geometry():
    module = load_module()
    feature = module.to_public_feature(
        {
            "source_record_id": "7",
            "name": "Ilê Axé Exemplo",
            "email": "contato@example.org",
            "leadership": "Mãe Exemplo",
            "source_url": "https://example.org/terreiros.htm",
        }
    )

    assert feature["type"] == "Feature"
    assert feature["geometry"] is None
    assert feature["properties"]["name"] == "Ilê Axé Exemplo"
    assert "email" not in feature["properties"]


def test_write_outputs_keeps_email_only_in_complete_json(tmp_path):
    import json

    module = load_module()
    record = {
        "source": "mapeando_axe_2010",
        "source_record_id": "7",
        "source_url": "https://example.org/terreiros.htm",
        "name": "Ilê Axé Exemplo",
        "leadership": "Mãe Exemplo",
        "religion": "Candomblé",
        "nation_line_raw": "Ketu",
        "regent_raw": "Oxum",
        "foundation_raw": "1998",
        "address_raw": "Rua Um, 10",
        "address_full_raw": "Rua Um, 10 Belém - PA contato@example.org",
        "city": "Belém",
        "state": "PA",
        "postcode": "66000-000",
        "email": "contato@example.org",
        "photo_urls": [],
    }

    module.write_outputs([record], tmp_path)

    complete = json.loads((tmp_path / "mapeando_axe_2010_complete.json").read_text())
    public = json.loads((tmp_path / "mapeando_axe_2010.geojson").read_text())
    csv_text = (tmp_path / "mapeando_axe_2010.csv").read_text()
    csv_bytes = (tmp_path / "mapeando_axe_2010.csv").read_bytes()
    assert complete[0]["email"] == "contato@example.org"
    assert "email" not in public["features"][0]["properties"]
    assert "contato@example.org" not in csv_text
    assert b"\r\n" not in csv_bytes


def test_full_source_has_expected_published_record_count():
    module = load_module()
    raw = Path(__file__).parents[1] / "data" / "mapeando_axe" / "raw" / "paginas" / "terreiros.htm"
    records = module.parse_html(
        raw.read_bytes(),
        "https://www.mapeandoaxe.org.br/cd/paginas/terreiros.htm",
    )
    assert len(records) == 3923
    assert any(
        r["name"] == "Casa Espírita Pai Xangô" and r["city"] == "Eldorado do Sul"
        for r in records
    )
