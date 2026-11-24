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
    assert len(body["history"]) == 2
    assert body["history"][0]["ply"] == 0
    assert body["history"][0]["actor"] == "initial"
    assert body["history"][1]["actor"] == "ai"
    assert body["history"][1]["ply"] == 1
    assert body["history"][1]["evidence"] is not None


def test_history_records_human_and_ai_snapshots_and_resets_on_new_game():
    r_new = client.post("/game/new", json={"k": 2, "human_color": "R"})
    assert r_new.status_code == 200
    assert len(r_new.json()["history"]) == 1
    assert r_new.json()["history"][0]["ply"] == 0
    assert r_new.json()["history"][0]["actor"] == "initial"

    r1 = client.post("/game/move", json={"column": 3})
    assert r1.status_code == 200
    body = r1.json()
    history = body["history"]
    assert len(history) == 3

    init_ply, human_ply, ai_ply = history[0], history[1], history[2]
    assert init_ply["ply"] == 0
    assert init_ply["actor"] == "initial"
    assert init_ply["grid"][0][3] == "."

    assert human_ply["ply"] == 1
    assert human_ply["actor"] == "human"
    assert human_ply["color"] == "R"
    assert human_ply["column"] == 3
    assert human_ply["evidence"] is None
    assert human_ply["grid"][0][3] == "R"

    assert ai_ply["ply"] == 2
    assert ai_ply["actor"] == "ai"
    assert ai_ply["color"] == "Y"
    assert ai_ply["column"] == body["ai_column"]
    assert ai_ply["evidence"] is not None
    assert ai_ply["evidence"]["role"] in ("MAX", "MIN")
    assert "value" in ai_ply["evidence"]
    assert "alpha" in ai_ply["evidence"]
    assert "beta" in ai_ply["evidence"]
    assert isinstance(ai_ply["evidence"]["pruned"], bool)

    r_reset = client.post("/game/new", json={"k": 2, "human_color": "R"})
    assert r_reset.status_code == 200
    assert len(r_reset.json()["history"]) == 1
    assert r_reset.json()["history"][0]["actor"] == "initial"
