import { isNil, map, extend, sortBy, filter, keys, values, identity } from "lodash";
import ColorPalette from "@/visualizations/ColorPalette";

export function prepareSankeyGraph(rows: any[]) {
  if (!rows?.length) {
    return { nodes: [], links: [] };
  }

  const nodesDict: Record<string, any> = {};
  const linksDict: Record<string, any> = {};
  const nodes: any[] = [];

  const validKey = (key: any) => key !== "value";
  const dataKeys = sortBy(filter(keys(rows[0]), validKey), identity);

  function normalizeName(name: any) {
    if (!isNil(name)) {
      return "" + name;
    }
    return "Exit";
  }

  function getNode(name: string, level: any) {
    name = normalizeName(name);
    const key = `${name}:${String(level)}`;
    let node = nodesDict[key];
    if (!node) {
      node = { name };
      node.id = nodes.push(node) - 1;
      nodesDict[key] = node;
    }
    return node;
  }

  function getLink(source: number, target: number) {
    const linkKey = `${source}-${target}`;
    let link = linksDict[linkKey];
    if (!link) {
      link = { source, target, value: 0 };
      linksDict[linkKey] = link;
    }
    return link;
  }

  function addLink(sourceName: any, targetName: any, value: any, depth: any) {
    if ((sourceName === "" || !sourceName) && depth > 1) {
      return;
    }
    const source = getNode(sourceName, depth);
    const target = getNode(targetName, depth + 1);
    const link = getLink(source.id, target.id);
    link.value += parseInt(value, 10);
  }

  rows.forEach((row: any) => {
    addLink(row[dataKeys[0]], row[dataKeys[1]], row.value || 0, 1);
    addLink(row[dataKeys[1]], row[dataKeys[2]], row.value || 0, 2);
    addLink(row[dataKeys[2]], row[dataKeys[3]], row.value || 0, 3);
    addLink(row[dataKeys[3]], row[dataKeys[4]], row.value || 0, 4);
    addLink(row[dataKeys[4]], null, row.value || 0, 5);
  });

  const palette = ColorPalette;
  const colorNames = Object.keys(palette).filter(k => typeof (palette as any)[k] === "string");
  const getColor = (name: string, i: number) => (palette as any)[colorNames[i % colorNames.length]] ?? "#356aff";

  return {
    nodes: map(nodes, (d, i) =>
      extend(d, {
        itemStyle: { color: getColor(d.name.replace(/ .*/, ""), i) },
      })
    ),
    links: values(linksDict),
  };
}

export function prepareSankeyRows(rows: any[]) {
  return map(rows, row =>
    Object.fromEntries(
      Object.entries(row).map(([k, v]) => {
        if (!v || typeof v === "number") {
          return [k, v];
        }
        const num = parseFloat(v as string);
        return [k, isNaN(num) ? v : num];
      })
    )
  );
}
