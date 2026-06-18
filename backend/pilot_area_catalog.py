from __future__ import annotations

import csv
import json
import re
import struct
import zipfile
from pathlib import Path


PLACES_LAYER = "gis_osm_places_a_free_1"
CATALOG_VERSION = "pilot_area_catalog_v001"
DEFAULT_SOURCE_DATASET_ID = "israel-and-palestine-260521-free-shp-zip"


def parse_int(value: object, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_float(value: object, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def slug(value: str) -> str:
    lowered = value.lower().strip()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-") or "pilot"


def workspace_ids_for_pilot(name: str, osm_id: str) -> dict:
    if str(osm_id).strip() == "53796999":
        return {
            "pbf_enriched_workspace_id": "safe_access_kfar_saba_pbf_enriched_v001",
            "route_aware_workspace_id": "safe_access_kfar_saba_route_aware_v001",
        }
    name_part = slug(f"{name} {transliteration_hint(name)}")
    base = f"safe_access_{name_part}_{str(osm_id).strip()}".strip("_")
    return {
        "pbf_enriched_workspace_id": f"{base}_pbf_enriched_v001",
        "route_aware_workspace_id": f"{base}_route_aware_v001",
    }


class PilotAreaCatalog:
    def __init__(self, source_zip: Path, output_root: Path) -> None:
        self.source_zip = source_zip
        self.output_root = output_root
        self.catalog_dir = output_root / "georeview_studio_pilot_catalog"
        self.catalog_path = self.catalog_dir / "pilot_areas.csv"
        self.manifest_path = self.catalog_dir / "pilot_area_catalog_manifest.json"

    def list_pilots(self, query: dict[str, list[str]] | None = None) -> list[dict]:
        query = query or {}
        pilots = self.ensure_catalog()["pilots"]
        text = first(query, "q", "").strip().lower()
        fclass = first(query, "fclass", "").strip().lower()
        min_population = parse_int(first(query, "min_population", "0"))
        limit = max(1, min(parse_int(first(query, "limit", "100"), 100), 500))
        rows = []
        for pilot in pilots:
            if text and text not in (pilot.get("name_search") or "").lower() and text not in str(pilot.get("osm_id", "")):
                continue
            if fclass and str(pilot.get("fclass", "")).lower() != fclass:
                continue
            if parse_int(pilot.get("population")) < min_population:
                continue
            rows.append(pilot)
        rows.sort(key=lambda row: (-parse_int(row.get("population")), row.get("name") or "", row.get("osm_id") or ""))
        return rows[:limit]

    def detail(self, osm_id: str) -> dict:
        for pilot in self.ensure_catalog()["pilots"]:
            if str(pilot.get("osm_id")) == str(osm_id):
                return pilot
        return {"error": "pilot_area_not_found", "pilot_osm_id": str(osm_id)}

    def metadata(self) -> dict:
        catalog = self.ensure_catalog()
        fclasses: dict[str, int] = {}
        for pilot in catalog["pilots"]:
            key = pilot.get("fclass") or "unknown"
            fclasses[key] = fclasses.get(key, 0) + 1
        return {
            "catalog_version": CATALOG_VERSION,
            "source_zip": str(self.source_zip),
            "catalog_path": str(self.catalog_path),
            "source_gis_modified": False,
            "pilot_count": len(catalog["pilots"]),
            "fclasses": dict(sorted(fclasses.items())),
            "recommended_default_osm_id": "53796999",
            "recommended_default_name": "Kfar Saba / כפר סבא",
        }

    def ensure_catalog(self) -> dict:
        if self.catalog_path.exists() and self.manifest_path.exists():
            return {
                "pilots": read_csv_rows(self.catalog_path),
                "manifest": read_json(self.manifest_path),
                "created": False,
            }
        self.catalog_dir.mkdir(parents=True, exist_ok=True)
        pilots = self._build_catalog()
        write_csv_rows(self.catalog_path, pilot_fieldnames(), pilots)
        manifest = {
            "catalog_version": CATALOG_VERSION,
            "source_zip": str(self.source_zip),
            "source_layer": PLACES_LAYER,
            "catalog_path": str(self.catalog_path),
            "source_gis_modified": False,
            "pilot_count": len(pilots),
        }
        write_json(self.manifest_path, manifest)
        return {"pilots": pilots, "manifest": manifest, "created": True}

    def _build_catalog(self) -> list[dict]:
        if not self.source_zip.exists():
            raise FileNotFoundError(f"source zip not found: {self.source_zip}")
        with zipfile.ZipFile(self.source_zip) as archive:
            dbf_rows = read_dbf_rows(archive, f"{PLACES_LAYER}.dbf")
            bboxes = read_shp_record_bboxes(archive, f"{PLACES_LAYER}.shp")
        pilots = []
        for index, row in enumerate(dbf_rows):
            bbox = bboxes[index] if index < len(bboxes) else {}
            osm_id = str(row.get("osm_id") or "").strip()
            name = str(row.get("name") or "").strip()
            fclass = str(row.get("fclass") or "").strip()
            if not osm_id or not name:
                continue
            ids = workspace_ids_for_pilot(name, osm_id)
            pilots.append({
                "source_dataset_id": DEFAULT_SOURCE_DATASET_ID,
                "source_file_name": self.source_zip.name,
                "source_layer": PLACES_LAYER,
                "osm_id": osm_id,
                "code": str(row.get("code") or "").strip(),
                "fclass": fclass,
                "population": str(parse_int(row.get("population"))),
                "name": name,
                "name_search": f"{name} {transliteration_hint(name)} {osm_id}".strip(),
                "bbox_min_lon": f"{parse_float(bbox.get('min_x')):.7f}",
                "bbox_min_lat": f"{parse_float(bbox.get('min_y')):.7f}",
                "bbox_max_lon": f"{parse_float(bbox.get('max_x')):.7f}",
                "bbox_max_lat": f"{parse_float(bbox.get('max_y')):.7f}",
                "pbf_enriched_workspace_id": ids["pbf_enriched_workspace_id"],
                "route_aware_workspace_id": ids["route_aware_workspace_id"],
                "source_gis_modified": "False",
            })
        return pilots


def read_csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv_rows(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def first(query: dict[str, list[str]], key: str, default: str) -> str:
    values = query.get(key)
    return values[0] if values else default


def pilot_fieldnames() -> list[str]:
    return [
        "source_dataset_id",
        "source_file_name",
        "source_layer",
        "osm_id",
        "code",
        "fclass",
        "population",
        "name",
        "name_search",
        "bbox_min_lon",
        "bbox_min_lat",
        "bbox_max_lon",
        "bbox_max_lat",
        "pbf_enriched_workspace_id",
        "route_aware_workspace_id",
        "source_gis_modified",
    ]


def read_dbf_rows(archive: zipfile.ZipFile, member_name: str) -> list[dict]:
    data = archive.read(member_name)
    record_count = struct.unpack("<I", data[4:8])[0]
    header_length = struct.unpack("<H", data[8:10])[0]
    record_length = struct.unpack("<H", data[10:12])[0]
    fields = []
    offset = 32
    while data[offset] != 0x0D:
        descriptor = data[offset:offset + 32]
        name = descriptor[:11].split(b"\x00", 1)[0].decode("ascii")
        fields.append({
            "name": name,
            "type": chr(descriptor[11]),
            "length": descriptor[16],
            "decimal_count": descriptor[17],
        })
        offset += 32

    rows = []
    for record_index in range(record_count):
        start = header_length + record_index * record_length
        record = data[start:start + record_length]
        if not record or record[0:1] == b"*":
            continue
        cursor = 1
        row = {}
        for field in fields:
            raw = record[cursor:cursor + field["length"]]
            cursor += field["length"]
            value = raw.decode("utf-8", errors="replace").strip()
            row[field["name"]] = value
        rows.append(row)
    return rows


def read_shp_record_bboxes(archive: zipfile.ZipFile, member_name: str) -> list[dict]:
    data = archive.read(member_name)
    bboxes = []
    offset = 100
    while offset + 8 <= len(data):
        _record_number = struct.unpack(">i", data[offset:offset + 4])[0]
        content_words = struct.unpack(">i", data[offset + 4:offset + 8])[0]
        content_bytes = content_words * 2
        content_start = offset + 8
        content = data[content_start:content_start + content_bytes]
        if len(content) >= 36:
            shape_type = struct.unpack("<i", content[:4])[0]
            if shape_type in {5, 15, 25, 31}:
                min_x, min_y, max_x, max_y = struct.unpack("<4d", content[4:36])
                bboxes.append({"min_x": min_x, "min_y": min_y, "max_x": max_x, "max_y": max_y})
            else:
                bboxes.append({})
        offset = content_start + content_bytes
    return bboxes


def transliteration_hint(name: str) -> str:
    hints = {
        "כפר סבא": "kfar saba kefar sava",
        "הרצליה": "herzliya",
        "נתניה": "netanya",
        "ירושלים": "jerusalem",
        "תל אביב": "tel aviv",
        "חיפה": "haifa",
        "אשדוד": "ashdod",
        "פתח תקווה": "petah tikva petach tikva",
        "באר-שבע": "beer sheva beersheba",
        "חולון": "holon",
        "רמת גן": "ramat gan",
        "רחובות": "rehovot",
        "אשקלון": "ashkelon",
    }
    return hints.get(name, "")
