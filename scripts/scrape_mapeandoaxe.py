#!/usr/bin/env python3
"""Extrai as fichas públicas do projeto Mapeando o Axé."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+")
PHOTO_RE = re.compile(r"['\"](\.\./images/terreiros/terreiros/[^'\"]+)['\"]")


def _paired_fields(group) -> dict[str, str]:
    fields: dict[str, str] = {}
    for label in group.select(".texto .rotulo"):
        content = label.find_next_sibling("div", class_="conteudo")
        if content is None:
            continue
        key = label.get_text(" ", strip=True).casefold()
        fields[key] = content.get_text(" ", strip=True)
    return fields


def parse_html(content: bytes, source_url: str) -> list[dict]:
    soup = BeautifulSoup(content, "lxml", from_encoding="iso-8859-1")
    records: list[dict] = []

    for group in soup.select("div.group[id]"):
        if group.get("id") == "nenhum":
            continue
        title = group.select_one(".title")
        city_tag = group.select_one('[id^="cid_"]')
        fields = _paired_fields(group)
        address_node = next(
            (
                label.find_next_sibling("div", class_="conteudo")
                for label in group.select(".texto .rotulo")
                if label.get_text(" ", strip=True).casefold().startswith("endereço")
            ),
            None,
        )
        address_text = address_node.get_text(" ", strip=True) if address_node else ""
        city = city_tag.get_text(" ", strip=True) if city_tag else ""
        state_match = re.search(
            rf"{re.escape(city)}\s*-\s*([A-Z]{{2}})",
            address_text,
        ) if city else None
        postcode_match = re.search(r"\bCEP\s*([0-9]{5}-?[0-9]{3})\b", address_text)
        state = state_match.group(1) if state_match else ""
        postcode = postcode_match.group(1) if postcode_match else ""
        email_match = EMAIL_RE.search(address_text)

        address_parts = list(address_node.stripped_strings) if address_node else []
        address_raw_parts: list[str] = []
        for part in address_parts:
            if part == city or EMAIL_RE.fullmatch(part):
                break
            address_raw_parts.append(part)

        photo_urls = {
            urljoin(source_url, img.get("src"))
            for img in group.select("img[src]")
            if "images/terreiros/terreiros/" in (img.get("src") or "")
        }
        for tag in group.select("[onclick]"):
            for relative_url in PHOTO_RE.findall(tag.get("onclick", "")):
                photo_urls.add(urljoin(source_url, relative_url))

        records.append(
            {
                "source": "mapeando_axe_2010",
                "source_record_id": str(group.get("id")),
                "source_url": source_url,
                "name": title.get_text(" ", strip=True) if title else "",
                "leadership": fields.get("liderança", ""),
                "religion": fields.get("religião", ""),
                "nation_line_raw": fields.get("nação / linha", ""),
                "regent_raw": fields.get("regente", ""),
                "foundation_raw": fields.get("fundação", ""),
                "address_raw": " ".join(address_raw_parts).strip(),
                "address_full_raw": address_text,
                "city": city,
                "state": state,
                "postcode": postcode,
                "email": email_match.group(0) if email_match else "",
                "photo_urls": sorted(photo_urls),
            }
        )

    return records


def to_public_feature(record: dict) -> dict:
    private_fields = {"email", "address_full_raw"}
    properties = {key: value for key, value in record.items() if key not in private_fields}
    return {"type": "Feature", "geometry": None, "properties": properties}


def write_outputs(records: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    complete_path = output_dir / "mapeando_axe_2010_complete.json"
    geojson_path = output_dir / "mapeando_axe_2010.geojson"
    csv_path = output_dir / "mapeando_axe_2010.csv"

    complete_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    geojson = {
        "type": "FeatureCollection",
        "features": [to_public_feature(record) for record in records],
    }
    geojson_path.write_text(
        json.dumps(geojson, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    public_records = [feature["properties"] for feature in geojson["features"]]
    fieldnames = list(public_records[0]) if public_records else []
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for record in public_records:
            row = dict(record)
            row["photo_urls"] = "|".join(row.get("photo_urls", []))
            writer.writerow(row)
