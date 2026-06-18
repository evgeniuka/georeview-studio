from __future__ import annotations

import argparse
import json
import math
import re
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ANALYSIS_CRS = "EPSG:2039"
SOURCE_CRS = "EPSG:4326"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."
MAJOR_ROADS = {"motorway", "trunk", "primary", "secondary", "tertiary"}
GENERATOR_FCLASSES = {"school", "kindergarten", "playground", "community_centre", "park"}
REQUIRED_GEOFABRIK_LAYERS = [
    "gis_osm_places_a_free_1",
    "gis_osm_roads_free_1",
    "gis_osm_traffic_free_1",
    "gis_osm_transport_free_1",
    "gis_osm_pois_free_1",
    "gis_osm_pois_a_free_1",
    "gis_osm_landuse_a_free_1",
]
PBF_TAG_KEYS = [
    "amenity",
    "highway",
    "crossing",
    "crossing_ref",
    "tactile_paving",
    "kerb",
    "crossing:island",
    "button_operated",
    "traffic_signals:sound",
    "sidewalk",
    "sidewalk:left",
    "sidewalk:right",
    "lit",
    "maxspeed",
    "lanes",
    "surface",
    "smoothness",
    "access",
    "oneway",
    "traffic_calming",
    "footway",
    "cycleway",
    "cycleway:left",
    "cycleway:right",
    "bicycle",
    "segregated",
]
TAG_PATTERN = re.compile(r'"((?:[^"\\]|\\.)*)"=>"((?:[^"\\]|\\.)*)"')


def import_gis_modules() -> dict[str, Any]:
    import geopandas as gpd
    import pandas as pd

    return {"gpd": gpd, "pd": pd}


def safe_str(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value)
    return "" if text.lower() in {"nan", "none", "<na>"} else text


def json_list(values: list[str]) -> str:
    return json.dumps(values, ensure_ascii=False)


def vsi_zip_path(source_zip: Path, layer: str) -> str:
    return "/vsizip/" + str(source_zip).replace("\\", "/") + f"/{layer}.shp"


def read_zip_layer(source_zip: Path, layer: str, bbox: tuple[float, float, float, float] | None = None):
    modules = import_gis_modules()
    gpd = modules["gpd"]
    gdf = gpd.read_file(vsi_zip_path(source_zip, layer), bbox=bbox)
    if gdf.crs is None:
        gdf = gdf.set_crs(SOURCE_CRS)
    return gdf[gdf.geometry.notna()].copy()


def parse_other_tags(value: object) -> dict[str, str]:
    if not isinstance(value, str) or not value:
        return {}
    tags: dict[str, str] = {}
    for key, tag_value in TAG_PATTERN.findall(value):
        tags[key.replace(r"\"", '"')] = tag_value.replace(r"\"", '"')
    return tags


def add_parsed_tag_columns(gdf, keys: list[str]) -> None:
    modules = import_gis_modules()
    pd = modules["pd"]
    if "other_tags" not in gdf.columns:
        for key in keys:
            if key not in gdf.columns:
                gdf[key] = pd.NA
        return
    parsed = gdf["other_tags"].map(parse_other_tags)
    for key in keys:
        existing = gdf[key] if key in gdf.columns else pd.Series(pd.NA, index=gdf.index)
        from_other = parsed.map(lambda tags: tags.get(key, pd.NA))
        gdf[key] = existing.where(existing.notna() & (existing.astype(str) != ""), from_other)


def read_pbf_layer(source_pbf: Path, layer: str, bbox: tuple[float, float, float, float]):
    modules = import_gis_modules()
    gpd = modules["gpd"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        gdf = gpd.read_file(str(source_pbf), layer=layer, bbox=bbox)
    if gdf.crs is None:
        gdf = gdf.set_crs(SOURCE_CRS)
    gdf = gdf[gdf.geometry.notna()].copy()
    add_parsed_tag_columns(gdf, PBF_TAG_KEYS)
    return gdf


def load_pbf_layers(source_pbf: Path | None, pilot_geom_4326, bbox: tuple[float, float, float, float]) -> dict[str, Any]:
    modules = import_gis_modules()
    gpd = modules["gpd"]
    empty = gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs=SOURCE_CRS)
    if source_pbf is None or not source_pbf.exists():
        return {"points": empty.copy(), "lines": empty.copy(), "multipolygons": empty.copy(), "used": False}
    return {
        "points": clip_to_pilot(read_pbf_layer(source_pbf, "points", bbox), pilot_geom_4326),
        "lines": clip_to_pilot(read_pbf_layer(source_pbf, "lines", bbox), pilot_geom_4326),
        "multipolygons": clip_to_pilot(read_pbf_layer(source_pbf, "multipolygons", bbox), pilot_geom_4326),
        "used": True,
    }


