import pytest

from agent import skills_factory


def test_empty_body_raises():
    with pytest.raises(ValueError):
        skills_factory.build_source("my_tool", "desc", {"type": "object", "properties": {}}, body="")


def test_whitespace_body_raises():
    with pytest.raises(ValueError):
        skills_factory.build_source("my_tool", "desc", {}, body="   \n  \n")


def test_valid_body_builds_source():
    src = skills_factory.build_source(
        "currency_double", "double a number",
        {"type": "object", "properties": {"n": {"type": "number"}}},
        body="return kwargs.get('n', 0) * 2",
    )
    assert "def currency_double" in src
    assert "return kwargs.get('n', 0) * 2" in src
