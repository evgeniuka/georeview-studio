"""Unit tests for the portfolio generator's pure helpers (no data store needed)."""

import importlib

gen = importlib.import_module("generate_portfolio_artifacts")

BOUNDS = {"min_lon": 34.9, "max_lon": 35.0, "min_lat": 32.1, "max_lat": 32.2}


def test_parse_float():
    assert gen.parse_float("3.5") == 3.5
    assert gen.parse_float("") == 0.0
    assert gen.parse_float(None) == 0.0
    assert gen.parse_float("bad") == 0.0
    assert gen.parse_float("bad", 1.0) == 1.0


def test_parse_int():
    assert gen.parse_int("5") == 5
    assert gen.parse_int("5.9") == 5
    assert gen.parse_int("") == 0
    assert gen.parse_int(None, 7) == 7


def test_parse_list():
    assert gen.parse_list('["a", "b"]') == ["a", "b"]
    assert gen.parse_list("") == []
    assert gen.parse_list("not json") == []
    assert gen.parse_list('{"k": 1}') == []  # valid JSON but not a list


def test_project_point_inside_canvas():
    width, height = 980, 620
    for lon, lat in [(34.9, 32.1), (35.0, 32.2), (34.95, 32.15)]:
        x, y = gen.project_point({"lon": lon, "lat": lat}, BOUNDS, width, height)
        assert 0 <= x <= width
        assert 0 <= y <= height


def test_project_point_orientation():
    width, height = 980, 620
    south = gen.project_point({"lon": 34.95, "lat": 32.1}, BOUNDS, width, height)
    north = gen.project_point({"lon": 34.95, "lat": 32.2}, BOUNDS, width, height)
    assert north[1] < south[1]  # higher latitude -> nearer the top (smaller y)
    west = gen.project_point({"lon": 34.9, "lat": 32.15}, BOUNDS, width, height)
    east = gen.project_point({"lon": 35.0, "lat": 32.15}, BOUNDS, width, height)
    assert west[0] < east[0]  # higher longitude -> further right (larger x)