def clip_to_pilot(gdf, pilot_geom_4326):
    if gdf.empty:
        return gdf.copy()
    gdf = gdf.to_crs(SOURCE_CRS)
    clipped = gdf.loc[gdf.geometry.intersects(pilot_geom_4326)].copy()
    if clipped.empty:
        return clipped
    clipped.geometry = clipped.geometry.intersection(pilot_geom_4326)
    return clipped[clipped.geometry.notna() & ~clipped.geometry.is_empty].copy()


def to_analysis_crs(gdf):
    if gdf.empty:
        return gdf.set_crs(SOURCE_CRS, allow_override=True).to_crs(ANALYSIS_CRS)
    return gdf.to_crs(ANALYSIS_CRS)


def count_within(geom, target, radius_m: float) -> int:
    if target.empty or geom is None or geom.is_empty:
        return 0
    return int((target.geometry.distance(geom) <= radius_m).sum())


def nearest_row(geom, target) -> tuple[Any | None, float]:
    if target.empty or geom is None or geom.is_empty:
        return None, math.nan
    distances = target.geometry.distance(geom)
    idx = distances.idxmin()
    return target.loc[idx], float(distances.loc[idx])


def nearby_subset(geom, target, radius_m: float):
    if target.empty or geom is None or geom.is_empty:
        return target.iloc[0:0].copy()
    return target[target.geometry.distance(geom) <= radius_m].copy()


def has_any_value(row, columns: list[str]) -> bool:
    return any(safe_str(row.get(col)) for col in columns)


def has_no_value(row, columns: list[str]) -> bool:
    return any(safe_str(row.get(col)).lower() in {"no", "none"} for col in columns)


def first_nonempty(*values: object) -> str:
    for value in values:
        text = safe_str(value)
        if text and text != "0":
            return text
    return ""


def load_pilot_boundary(source_zip: Path, pilot_osm_id: str):
    places = read_zip_layer(source_zip, "gis_osm_places_a_free_1")
    pilot = places.loc[places["osm_id"].astype(str) == str(pilot_osm_id)].copy()
    if pilot.empty:
        raise RuntimeError(f"Pilot polygon osm_id={pilot_osm_id} was not found in gis_osm_places_a_free_1.")
    keep = [col for col in ["osm_id", "code", "fclass", "population", "name", "geometry"] if col in pilot.columns]
    pilot = pilot[keep].copy()
    pilot_geom = pilot.geometry.iloc[0]
    return pilot, pilot_geom, tuple(pilot.total_bounds)


def load_pilot_layers(source_zip: Path, pilot_geom_4326, bbox: tuple[float, float, float, float]) -> dict[str, Any]:
    layers = {}
    for layer in REQUIRED_GEOFABRIK_LAYERS:
        if layer == "gis_osm_places_a_free_1":
            continue
        layers[layer] = clip_to_pilot(read_zip_layer(source_zip, layer, bbox=bbox), pilot_geom_4326)
    return layers


def add_source_fields(gdf, source_layer: str):
    out = gdf.copy()
    out["source_layer"] = source_layer
    return out


