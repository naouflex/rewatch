import { prepareSankeyGraph, prepareSankeyRows } from "./prepareData";

describe("Sankey prepareData", () => {
  test("builds nodes and links from rows", () => {
    const rows = prepareSankeyRows([
      { s1: "a", s2: "b", s3: "c", s4: null, s5: null, value: 10 },
    ]);
    const graph = prepareSankeyGraph(rows);
    expect(graph.nodes.length).toBeGreaterThan(0);
    expect(graph.links.length).toBeGreaterThan(0);
  });
});
