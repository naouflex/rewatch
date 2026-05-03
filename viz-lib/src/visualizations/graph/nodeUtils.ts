import { scaleSequential, scaleOrdinal, scaleLinear } from "d3-scale";
import { Selection, select } from "d3-selection";
import { min, max } from "d3-array";

import { generateNodeTooltipHtml, updateTooltip, hideTooltip, updateTooltipPosition, tooltipCache, CACHE_TIMEOUT } from "./graphTooltip";
import { getLinkColor } from "./linkUtils";
import { NodeType, DeletedNodes, GraphOptions } from "./types";
import { relativeToAbsolutePosition } from "./graphUtils";

let isDragging = false;

const handleMouseover = (
  event: MouseEvent,
  d: any,
  nodeTooltip: any,
  selectedNodes: Set<any>,
  minBalance: number,
  sizeNodeBy: string,
  nodeSizeScale: any,
  link: any,
  nodeGroups: any
) => {
  event.stopPropagation();
  updateTooltip(nodeTooltip, d, false, event);
  if (!selectedNodes.has(d)) {
    select(event.target as Element).style("fill", "orange");
    select(event.target as Element).attr("r", getRadius(d, minBalance, sizeNodeBy, nodeSizeScale) * 1.5);
  }

  // Highlight connected links + neighbour nodes whether the node is hovered or
  // already clicked-selected.
  link.style("stroke", (l: any) => {
    return l.source === d ||
      l.target === d ||
      Array.from(selectedNodes).some((selectedNode: any) => l.source === selectedNode || l.target === selectedNode)
      ? "orange"
      : "var(--graph-text-color)";
  });

  if (!selectedNodes.has(d)) {
    const connectedIds = d.connected_nodes || [];
    connectedIds.forEach((id: string) => {
      nodeGroups
        .selectAll("circle")
        .filter((dd: any) => dd.id.toLowerCase().includes(id.toLowerCase()))
        .style("fill", "orange");
    });
  }

  const cachedData = tooltipCache[d.id];
  const now = Date.now();
  if (cachedData && now - cachedData.timestamp < CACHE_TIMEOUT) {
    nodeTooltip.html(cachedData.data);
  } else {
    const tooltipHtml = generateNodeTooltipHtml(d);
    tooltipCache[d.id] = { data: tooltipHtml, timestamp: now };
    nodeTooltip.html(tooltipHtml);
  }
};

export function getRadius(d: any, minBalance: number, sizeNodeBy: string, nodeSizeScale: any) {
  switch (sizeNodeBy) {
    case "balance":
      return nodeSizeScale(Math.max(d.balance, minBalance));
    case "linkCount":
      return nodeSizeScale(d.link_count);
    case "totalSent":
      return nodeSizeScale(d.total_sent);
    case "totalReceived":
      return nodeSizeScale(d.total_received);
    default:
      return nodeSizeScale(Math.max(d.balance, minBalance));
  }
}

export function getNodeColor(d: NodeType, searchTerm: string, colorNodeBy: string, colorScale: any): string {
  const idIncludesSearch = d.id.toLowerCase().includes(searchTerm.toLowerCase());
  const connectedToSearch = (d.connected_nodes || []).some((id: string) => id.toLowerCase().includes(searchTerm.toLowerCase()));
  if (searchTerm) {
    return idIncludesSearch || connectedToSearch ? "orange" : "lightgrey";
  }
  switch (colorNodeBy) {
    case "balance":
      return colorScale(d.balance);
    case "linkCount":
      return colorScale(d.link_count);
    case "totalSent":
      return colorScale(d.total_sent);
    case "totalReceived":
      return colorScale(d.total_received);
    case "group":
      return colorScale(d.grouping_id);
    default:
      return colorScale(d.balance);
  }
}