def build_generators(layers: dict[str, Any], pbf_points, pbf_polygons, pbf_enrichment_used: bool):
    modules = import_gis_modules()
    gpd = modules["gpd"]
    pd = modules["pd"]
    frames = []

    pois_point = layers["gis_osm_pois_free_1"]
    if not pois_point.empty:
        selected = pois_point[pois_point["fclass"].isin(GENERATOR_FCLASSES)].copy()
        selected["generator_type"] = selected["fclass"]
        frames.append(add_source_fields(selected, "gis_osm_pois_free_1"))

    pois_area = layers["gis_osm_pois_a_free_1"]
    if not pois_area.empty:
        selected = pois_area[pois_area["fclass"].isin(GENERATOR_FCLASSES)].copy()
        selected["generator_type"] = selected["fclass"]
        frames.append(add_source_fields(selected, "gis_osm_pois_a_free_1"))

    landuse = layers["gis_osm_landuse_a_free_1"]
    if not landuse.empty:
        selected = landuse[landuse["fclass"].isin({"park", "recreation_ground"})].copy()
        selected["generator_type"] = selected["fclass"]
        frames.append(add_source_fields(selected, "gis_osm_landuse_a_free_1"))

    transport = layers["gis_osm_transport_free_1"]
    if not transport.empty:
        selected = transport[transport["fclass"] == "bus_stop"].copy()
        selected["generator_type"] = "bus_stop"
        frames.append(add_source_fields(selected, "gis_osm_transport_free_1"))

    for source_name, pbf_gdf in [("osm_pbf_points", pbf_points), ("osm_pbf_multipolygons", pbf_polygons)]:
        if pbf_gdf.empty or "amenity" not in pbf_gdf.columns:
            continue
        childcare = pbf_gdf[pbf_gdf["amenity"].fillna("") == "childcare"].copy()
        if childcare.empty:
            continue
        childcare["code"] = pd.NA
        childcare["fclass"] = "childcare"
        childcare["generator_type"] = "childcare"
        frames.append(add_source_fields(childcare, source_name))

    if not frames:
        return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs=ANALYSIS_CRS)

    combined = pd.concat(frames, ignore_index=True)
    combined = gpd.GeoDataFrame(combined, geometry="geometry", crs=SOURCE_CRS)
    combined["osm_id"] = combined["osm_id"].astype(str)
    combined["name"] = combined.get("name", pd.Series("", index=combined.index)).map(safe_str)
    combined = combined.sort_values(["generator_type", "osm_id", "source_layer"]).drop_duplicates(["generator_type", "osm_id"])
    combined = combined.to_crs(ANALYSIS_CRS)
    combined["original_geometry_type"] = combined.geometry.geom_type
    combined["geometry"] = combined.geometry.representative_point()
    combined = combined.reset_index(drop=True)
    combined["generator_id"] = [f"gen_{idx + 1:04d}" for idx in range(len(combined))]
    flags = ["pilot_boundary_osm_geofabrik_not_official"]
    if not pbf_enrichment_used:
        flags.append("raw_pbf_tag_enrichment_not_used_in_generic_zip_mapper")
    combined["data_quality_flags"] = json_list(flags)
    return combined


def build_crossings(traffic, pbf_points):
    modules = import_gis_modules()
    pd = modules["pd"]
    traffic_2039 = to_analysis_crs(traffic)
    crossings = traffic_2039[traffic_2039["fclass"] == "pedestrian_crossing"].copy().reset_index(drop=True)
    signals = traffic_2039[traffic_2039["fclass"] == "traffic_signals"].copy().reset_index(drop=True)
    street_lamps = traffic_2039[traffic_2039["fclass"] == "street_lamp"].copy().reset_index(drop=True)
    for col in ["crossing", "crossing_ref", "tactile_paving", "kerb", "crossing:island", "button_operated", "traffic_signals:sound"]:
        crossings[col] = pd.NA
    if not pbf_points.empty:
        point_tags = pbf_points.copy()
        point_tags["osm_id"] = point_tags["osm_id"].astype(str)
        tag_cols = [
            "osm_id",
            "crossing",
            "crossing_ref",
            "tactile_paving",
            "kerb",
            "crossing:island",
            "button_operated",
            "traffic_signals:sound",
        ]
        point_tags = point_tags[[col for col in tag_cols if col in point_tags.columns]].drop_duplicates("osm_id")
        crossings["osm_id"] = crossings["osm_id"].astype(str)
        crossings = crossings.merge(point_tags, on="osm_id", how="left", suffixes=("", "_pbf"))
        for col in ["crossing", "crossing_ref", "tactile_paving", "kerb", "crossing:island", "button_operated", "traffic_signals:sound"]:
            pbf_col = f"{col}_pbf"
            if pbf_col in crossings.columns:
                crossings[col] = crossings[col].where(crossings[col].notna() & (crossings[col].astype(str) != ""), crossings[pbf_col])
    crossings["crossing_id"] = [f"cross_{idx + 1:04d}" for idx in range(len(crossings))]
    crossings["crossing_type"] = crossings["crossing"].map(safe_str)
    crossings.loc[crossings["crossing_type"] == "", "crossing_type"] = "pedestrian_crossing"
    crossings["has_signal_nearby"] = [bool(count_within(geom, signals, 50) > 0) for geom in crossings.geometry]
    crossings["crossing_island"] = crossings["crossing:island"].map(safe_str)
    return crossings, signals, street_lamps


