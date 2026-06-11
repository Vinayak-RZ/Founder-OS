from memory import world_templates as wt


def test_startup_template_has_facets():
    t = wt.get_template("startup")
    assert t is not None
    assert len(t["facets"]) >= 6
    ids = {f["id"] for f in t["facets"]}
    assert "leads" in ids
    assert "product" in ids


def test_kind_mapping():
    assert wt.template_for_kind("project") == "startup"
    assert wt.template_for_kind("technical") == "technical"
