import pytest
from astroshield.model import load_scenario, get_satellite_positions
from astroshield.viz import render_scene

def test_render_scene_basic():
    sc = load_scenario("scenarios/base.json")
    positions = get_satellite_positions(sc, t=0.0)
    
    scene = render_scene(sc, positions)
    assert isinstance(scene, dict)
    assert "satellites_count" in scene
    assert "status" in scene
    assert scene["status"] == "rendered"
    