def build_roads(roads, pbf_lines):
    modules = import_gis_modules()
    pd = modules["pd"]
    roads_2039 = to_analysis_crs(roads).reset_index(drop=True)
    roads_2039["osm_id"] = roads_2039["osm_id"].astype(str)
    for col in [
        "sidewalk",
        "sidewalk:left",
        "sidewalk:right",
        "lit",
        "lanes",
        "surface",
        "smoothness",
        "access",
        "cycleway",
        "cycleway:left",
        "cycleway:right",
        "bicycle",
        "segregated",
    ]:
        roads_2039[col] = pd.NA
    if not pbf_lines.empty:
        line_tags = pbf_lines.copy()
        line_tags["osm_id"] = line_tags["osm_id"].astype(str)
        tag_cols = [
            "osm_id",
            "sidewalk",
            "sidewalk:left",
            "sidewalk:right",
            "lit",
            "maxspeed",
            "lanes",
            "surface",
            "smoothness",
            "access",
            "oneway",
            "cycleway",
            "cycleway:left",
            "cycleway:right",
            "bicycle",
            "segregated",
        ]
        line_tags = line_tags[[col for col in tag_cols if col in line_tags.columns]].drop_duplicates("osm_id")
        roads_2039 = roads_2039.merge(line_tags, on="osm_id", how="left", suffixes=("", "_pbf"))
        for col in [
            "sidewalk",
            "sidewalk:left",
            "sidewalk:right",
            "lit",
            "lanes",
            "surface",
            "smoothness",
            "access",
            "cycleway",
            "cycleway:left",
            "cycleway:right",
            "bicycle",
            "segregated",
        ]:
            pbf_col = f"{col}_pbf"
            if pbf_col in roads_2039.columns:
                roads_2039[col] = roads_2039[col].where(roads_2039[col].notna() & (roads_2039[col].astype(str) != ""), roads_2039[pbf_col])
    roads_2039["road_id"] = [f"road_{idx + 1:05d}" for idx in range(len(roads_2039))]
    roads_2039["highway_class"] = roads_2039["fclass"].map(safe_str)
    roads_2039["maxspeed_source"] = [
        "shapefile" if safe_str(row.get("maxspeed")) and safe_str(row.get("maxspeed")) != "0" else ("pbf" if safe_str(row.get("maxspeed_pbf")) else "")
        for _, row in roads_2039.iterrows()
    ]
    roads_2039["maxspeed_effective"] = [first_nonempty(row.get("maxspeed"), row.get("maxspeed_pbf")) for _, row in roads_2039.iterrows()]
    roads_2039["oneway_effective"] = [first_nonempty(row.get("oneway"), row.get("oneway_pbf")) for _, row in roads_2039.iterrows()]
    major = roads_2039[roads_2039["highway_class"].isin(MAJOR_ROADS)].copy().reset_index(drop=True)
    return roads_2039, major


def build_traffic_calming(traffic, pbf_points, pbf_lines):
    modules = import_gis_modules()
    gpd = modules["gpd"]
    pd = modules["pd"]
    traffic_2039 = to_analysis_crs(traffic)
    frames = []
    if not traffic_2039.empty and "fclass" in traffic_2039.columns:
        selected = traffic_2039[traffic_2039["fclass"].isin({"traffic_calming", "speed_bump"})].copy()
        if not selected.empty:
            selected["feature_type"] = "traffic_calming"
            selected["feature_value"] = selected["fclass"].map(safe_str)
            selected["source_layer"] = "gis_osm_traffic_free_1"
            frames.append(selected)
    for source_layer, gdf in [("osm_pbf_points", pbf_points), ("osm_pbf_lines", pbf_lines)]:
        if gdf.empty:
            continue
        highway = gdf["highway"].map(safe_str) if "highway" in gdf.columns else pd.Series("", index=gdf.index)
        calming = gdf["traffic_calming"].map(safe_str) if "traffic_calming" in gdf.columns else pd.Series("", index=gdf.index)
        selected = gdf[(calming != "") | (highway == "traffic_calming")].copy()
        if selected.empty:
            continue
        selected = to_analysis_crs(selected)
        selected["feature_type"] = "traffic_calming"
        selected["feature_value"] = selected["traffic_calming"].map(safe_str) if "traffic_calming" in selected.columns else ""
        selected.loc[selected["feature_value"] == "", "feature_value"] = "traffic_calming"
        selected["source_layer"] = source_layer
        frames.append(selected)
    if not frames:
        return gpd.GeoDataFrame(columns=["feature_id", "feature_type", "feature_value", "source_layer", "geometry"], geometry="geometry", crs=ANALYSIS_CRS)
    combined = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), geometry="geometry", crs=ANALYSIS_CRS).reset_index(drop=True)
    combined["feature_id"] = [f"calm_{idx + 1:04d}" for idx in range(len(combined))]
    return combined


def road_has_sidewalk_no(row) -> bool:
    return has_no_value(row, ["sidewalk", "sidewalk:left", "sidewalk:right"])


def road_has_sidewalk_tag(row) -> bool:
    return has_any_value(row, ["sidewalk", "sidewalk:left", "sidewalk:right"])


def road_has_lit_tag(row) -> bool:
    return has_any_value(row, ["lit"])


