import { buildSunburstHierarchy, isSunburstDataValid } from "./prepareHierarchy";

describe("Sunburst prepareHierarchy", () => {
  test("builds hierarchy from table data", () => {
    const rows = [
      { s1: "a", s2: "a1", s3: "a2", value: 11 },
      { s1: "a", s2: "a2", s3: null, value: 12 },
    ];
    expect(isSunburstDataValid({ rows })).toBe(true);
    const hierarchy = buildSunburstHierarchy(rows);
    expect(hierarchy.id).toBe("root");
    expect(hierarchy.children.length).toBeGreaterThan(0);
  });
});
