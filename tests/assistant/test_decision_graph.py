"""Tests for assistant decision graph tracking."""

from rewatch.assistant.decision_graph import DecisionGraph


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