def road_lit_no(row) -> bool:
    return safe_str(row.get("lit")).lower() == "no"


def build_risk_results(generators, crossings, signals, roads, major_roads, traffic_calming, pbf_enrichment_used: bool):
    modules = import_gis_modules()
    gpd = modules["gpd"]
    road_flags = roads.copy()
    if not road_flags.empty:
        road_flags["has_sidewalk_tag"] = [road_has_sidewalk_tag(row) for _, row in road_flags.iterrows()]
        road_flags["has_sidewalk_no"] = [road_has_sidewalk_no(row) for _, row in road_flags.iterrows()]
        road_flags["has_lit_tag"] = [road_has_lit_tag(row) for _, row in road_flags.iterrows()]
        road_flags["has_lit_no"] = [road_lit_no(row) for _, row in road_flags.iterrows()]

    records = []
    for _, gen in generators.iterrows():
        geom = gen.geometry
        nearest_crossing, nearest_crossing_m = nearest_row(geom, crossings)
        nearest_major, nearest_major_m = nearest_row(geom, major_roads)
        crossing_within_100m = bool(not math.isnan(nearest_crossing_m) and nearest_crossing_m <= 100)
        crossing_within_150m = bool(not math.isnan(nearest_crossing_m) and nearest_crossing_m <= 150)
        major_road_within_150m = bool(not math.isnan(nearest_major_m) and nearest_major_m <= 150)
        signals_within_50m = count_within(geom, signals, 50)
        traffic_calming_within_100m = count_within(geom, traffic_calming, 100)

        nearest_crossing_id = ""
        nearest_crossing_signals_within_50m = 0
        nearest_crossing_major_road_m = math.nan
        crossing_near_major_without_signal = False
        crossing_detail_missing = False
        if nearest_crossing is not None:
            nearest_crossing_id = safe_str(nearest_crossing.get("crossing_id"))
            nearest_crossing_signals_within_50m = count_within(nearest_crossing.geometry, signals, 50)
            _, nearest_crossing_major_road_m = nearest_row(nearest_crossing.geometry, major_roads)
            crossing_near_major_without_signal = (
                not math.isnan(nearest_crossing_major_road_m)
                and nearest_crossing_major_road_m <= 25
                and nearest_crossing_signals_within_50m == 0
            )
            crossing_detail_missing = not has_any_value(
                nearest_crossing,
                ["crossing", "crossing_ref", "tactile_paving", "kerb", "crossing:island", "button_operated", "traffic_signals:sound"],
            )

        nearby_roads_50 = nearby_subset(geom, road_flags, 50)
        sidewalk_no_nearby = int(nearby_roads_50["has_sidewalk_no"].sum()) if not nearby_roads_50.empty else 0
        lit_no_nearby = int(nearby_roads_50["has_lit_no"].sum()) if not nearby_roads_50.empty else 0
        nearby_sidewalk_tag_count = int(nearby_roads_50["has_sidewalk_tag"].sum()) if not nearby_roads_50.empty else 0
        nearby_lit_tag_count = int(nearby_roads_50["has_lit_tag"].sum()) if not nearby_roads_50.empty else 0

        risk_score = 0
        risk_flags = []
        if major_road_within_150m:
            risk_score += 25
            risk_flags.append("major_road_within_150m")
        if not crossing_within_150m:
            risk_score += 25
            risk_flags.append("no_mapped_crossing_within_150m")
        if crossing_near_major_without_signal:
            risk_score += 15
            risk_flags.append("nearest_crossing_near_major_road_without_signal_within_50m")
        if traffic_calming_within_100m == 0:
            risk_score += 10
            risk_flags.append("no_mapped_traffic_calming_within_100m_weak_indicator")
        if sidewalk_no_nearby > 0:
            risk_score += 10
            risk_flags.append("explicit_sidewalk_no_within_50m")
        if lit_no_nearby > 0:
            risk_score += 5
            risk_flags.append("explicit_lit_no_within_50m")

        data_quality_flags = ["pilot_boundary_osm_geofabrik_not_official"]
        if not pbf_enrichment_used:
            data_quality_flags.append("raw_pbf_tag_enrichment_not_used_in_generic_zip_mapper")
        if crossing_detail_missing:
            data_quality_flags.append("nearest_crossing_detail_tags_missing")
        if not nearby_roads_50.empty and nearby_sidewalk_tag_count == 0:
            data_quality_flags.append("nearby_sidewalk_tags_missing")
        if not nearby_roads_50.empty and nearby_lit_tag_count == 0:
            data_quality_flags.append("nearby_lit_tags_missing")
        if nearest_major is not None and major_road_within_150m and not safe_str(nearest_major.get("maxspeed_effective")):
            data_quality_flags.append("nearby_major_road_maxspeed_missing")

        records.append({
            "generator_id": gen["generator_id"],
            "osm_id": safe_str(gen.get("osm_id")),
            "generator_type": safe_str(gen.get("generator_type")),
            "name": safe_str(gen.get("name")),
            "source_layer": safe_str(gen.get("source_layer")),
            "nearest_crossing_id": nearest_crossing_id,
            "nearest_crossing_m": round(nearest_crossing_m, 1) if not math.isnan(nearest_crossing_m) else "",
            "crossing_within_100m": crossing_within_100m,
            "crossing_within_150m": crossing_within_150m,
            "nearest_major_road_id": safe_str(nearest_major.get("road_id")) if nearest_major is not None else "",
            "nearest_major_road_class": safe_str(nearest_major.get("highway_class")) if nearest_major is not None else "",
            "nearest_major_road_m": round(nearest_major_m, 1) if not math.isnan(nearest_major_m) else "",
            "major_road_within_150m": major_road_within_150m,
            "signals_within_50m": signals_within_50m,
            "nearest_crossing_signals_within_50m": nearest_crossing_signals_within_50m,
            "nearest_crossing_major_road_m": round(nearest_crossing_major_road_m, 1) if not math.isnan(nearest_crossing_major_road_m) else "",
            "traffic_calming_within_100m": traffic_calming_within_100m,
            "sidewalk_no_roads_within_50m": sidewalk_no_nearby,
            "lit_no_roads_within_50m": lit_no_nearby,
            "risk_score": risk_score,
            "risk_flags": json_list(risk_flags),
            "data_quality_flags": json_list(data_quality_flags),
            "review_wording": REVIEW_WORDING,
            "geometry": geom,
        })

    return gpd.GeoDataFrame(records, geometry="geometry", crs=ANALYSIS_CRS).sort_values(["risk_score", "nearest_crossing_m"], ascending=[False, False])


