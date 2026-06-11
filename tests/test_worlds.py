import memory.worlds as worlds


def test_get_tree_does_not_recurse():
    tree = worlds.get_tree()
    assert tree["root"] is not None
    assert tree["root"]["id"] == worlds.ROOT_ID


def test_create_child_and_snapshot():
    w = worlds.create_world(
        name="Test Research Idea",
        kind="research",
        description="Side project",
        context="Focus on battery materials.",
    )
    assert w["id"]
    block = worlds.snapshot_block(w["id"])
    assert "Test Research Idea" in block
    assert "battery materials" in block
    worlds.delete_world(w["id"])


def test_resolve_world_id_defaults_to_root():
    assert worlds.resolve_world_id(None) == worlds.ROOT_ID
    assert worlds.resolve_world_id("root") == worlds.ROOT_ID
    assert worlds.resolve_world_id("global") == worlds.ROOT_ID


def test_hierarchy_graph_structure():
    from dashboard import graph_viz

    tree = worlds.get_tree()
    g = graph_viz.build_world_hierarchy_graph(tree)
    types = {n["data"]["type"] for n in g["nodes"]}
    assert "world_root" in types
    assert "founder" in types
    world_ids = {n["data"].get("world_id") for n in g["nodes"] if n["data"].get("world_id")}
    assert worlds.ROOT_ID in world_ids
