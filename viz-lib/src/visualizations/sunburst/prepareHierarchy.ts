import { has, map, keys, groupBy, sortBy, filter, find, compact, first, every, identity } from "lodash";

const exitNode = "<<<Exit>>>";

function buildNodesFromHierarchyData(data: any) {
  const grouped = groupBy(data, "sequence");
  return map(grouped, value => {
    const sorted = sortBy(value, "stage");
    return {
      size: value[0].value || 0,
      sequence: value[0].sequence,
      nodes: map(sorted, i => i.node),
    };
  });
}

function buildNodesFromTableData(data: any) {
  const validKey = (key: any) => key !== "value";
  const dataKeys = sortBy(filter(keys(data[0]), validKey), identity);

  return map(data, (row, sequence) => ({
    size: row.value || 0,
    sequence,
    nodes: compact(map(dataKeys, key => row[key])),
  }));
}

function isDataInHierarchyFormat(data: any) {
  const firstRow = first(data);
  return every(["sequence", "stage", "node", "value"], field => has(firstRow, field));
}

export function buildSunburstHierarchy(rows: any[]) {
  let data = isDataInHierarchyFormat(rows) ? buildNodesFromHierarchyData(rows) : buildNodesFromTableData(rows);

  const root: any = {
    id: "root",
    children: [] as any[],
  };

  data.forEach((d: any) => {
    const nodes = d.nodes;
    const size = parseInt(d.size, 10);

    let currentNode = root;
    for (let j = 0; j < nodes.length; j += 1) {
      let children = currentNode.children;
      const nodeName = nodes[j];
      const isLeaf = j + 1 === nodes.length;

      if (!children) {
        currentNode.children = children = [];
        children.push({
          id: exitNode,
          value: currentNode.value ?? 0,
        });
      }

      let childNode = find(children, child => child.id === nodeName);

      if (isLeaf && childNode) {
        childNode.children = childNode.children || [];
        childNode.children.push({
          id: exitNode,
          value: size,
        });
      } else if (isLeaf) {
        children.push({
          id: nodeName,
          value: size,
        });
      } else {
        if (!childNode) {
          childNode = {
            id: nodeName,
            children: [],
          };
          children.push(childNode);
        }
        currentNode = childNode;
      }
    }
  });

  return root;
}

export function isSunburstDataValid(data: { rows: any[] }) {
  return data && data.rows.length > 0;
}