def add_csv_geometry_columns(gdf):
    modules = import_gis_modules()
    pd = modules["pd"]
    out = gdf.copy()
    out["geometry_wkt"] = out.geometry.to_wkt()
    lonlat = out.to_crs(SOURCE_CRS)
    label_points = lonlat.geometry.representative_point()
    out["lon"] = label_points.x
    out["lat"] = label_points.y
    return pd.DataFrame(out.drop(columns=["geometry"]))


def write_csv(path: Path, gdf_or_df) -> None:
    modules = import_gis_modules()
    gpd = modules["gpd"]
    if isinstance(gdf_or_df, gpd.GeoDataFrame):
        df = add_csv_geometry_columns(gdf_or_df)
    else:
        df = gdf_or_df.copy()
    df.to_csv(path, index=False, encoding="utf-8-sig")


def clean_frame(gdf, columns: list[str] | None = None):
    if columns is None:
        out = gdf.copy()
    else:
        keep = [col for col in columns if col in gdf.columns] + ["geometry"]
        out = gdf[keep].copy()
    for col in out.columns:
        if col != "geometry" and out[col].dtype == "object":
            out[col] = out[col].map(safe_str)
    return out


def write_data_dictionary(path: Path) -> None:
    rows = [
        ["table", "field", "required", "reliability", "notes"],
        ["pedestrian_generators", "generator_id", "yes", "derived_stable", "Local generated identifier."],
        ["pedestrian_generators", "generator_type", "yes", "template_mapped", "Mapped from Geofabrik fclass."],
        ["crossings", "crossing_type", "yes", "source_dependent", "Generic ZIP mapper uses pedestrian_crossing where detailed tags are unavailable."],
        ["road_segments", "highway_class", "yes", "source_dependent", "Mapped from Geofabrik fclass."],
        ["risk_assessment_results", "risk_score", "yes", "rule_based_v001", "Transparent prioritization score for field review."],
        ["risk_assessment_results", "risk_flags", "yes", "derived", "Infrastructure risk indicators."],
        ["risk_assessment_results", "data_quality_flags", "yes", "derived", "Missing/incomplete OSM evidence separated from risk score."],
        ["risk_assessment_results", "review_wording", "yes", "policy_required", "Approved wording for all candidate rows."],
    ]
    path.write_text("\n".join(",".join(row) for row in rows) + "\n", encoding="utf-8")