export function getNodeColorScale(nodes: NodeType[], colorNodeBy: string, colorInterpolator: any) {
  let colorScale: any;
  const maxBalance = max(nodes, (d: NodeType) => d.balance!)!;
  const maxLinkCount = max(nodes, (d: NodeType) => d.link_count!)!;
  const groupingIdCount = new Set(nodes.map((d: NodeType) => d.grouping_id)).size;
  const totalSent = max(nodes, (d: NodeType) => d.total_sent!)!;
  const totalReceived = max(nodes, (d: NodeType) => d.total_received!)!;

  switch (colorNodeBy) {
    case "balance":
      colorScale = scaleSequential(colorInterpolator).domain([-maxBalance, maxBalance] as any);
      break;
    case "totalSent":
      colorScale = scaleSequential(colorInterpolator).domain([0, totalSent] as any);
      break;
    case "totalReceived":
      colorScale = scaleSequential(colorInterpolator).domain([0, totalReceived] as any);
      break;
    case "linkCount":
      colorScale = scaleSequential(colorInterpolator).domain([-maxLinkCount, maxLinkCount] as any);
      break;
    case "group":
      colorScale = scaleOrdinal()
        .domain([...Array.from({ length: groupingIdCount }).keys()].map(String))
        .range([...Array.from({ length: groupingIdCount }).keys()].map((d: any) => colorInterpolator(d / groupingIdCount)));
      break;
    default:
      colorScale = scaleSequential(colorInterpolator).domain([-maxBalance, maxBalance] as any);
      break;
  }
  return colorScale;
}

export function getNodeSizeScale(nodes: NodeType[], sizeNodeBy: string, minNodeSize: number, maxNodeSize: number) {
  let nodeSizeScale;
  const minBalance: any = min(nodes, (d: NodeType) => d.balance!)!;
  const maxBalance: any = max(nodes, (d: NodeType) => d.balance!)!;
  const maxLinkCount: any = max(nodes, (d: NodeType) => d.link_count!)!;
  const maxTotalSent: any = max(nodes, (d: NodeType) => d.total_sent!)!;
  const maxTotalReceived: any = max(nodes, (d: NodeType) => d.total_received!)!;

  // Negative or zero balances would break the linear scale, so we floor at 1.
  const minBalancePositive = Math.max(minBalance, 1);
  switch (sizeNodeBy) {
    case "balance":
      nodeSizeScale = scaleLinear().domain([minBalancePositive, maxBalance]).range([minNodeSize, maxNodeSize]).clamp(true);
      break;
    case "totalSent":
      nodeSizeScale = scaleLinear().domain([1, maxTotalSent]).range([minNodeSize, maxNodeSize]).clamp(true);
      break;
    case "totalReceived":
      nodeSizeScale = scaleLinear().domain([1, maxTotalReceived]).range([minNodeSize, maxNodeSize]).clamp(true);
      break;
    case "linkCount":
      nodeSizeScale = scaleLinear().domain([1, maxLinkCount]).range([minNodeSize, maxNodeSize]).clamp(true);
      break;
    default:
      nodeSizeScale = scaleLinear().domain([1, maxLinkCount]).range([minNodeSize, maxNodeSize]).clamp(true);
  }
  return nodeSizeScale;
}

export function createNodes(
  container: Selection<SVGGElement, unknown, null, undefined>,
  nodes: NodeType[],
  width: number,
  height: number,
  deletedNodes: DeletedNodes
) {
  const nodeGroups = container
    .append("g")
    .attr("class", "nodes")
    .selectAll(".node")
    .data(nodes)
    .enter()
    .append("g")
    .attr("class", "node")
    .attr("transform", d => {
      // Without a saved position, drop the node somewhere random in the
      // viewport so the force layout can spread them out.
      if (d.x === undefined || d.y === undefined) {
        d.x = Math.random() * width;
        d.y = Math.random() * height;
      }
      return `translate(${d.x}, ${d.y})`;
    })
    .classed("deleted", d => deletedNodes[d.id]);

  nodeGroups
    .append("circle")
    .attr("r", 5) // overwritten by updateNodes once size scale is known
    .style("opacity", d => (deletedNodes[d.id] ? 0.5 : 1));

  nodeGroups
    .append("text")
    .attr("dy", ".35em")
    .attr("text-anchor", "middle")
    .text(d => (deletedNodes[d.id] ? "" : d.id))
    .style("font-size", "10px")
    .style("pointer-events", "none");

  return nodeGroups;
}

