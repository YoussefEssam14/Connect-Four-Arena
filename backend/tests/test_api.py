import pytest
from fastapi.testclient import TestClient
import services.game_service as gs_module
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset():
    gs_module._game = None
    yield
    gs_module._game = None


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_new_game_human_r():
    r = client.post("/game/new", json={"k": 2, "human_color": "R"})
    assert r.status_code == 200
    body = r.json()
    assert body["human_color"] == "R"
    assert body["ai_color"] == "Y"
    assert body["is_human_turn"] is True
    assert body["ai_column"] is None
    assert body["stats"] is None


def test_new_game_human_y_ai_opens():
    r = client.post("/game/new", json={"k": 2, "human_color": "Y"})
    assert r.status_code == 200
    body = r.json()
    assert body["human_color"] == "Y"
    assert body["ai_color"] == "R"
    assert body["is_human_turn"] is True
    assert body["ai_column"] is not None
    assert body["stats"] is not None


def test_get_state_no_game():
    r = client.get("/game")
    assert r.status_code == 400


def test_get_state_after_new_game():
    client.post("/game/new", json={"k": 2, "human_color": "R"})
    r = client.get("/game")
    assert r.status_code == 200
    assert "grid" in r.json()


def test_move_valid():
    client.post("/game/new", json={"k": 2, "human_color": "R"})
    r = client.post("/game/move", json={"column": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["grid"][0][3] != "."


def test_move_out_of_range():
    client.post("/game/new", json={"k": 2, "human_color": "R"})
    r = client.post("/game/move", json={"column": 99})
    assert r.status_code == 422


def test_tree_no_ai_move():
    client.post("/game/new", json={"k": 2, "human_color": "R"})
    r = client.get("/game/tree?max_depth=1")
    assert r.status_code == 404


def test_tree_after_ai_moves():
    client.post("/game/new", json={"k": 2, "human_color": "R"})
    client.post("/game/move", json={"column": 3})
    r = client.get("/game/tree?max_depth=1")
    assert r.status_code == 200
    assert "children" in r.json()


def test_new_game_ai_first():
    r = client.post("/game/new", json={"k": 2, "human_color": "Y"})
    assert r.status_code == 200
    body = r.json()
    assert body["ai_column"] is not None
    assert body["is_human_turn"] is True
