import { NodePositions, NodeType, LinkType, ExtendedGraphDataType, GraphOptions } from "./types";
import { select } from "d3-selection";
import { forceLink, forceManyBody, forceCenter, forceSimulation } from "d3-force";

import { prepareRows, isDataValid, updateNodeMap } from "./graphData";
import { createTooltip, updateTooltip, hideTooltip } from "./graphTooltip";
import { getColorInterpolator } from "./graphUtils";
import { getNodeColorScale, createNodes, getNodeColor, updateNodes } from "./nodeUtils";
import { createLinks, updateLinks } from "./linkUtils";

// Builds a render function tied to the current data + options. The returned
// closure is then attached to a DOM element by `Renderer`.
export default function initGraph(
  data: ExtendedGraphDataType,
  options: GraphOptions,
  _onNodePositionsChange: (newPositions: NodePositions) => void,
  onNodeDelete: (nodeId: string) => void,
  onNodeRestore: (nodeId: string) => void,
  forceUpdate: () => void
) {
  if (!isDataValid(data)) {
    // Defensive: the editor doc tells the user the expected shape, but we
    // don't want to crash the page if a query returns garbage.
    console.error("Graph visualization: data is invalid (need 'value' column).");
    return (element: HTMLDivElement) => {
      select(element).selectAll("*").remove();
    };
  }

  const preparedRows = prepareRows(data.rows);
  const nodes: NodeType[] = [];
  const links: LinkType[] = [];
  const nodeMap: { [key: string]: NodeType } = {};
  const nodeTooltip = createTooltip("nodeTooltip");
  const linkTooltip = createTooltip("linkTooltip");

  preparedRows.forEach(row => {
    const sourceId = row.from as string;
    const targetId = row.to as string;
    const linkId = row.id || ("" as string);
    const linkValue = (row.value as number) || 0;
    const group = (row.group as string) || "";

    if (!options.deletedNodes[sourceId] && !options.deletedNodes[targetId]) {
      updateNodeMap(sourceId, targetId, linkValue, true, group, nodeMap, nodes);
      updateNodeMap(targetId, sourceId, linkValue, false, group, nodeMap, nodes);

      links.push({ source: sourceId, target: targetId, value: linkValue, id: linkId });
    }
  });

  const filteredNodes = nodes.filter(node => !options.deletedNodes[node.id]);
  const filteredLinks = links.filter(link => {
    const sourceId = typeof link.source === "object" ? link.source.id : link.source;
    const targetId = typeof link.target === "object" ? link.target.id : link.target;
    return !options.deletedNodes[sourceId] && !options.deletedNodes[targetId];
  });

  filteredNodes.forEach(node => {
    // `balance` = received - sent: a useful one-shot summary for any
    // edge-weighted directed graph.
    node.balance = (node.total_received || 0) - (node.total_sent || 0);
    node.grouping_id = node.groups.sort().join("-");

    if (options.initialNodePositions[node.id]) {
      // Stored positions are relative; we'll rescale to pixels in renderGraph.
      node.x = options.initialNodePositions[node.id].x;
      node.y = options.initialNodePositions[node.id].y;
    }
  });

  const colorInterpolator = getColorInterpolator(options.colorInterpolatorName);
  const colorScale = getNodeColorScale(filteredNodes, options.colorNodeBy, colorInterpolator);

  return function renderGraph(element: HTMLDivElement) {
    select(element).selectAll("*").remove();

    const margin = { top: 10, right: 10, bottom: 10, left: 10 };
    const width = element.offsetWidth - margin.left - margin.right;
    const height = element.offsetHeight - margin.top - margin.bottom;

    if (width <= 0 || height <= 0) {
      return;
    }

    filteredNodes.forEach((node: any) => {
      if (options.initialNodePositions[node.id]) {
        node.x = options.initialNodePositions[node.id].x * width;
        node.y = options.initialNodePositions[node.id].y * height;
        node.fx = node.x;
        node.fy = node.y;
      } else if (node.x === undefined || node.y === undefined) {
        node.x = Math.random() * width;
        node.y = Math.random() * height;
      }
    });

    const svg = select(element)
      .append("svg")
      .attr("class", "graph")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom);

    const container = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

    const createdLinks = createLinks(container, filteredLinks);
    const createdNodes = createNodes(container, filteredNodes, width, height, options.deletedNodes);

    let clicked: NodeType | null = null;

    select("body").on("click", function () {
      if (clicked) {
        select(clicked as any).style("fill", (d: any) => {
          return getNodeColor(d, "", options.colorNodeBy, colorScale);
        });
        clicked = null;
      }
      hideTooltip(nodeTooltip);
      hideTooltip(linkTooltip);
    });

    let simulation: any;

    createdNodes.on("click", function (event: MouseEvent, d: NodeType) {
      event.stopPropagation();
      if (clicked === d) {
        clicked = null;
        select(this).style("fill", getNodeColor(d, "", options.colorNodeBy, colorScale));
        hideTooltip(nodeTooltip);
      } else {
        if (clicked) {
          select(clicked as any).style("fill", getNodeColor(clicked, "", options.colorNodeBy, colorScale));
        }
        clicked = d;
        select(this).style("fill", "orange");
        updateTooltip(nodeTooltip, d, true, event);
      }
    });

    function initializeSimulation() {
      simulation = forceSimulation(filteredNodes)
        .force("link", forceLink<NodeType, LinkType>(filteredLinks).id((d: NodeType) => d.id))
        .force("charge", forceManyBody().strength(options.repulsion))
        .force("center", forceCenter(width / 2, height / 2))
        .on("tick", () => {
          createdLinks
            .attr("x1", d => (d.source as NodeType).x || 0)
            .attr("y1", d => (d.source as NodeType).y || 0)
            .attr("x2", d => (d.target as NodeType).x || 0)
            .attr("y2", d => (d.target as NodeType).y || 0);

          createdNodes.attr("transform", d => `translate(${d.x || 0}, ${d.y || 0})`);

          if (options.saveNodePositions) {
            // Rebind any saved relative positions on each tick so dragging a
            // node also persists through the next layout pass.
            const nodesWithPositions = filteredNodes.filter(node => node.x !== undefined && node.y !== undefined);
            const nodesWithPositionsMap = new Map(nodesWithPositions.map(node => [node.id, node]));

            nodesWithPositionsMap.forEach((node, id) => {
              const savedNode = options.initialNodePositions[id];
              if (savedNode) {
                node.x = savedNode.x;
                node.y = savedNode.y;
              }
            });
          }
        });
    }

    initializeSimulation();

    updateNodes(
      container,
      options,
      getNodeColorScale(filteredNodes, options.colorNodeBy, colorInterpolator),
      Math.min(...filteredNodes.map((n: any) => n.balance)),
      "",
      colorScale,
      nodeTooltip,
      createdLinks,
      new Set(filteredNodes),
      1,
      width,
      height,
      onNodeDelete,
      onNodeRestore,
      () => {
        initializeSimulation();
        simulation.alpha(1).restart();
        forceUpdate();
      }
    );

    updateLinks(
      container,
      options,
      (d: any) => d.value,
      () => 1,
      "",
      colorScale,
      linkTooltip,
      new Set(filteredNodes),
      new Set(filteredLinks),
      () => {
        if (simulation) {
          simulation.alpha(1).restart();
        }
        forceUpdate();
      }
    );

    simulation.alpha(1).restart();
  };
}
