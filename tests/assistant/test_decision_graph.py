"""Tests for assistant decision graph tracking."""

from rewatch.assistant.decision_graph import DecisionGraph, merge_thread_decision_graph


def test_decision_graph_builds_hierarchy():
    events = []
    graph = DecisionGraph(on_activity=lambda event: events.append(event))
    graph.start()
    graph.start_step(0)
    graph.add_decision(label="Using 1 tool", detail="Let me check.", tool_names=["list_data_sources"])
    tool_id = graph.start_tool(node_id="tc1", tool="list_data_sources", label="Listing data sources", arguments={})
    graph.finish_tool(tool_id, result_summary="3 items")
    graph.finish_step()
    graph.complete()

    payload = graph.to_dict()
    assert len(payload["nodes"]) >= 5
    assert payload["nodes"][0]["type"] == "root"
    assert any(node["type"] == "tool" for node in payload["nodes"])
    assert any(node["type"] == "decision" for node in payload["nodes"])
    assert events
    assert events[-1]["type"] == "graph"


def test_decision_graph_records_tool_error():
    graph = DecisionGraph()
    graph.start()
    graph.start_step(0)
    tool_id = graph.start_tool(node_id="tc1", tool="run_query", label="Running query", arguments={"query_id": 1})
    graph.finish_tool(tool_id, error="Permission denied")

    tool_nodes = [node for node in graph.nodes if node["type"] == "tool"]
    assert len(tool_nodes) == 1
    assert tool_nodes[0]["status"] == "error"
    assert tool_nodes[0]["error"] == "Permission denied"


def test_complete_outcome_follows_compose_decision():
    graph = DecisionGraph()
    graph.start()
    graph.start_step(0)
    compose_id = graph.add_decision(label="Composing final reply", detail="Here is the answer.")
    graph.finish_step()
    outcome_id = graph.complete(label="Reply sent", parent_id=compose_id)

    nodes = graph.to_dict()["nodes"]
    outcome = next(node for node in nodes if node["id"] == outcome_id)
    compose = next(node for node in nodes if node["id"] == compose_id)

    assert outcome["parent_id"] == compose_id
    assert nodes.index(compose) < nodes.index(outcome)


def test_merge_thread_decision_graph_links_turns():
    messages = [
        {"role": "user", "content": "List dashboards"},
        {
            "role": "assistant",
            "content": "Here you go.",
            "decision_graph": {
                "nodes": [
                    {"id": "g1", "parent_id": None, "type": "root", "label": "Analyzing"},
                    {"id": "g2", "parent_id": "g1", "type": "tool", "label": "Listing dashboards"},
                    {"id": "g3", "parent_id": "g1", "type": "outcome", "label": "Reply sent"},
                ]
            },
        },
        {"role": "user", "content": "Create one"},
        {
            "role": "assistant",
            "content": "Done.",
            "decision_graph": {
                "nodes": [
                    {"id": "g1", "parent_id": None, "type": "root", "label": "Planning"},
                    {"id": "g2", "parent_id": "g1", "type": "outcome", "label": "Reply sent"},
                ]
            },
        },
    ]

    merged = merge_thread_decision_graph(messages, "thread-1")

    assert merged["thread_id"] == "thread-1"
    assert any(node["type"] == "user" for node in merged["nodes"])
    assert merged["nodes"][0]["id"] == "turn0_user"
    assert merged["nodes"][1]["id"] == "turn0_g1"
    assert merged["nodes"][1]["parent_id"] == "turn0_user"
    assert merged["nodes"][4]["id"] == "turn1_user"
    assert merged["nodes"][4]["parent_id"] == "turn0_g3"