def build_workspace(
    source_zip: Path,
    source_pbf: Path | None,
    workspace_dir: Path,
    workspace_id: str,
    source_dataset_id: str,
    source_file_name: str,
    pilot_osm_id: str,
    pilot_name: str,
) -> dict:
    start = datetime.now(timezone.utc)
    tables_dir = workspace_dir / "tables"
    reports_dir = workspace_dir / "reports"
    tables_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    pilot, pilot_geom, bbox = load_pilot_boundary(source_zip, pilot_osm_id)
    layers = load_pilot_layers(source_zip, pilot_geom, bbox)
    pbf_layers = load_pbf_layers(source_pbf, pilot_geom, bbox)
    pbf_enrichment_used = bool(pbf_layers["used"])
    generators = build_generators(layers, pbf_layers["points"], pbf_layers["multipolygons"], pbf_enrichment_used)
    crossings, signals, street_lamps = build_crossings(layers["gis_osm_traffic_free_1"], pbf_layers["points"])
    roads, major_roads = build_roads(layers["gis_osm_roads_free_1"], pbf_layers["lines"])
    traffic_calming = build_traffic_calming(layers["gis_osm_traffic_free_1"], pbf_layers["points"], pbf_layers["lines"])
    risk = build_risk_results(generators, crossings, signals, roads, major_roads, traffic_calming, pbf_enrichment_used)
    top20 = risk.head(20).copy()

    write_csv(tables_dir / "pedestrian_generators.csv", clean_frame(generators, ["generator_id", "osm_id", "generator_type", "name", "source_layer", "original_geometry_type", "data_quality_flags"]))
    write_csv(tables_dir / "crossings.csv", clean_frame(crossings, ["crossing_id", "osm_id", "crossing_type", "has_signal_nearby", "tactile_paving", "kerb", "crossing_island"]))
    write_csv(tables_dir / "road_segments.csv", clean_frame(roads, ["road_id", "osm_id", "highway_class", "name", "maxspeed", "maxspeed_effective", "oneway", "oneway_effective", "sidewalk", "lit"]))
    write_csv(tables_dir / "risk_assessment_results.csv", risk)
    write_csv(tables_dir / "risk_assessment_top20.csv", top20)

    counts = {
        "pedestrian_generators": int(len(generators)),
        "schools": int((generators["generator_type"] == "school").sum()) if not generators.empty else 0,
        "kindergartens": int((generators["generator_type"] == "kindergarten").sum()) if not generators.empty else 0,
        "childcare": int((generators["generator_type"] == "childcare").sum()) if not generators.empty else 0,
        "bus_stops": int((generators["generator_type"] == "bus_stop").sum()) if not generators.empty else 0,
        "parks": int((generators["generator_type"] == "park").sum()) if not generators.empty else 0,
        "playgrounds": int((generators["generator_type"] == "playground").sum()) if not generators.empty else 0,
        "community_centres": int((generators["generator_type"] == "community_centre").sum()) if not generators.empty else 0,
        "crossings": int(len(crossings)),
        "traffic_signals": int(len(signals)),
        "street_lamps": int(len(street_lamps)),
        "road_segments": int(len(roads)),
        "major_roads": int(len(major_roads)),
        "traffic_calming_features": int(len(traffic_calming)),
    }
    validation = {
        "passed": bool(counts["pedestrian_generators"] > 0 and counts["crossings"] > 0 and counts["road_segments"] > 0),
        "analysis_crs": ANALYSIS_CRS,
        "source_crs": SOURCE_CRS,
        "pilot_osm_id": str(pilot_osm_id),
        "pilot_name": pilot_name,
        "source_zip": str(source_zip),
        "source_pbf": str(source_pbf) if source_pbf else "",
        "generic_mapper": "geofabrik_zip_plus_osm_pbf_v001" if pbf_enrichment_used else "geofabrik_shapefile_zip_v001",
        "raw_pbf_enrichment_used": pbf_enrichment_used,
        "pbf_points": int(len(pbf_layers["points"])),
        "pbf_lines": int(len(pbf_layers["lines"])),
        "pbf_multipolygons": int(len(pbf_layers["multipolygons"])),
        "review_wording_exact": bool((risk["review_wording"] == REVIEW_WORDING).all()) if not risk.empty else False,
        "risk_results_rows": int(len(risk)),
    }
    summary = {
        "workspace_id": workspace_id,
        "template_id": "safe_access",
        "pilot_area": pilot_name,
        "analysis_crs": ANALYSIS_CRS,
        "review_wording": REVIEW_WORDING,
        "counts": counts,
        "validation": validation,
        "scoring": {
            "major_road_within_150m": 25,
            "no_mapped_crossing_within_150m": 25,
            "nearest_crossing_near_major_road_without_signal_within_50m": 15,
            "no_mapped_traffic_calming_within_100m_weak_indicator": 10,
            "explicit_sidewalk_no_within_50m": 10,
            "explicit_lit_no_within_50m": 5,
            "missing_tags_add_risk_points": 0,
        },
    }
    (reports_dir / "workspace_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    quality_report = {
        "workspace_id": workspace_id,
        "data_quality_principles": [
            "Missing OSM tags are data-quality gaps, not proof that infrastructure is absent.",
            "Risk flags are infrastructure risk indicators for field review prioritization.",
            "The workspace is not a crash prediction model.",
        ],
        "known_limitations": [
            "Pilot boundary is OSM/Geofabrik based, not an official municipal boundary.",
            "PBF enrichment improves tag evidence, but OSM tag absence remains a data-quality gap only.",
            "This mapper still uses a simple nearest-distance model, not a routable pedestrian network.",
        ],
    }
    (reports_dir / "quality_report.json").write_text(json.dumps(quality_report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_data_dictionary(reports_dir / "data_dictionary.csv")
    template_mapping = {
        "template_id": "safe_access",
        "mapper": validation["generic_mapper"],
        "source_dataset_id": source_dataset_id,
        "source_file_name": source_file_name,
        "source_pbf": str(source_pbf) if source_pbf else "",
        "pilot_osm_id": str(pilot_osm_id),
        "required_layers": REQUIRED_GEOFABRIK_LAYERS,
        "canonical_tables": [
            {"table": "pedestrian_generators", "file": str(tables_dir / "pedestrian_generators.csv"), "rows": counts["pedestrian_generators"]},
            {"table": "crossings", "file": str(tables_dir / "crossings.csv"), "rows": counts["crossings"]},
            {"table": "road_segments", "file": str(tables_dir / "road_segments.csv"), "rows": counts["road_segments"]},
            {"table": "risk_assessment_results", "file": str(tables_dir / "risk_assessment_results.csv"), "rows": int(len(risk))},
            {"table": "risk_assessment_top20", "file": str(tables_dir / "risk_assessment_top20.csv"), "rows": int(len(top20))},
        ],
    }
    (reports_dir / "template_mapping.json").write_text(json.dumps(template_mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    readme = (
        f"# {pilot_name} Safe Access Generic Workspace\n\n"
        "Generated by GeoReview Studio v005 generic Geofabrik ZIP + OSM PBF mapper.\n\n"
        f"Approved review wording: `{REVIEW_WORDING}`\n\n"
        "Source GIS files were not modified.\n"
    )
    (workspace_dir / "README.md").write_text(readme, encoding="utf-8")

    finished = datetime.now(timezone.utc)
    manifest = {
        "workspace_id": workspace_id,
        "template_id": "safe_access",
        "created_by": "GeoReview Studio v005 PBF-enriched generic safe access mapper",
        "created_at_utc": finished.isoformat(),
        "runtime_seconds": round((finished - start).total_seconds(), 2),
        "source_dataset_id": source_dataset_id,
        "source_file_name": source_file_name,
        "source_path": str(source_zip),
        "source_pbf": str(source_pbf) if source_pbf else "",
        "source_gis_modified": False,
        "mapper": validation["generic_mapper"],
        "raw_pbf_enrichment_used": pbf_enrichment_used,
        "workspace_dir": str(workspace_dir),
        "tables_dir": str(tables_dir),
        "reports_dir": str(reports_dir),
        "tables": template_mapping["canonical_tables"],
        "reports": {
            "workspace_summary": str(reports_dir / "workspace_summary.json"),
            "quality_report": str(reports_dir / "quality_report.json"),
            "data_dictionary": str(reports_dir / "data_dictionary.csv"),
            "template_mapping": str(reports_dir / "template_mapping.json"),
        },
        "validation": validation,
    }
    (workspace_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "manifest": manifest}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Safe Access canonical workspace from a Geofabrik Shapefile ZIP.")
    parser.add_argument("--source-zip", required=True)
    parser.add_argument("--source-pbf", default="")
    parser.add_argument("--workspace-dir", required=True)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--source-dataset-id", required=True)
    parser.add_argument("--source-file-name", required=True)
    parser.add_argument("--pilot-osm-id", default="53796999")
    parser.add_argument("--pilot-name", default="Kfar Saba")
    parser.add_argument("--result-json", required=True)
    args = parser.parse_args()

    result = build_workspace(
        source_zip=Path(args.source_zip),
        source_pbf=Path(args.source_pbf) if args.source_pbf else None,
        workspace_dir=Path(args.workspace_dir),
        workspace_id=args.workspace_id,
        source_dataset_id=args.source_dataset_id,
        source_file_name=args.source_file_name,
        pilot_osm_id=args.pilot_osm_id,
        pilot_name=args.pilot_name,
    )
    Path(args.result_json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
