import asyncio

from agent import registry


def test_register_and_get():
    @registry.register(name="t_echo", description="echo", parameters={
        "type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]})
    def _echo(x):
        return {"echo": x}

    tool = registry.get("t_echo")
    assert tool is not None
    assert tool.name == "t_echo"


def test_call_sync_tool():
    @registry.register(name="t_add", description="add", parameters={"type": "object", "properties": {}})
    def _add(a=1, b=2):
        return a + b

    assert asyncio.run(registry.call("t_add", {"a": 3, "b": 4})) == 7


def test_call_async_tool():
    @registry.register(name="t_aecho", description="aecho", parameters={"type": "object", "properties": {}})
    async def _aecho(v="hi"):
        return v

    assert asyncio.run(registry.call("t_aecho", {"v": "yo"})) == "yo"


def test_unknown_tool_returns_error():
    res = asyncio.run(registry.call("does_not_exist", {}))
    assert "error" in res


def test_bad_arguments_handled():
    @registry.register(name="t_strict", description="strict", parameters={"type": "object", "properties": {}})
    def _strict(required_arg):
        return required_arg

    res = asyncio.run(registry.call("t_strict", {"wrong": 1}))
    assert isinstance(res, dict) and "error" in res