export function updateNodes(
  container: Selection<SVGGElement, unknown, null, undefined>,
  options: GraphOptions,
  nodeSizeScale: (value: number) => number,
  minBalance: number,
  searchTerm: string,
  colorScale: (d: any) => string,
  nodeTooltip: any,
  link: any,
  selectedNodes: Set<any>,
  currentZoomScale: number,
  width: number,
  height: number,
  _onNodeDelete: (nodeId: string) => void,
  _onNodeRestore: (nodeId: string) => void,
  forceUpdate: () => void
) {
  const searchTermLower = searchTerm.toLowerCase();
  const nodeGroups = container.selectAll(".node");

  nodeGroups
    .classed("search-highlight", (d: any) => searchTerm !== "" && d.id.toLowerCase().includes(searchTermLower))
    .classed("selected", (d: any) => selectedNodes.has(d));

  nodeGroups
    .select("circle")
    .attr("r", function (d: any) {
      return getRadius(d, minBalance, options.sizeNodeBy, nodeSizeScale);
    })
    .style("fill", function (d: any) {
      if (selectedNodes.has(d)) {
        return "orange";
      }
      return getNodeColor(d, searchTerm, options.colorNodeBy, colorScale);
    })
    .style("opacity", function (d: any): any {
      if (searchTerm !== "") {
        const connectedToSearch = (d.connected_nodes || []).some((id: string) => id.toLowerCase().includes(searchTermLower)) ? 1 : 0;
        const idIncludesSearch = d.id.toLowerCase().includes(searchTermLower) ? 1 : 0;
        return idIncludesSearch || connectedToSearch ? 1 : 0.9;
      }
      return 1;
    })
    .on("mousemove", function (event: MouseEvent) {
      updateTooltipPosition(nodeTooltip, event);
    })
    .on("mouseover", function (event: MouseEvent, d: any) {
      if (isDragging) return;
      handleMouseover(event, d, nodeTooltip, selectedNodes, minBalance, options.sizeNodeBy, nodeSizeScale, link, nodeGroups);
      nodeTooltip.style("visibility", "visible");
    })
    .on("mouseout", function (event: MouseEvent, d: any) {
      if (isDragging) return;

      if (!selectedNodes.has(d)) {
        select(this).style("fill", getNodeColor(d, searchTerm, options.colorNodeBy, colorScale));
        select(this).attr("r", getRadius(d, minBalance, options.sizeNodeBy, nodeSizeScale));
      }

      if (!selectedNodes.has(d)) {
        hideTooltip(nodeTooltip);
        // Restore link colours unless they touch a selected node.
        link.style("stroke", (l: any) => {
          return Array.from(selectedNodes).some((selectedNode: any) => l.source === selectedNode || l.target === selectedNode)
            ? "orange"
            : getLinkColor(l, searchTerm, options.colorNodeBy, colorScale);
        });
        const connectedIds = d.connected_nodes || [];
        const selectedConnectedIds = Array.from(selectedNodes).flatMap((selectedNode: any) => selectedNode.connected_nodes || []);

        connectedIds
          .filter((id: string) => !selectedConnectedIds.includes(id))
          .forEach((id: string) => {
            nodeGroups
              .selectAll("circle")
              .filter((dd: any) => dd.id.toLowerCase().includes(id.toLowerCase()))
              .style("fill", function (dd: any) {
                return selectedNodes.has(dd) ? "orange" : getNodeColor(dd, searchTerm, options.colorNodeBy, colorScale);
              });
          });
      }
    })
    .on("click", function (event: MouseEvent, d: any) {
      event.stopPropagation();
      selectedNodes.clear();
      startDragging();
      updateTooltip(nodeTooltip, d, true, event);

      if (selectedNodes.size > 0 && !selectedNodes.has(d)) {
        nodeGroups.selectAll("circle").style("fill", (dd: any) => getNodeColor(dd, searchTerm, options.colorNodeBy, colorScale));
        link.style("stroke", (l: any) => getLinkColor(l, searchTerm, options.colorNodeBy, colorScale));
        hideTooltip(nodeTooltip);
      }

      if (selectedNodes.has(d)) {
        selectedNodes.delete(d);
        hideTooltip(nodeTooltip);
      } else {
        selectedNodes.add(d);
        select(this).style("fill", "orange");
        select(this).attr("r", getRadius(d, minBalance, options.sizeNodeBy, nodeSizeScale) * 1.5);
        link.style("stroke", (l: any) => (l.source === d || l.target === d ? "orange" : "var(--graph-text-color)"));
        const connectedIds = d.connected_nodes || [];
        connectedIds.forEach((id: string) => {
          nodeGroups
            .selectAll("circle")
            .filter((dd: any) => dd.id.toLowerCase().includes(id.toLowerCase()))
            .style("fill", "orange");
        });

        if (tooltipCache[d.id]) {
          nodeTooltip.html(tooltipCache[d.id].data);
        } else {
          const tooltipHtml = generateNodeTooltipHtml(d);
          tooltipCache[d.id] = { data: tooltipHtml, timestamp: Date.now() };
          nodeTooltip.html(tooltipHtml);
        }

        nodeTooltip.style("visibility", "visible");
      }
      stopDragging();
      forceUpdate();
    });

  nodeGroups
    .select("text")
    .attr("x", 0)
    .attr("y", 0)
    .attr("text-anchor", "middle")
    .text((d: any) => {
      if (options.deletedNodes[d.id]) return "";
      // Truncate the label to whatever fits inside the circle at the current
      // zoom; addresses are abbreviated as `XXXXX...XXXX` once they don't fit.
      const nodeRadius = getRadius(d, minBalance, options.sizeNodeBy, nodeSizeScale) * currentZoomScale;
      const baseAvgCharWidth = 14;
      const avgCharWidth = baseAvgCharWidth / currentZoomScale;
      const maxCharsFit = Math.floor((nodeRadius * 2) / avgCharWidth);

      if (d.id.length <= maxCharsFit) {
        return d.id;
      } else if (maxCharsFit > 9) {
        return `${d.id.substring(0, 5)}...${d.id.substring(d.id.length - 4)}`;
      } else {
        return maxCharsFit > 5 ? `${d.id.substring(0, maxCharsFit)}` : "";
      }
    })
    .each(function (d: any) {
      const textLength = (this as SVGTextElement).getComputedTextLength();
      const nodeRadius = getRadius(d, minBalance, options.sizeNodeBy, nodeSizeScale) * currentZoomScale;
      select(this).style("visibility", textLength > nodeRadius * 1.5 ? "hidden" : "visible");
    })
    .style("font-size", () => {
      const baseFontSize = 14;
      return `${baseFontSize / currentZoomScale}px`;
    })
    .style("pointer-events", "none");

  nodeGroups.attr("transform", function (d: any) {
    if (options.initialNodePositions[d.id]) {
      const absolutePosition = relativeToAbsolutePosition(options.initialNodePositions[d.id], width, height);
      d.x = absolutePosition.x;
      d.y = absolutePosition.y;
    } else if (d.x === undefined || d.y === undefined) {
      d.x = Math.random() * width;
      d.y = Math.random() * height;
    }
    return `translate(${d.x}, ${d.y})`;
  });

  nodeGroups.filter((d: any) => options.deletedNodes[d.id]).remove();
}

export function startDragging() {
  isDragging = true;
}

export function stopDragging() {
  isDragging = false;
}
