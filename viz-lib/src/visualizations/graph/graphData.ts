import { find, every, isFinite, isString, isNumber, map, mapValues } from "lodash";
import { ExtendedGraphDataType, NodeType } from "./types";

// Validates the query result has the columns we need (`value`) and that every
// row has the expected types: strings for `from`/`to`/`id`/`group` and numbers
// (or empty) for everything else.
export function isDataValid(data: ExtendedGraphDataType): boolean {
  if (!data || !find(data.columns, c => c.name === "value")) {
    return false;
  }
  return every(data.rows, row =>
    every(row, (v, key) => {
      if (key === "from" || key === "to" || key === "id" || key === "group") {
        return isString(v);
      }
      if (!v) {
        return true;
      }
      return isFinite(v);
    })
  );
}

export function prepareRows(rows: ExtendedGraphDataType["rows"]) {
  return map(rows, row =>
    mapValues(row, (v, key) => {
      if (key === "from" || key === "to" || key === "id" || key === "group") {
        return v;
      }
      if (key === "value") {
        // Force `value` into a number so the renderer never has to guess.
        return isNumber(v) ? v : isNaN(parseFloat(v as any)) ? 0 : parseFloat(v as any);
      }
      if (!v || isNumber(v)) {
        return v;
      }
      return isNaN(parseFloat(v)) ? v : parseFloat(v);
    })
  );
}

// Mutates `nodeMap` and `nodes` in place: ensures a node exists for `id`, then
// folds the link's contribution into its running totals.
export function updateNodeMap(
  id: string,
  connectedId: string,
  value: number,
  isSent: boolean,
  group: string,
  nodeMap: { [key: string]: NodeType },
  nodes: NodeType[]
) {
  if (!nodeMap[id]) {
    nodeMap[id] = {
      id,
      name: id,
      color: "",
      balance: 0,
      link_count: 0,
      total_sent: 0,
      total_received: 0,
      groups: [],
      connected_nodes: [],
    } as NodeType;
    nodes.push(nodeMap[id]);
  }
  if (isSent) {
    nodeMap[id].total_sent! += value;
  } else {
    nodeMap[id].total_received! += value;
  }
  nodeMap[id].link_count! += 1;
  if (group && nodeMap[id].groups.indexOf(group) === -1) {
    nodeMap[id].groups.push(group);
  }
  if (connectedId) {
    if (nodeMap[id].connected_nodes!.indexOf(connectedId) === -1) {
      nodeMap[id].connected_nodes!.push(connectedId);
    }
  }
}
