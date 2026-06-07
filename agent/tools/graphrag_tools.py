"""GraphRAG tools — global, thematic reasoning over the knowledge graph."""
from agent.registry import register
from memory import graphrag, graph


@register(
    name="ask_network",
    description="Answer a BIG-PICTURE question about the founder's network/business by "
                "reasoning over knowledge-graph community summaries (GraphRAG), e.g. 'how is "
                "my network clustered?', 'which parts of my world touch fintech?', 'who are "
                "the hubs connecting my contacts?'. Use this for thematic/global questions; "
                "use graph_lookup for a single person/company.",
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string"},
            "top_n": {"type": "integer", "description": "How many communities to consider (default 4)."},
        },
        "required": ["question"],
    },
    category="memory",
)
async def ask_network(question, top_n=4):
    try:
        top_n = max(1, min(int(top_n or 4), 10))
    except (TypeError, ValueError):
        top_n = 4
    return await graphrag.global_answer(question, top_n=top_n)


@register(
    name="rebuild_network_map",
    description="Refresh the knowledge graph from the CRM, detect communities, and regenerate "
                "their summaries (GraphRAG index). Run after adding many contacts/relationships "
                "or if ask_network seems stale. Returns the discovered communities.",
    parameters={"type": "object", "properties": {}},
    category="memory",
)
async def rebuild_network_map():
    try:
        graph.build_from_crm()
    except Exception:
        pass
    return await graphrag.build_communities()


@register(
    name="list_network_map",
    description="List the current knowledge-graph communities and their summaries (no rebuild).",
    parameters={"type": "object", "properties": {}},
    category="memory",
)
def list_network_map():
    items = graphrag.list_communities()
    return {"communities": len(items), "items": items}
