import { zoom } from "d3-zoom";
import { select } from "d3-selection";
import * as d3drag from "d3-drag";
import { forceLink, forceManyBody, forceCenter, forceSimulation, Simulation } from "d3-force";
import debounce from "lodash/debounce";

import { getColorInterpolator } from "./graphUtils";
import { getNodeColorScale, getNodeSizeScale, updateNodes, startDragging, stopDragging } from "./nodeUtils";
import { getLinkThicknessScale, getLinkOpacityScale, updateLinks } from "./linkUtils";
import { createTooltip, updateTooltip, hideTooltip } from "./graphTooltip";
import { NodePositions, NodeType, LinkType, GraphOptions } from "./types";

// `updateGraph` runs after `initGraph` has built the SVG; it re-applies styles
// based on the current options/searchTerm/zoom and rebinds drag/zoom handlers.
export default function updateGraph(
  element: HTMLDivElement,
  searchTerm: string,
  options: GraphOptions,
  currentZoomScale: number = 1,
  onNodePositionsChange: (newPositions: NodePositions) => void,
  onNodeDelete: (nodeId: string) => void,
  onNodeRestore: (nodeId: string) => void,
  handleContextMenu: (event: MouseEvent, nodeId: string) => void,
  handleLinkContextMenu: (event: MouseEvent, linkId: string, source: { id: string }, target: { id: string }) => void,
  forceUpdate: () => void
) {
  const svg = select(element).select("svg");
  const container: any = svg.select("g");
  const nodeGroups = container.selectAll(".node");
  const nodes = nodeGroups.selectAll("circle");
  const links = container.selectAll("line");
  const nodeTooltip = createTooltip("nodeTooltip");
  const linkTooltip = createTooltip("linkTooltip");
  const nodesData: NodeType[] = nodes.data();
  const linksData: LinkType[] = links.data();

  const activeNodesData = nodesData.filter(node => !options.deletedNodes[node.id]);
  const activeLinksData = linksData.filter(link => {
    const sourceId = typeof link.source === "object" ? link.source.id : link.source;
    const targetId = typeof link.target === "object" ? link.target.id : link.target;
    return !options.deletedNodes[sourceId] && !options.deletedNodes[targetId];
  });

  const colorInterpolator = getColorInterpolator(options.colorInterpolatorName);

  const nodeSizeScale = getNodeSizeScale(activeNodesData, options.sizeNodeBy, options.minNodeSize, options.maxNodeSize);
  const colorScale = getNodeColorScale(activeNodesData, options.colorNodeBy, colorInterpolator);
  const linkThicknessScale = getLinkThicknessScale(activeLinksData, options.minLinkSize, options.maxLinkSize);
  const opacityScale = getLinkOpacityScale(activeLinksData);

  const margin = { top: 10, right: 10, bottom: 10, left: 10 };
  const width = element.offsetWidth - margin.left - margin.right;
  const height = element.offsetHeight - margin.top - margin.bottom;

  const simulation: Simulation<NodeType, LinkType> = forceSimulation(activeNodesData)
    .force("link", forceLink<NodeType, LinkType>(activeLinksData).id((d: NodeType) => d.id))
    .force("charge", forceManyBody().strength(options.repulsion))
    .force("center", forceCenter(width / 2, height / 2));

  // Pin nodes that have a saved position; let the rest float free.
  activeNodesData.forEach((d: NodeType) => {
    if (options.initialNodePositions[d.id]) {
      d.fx = options.initialNodePositions[d.id].x * width;
      d.fy = options.initialNodePositions[d.id].y * height;
    } else {
      d.fx = undefined;
      d.fy = undefined;
    }
  });

  const selectedNodes = new Set<NodeType>();
  const selectedLinks = new Set<LinkType>();

  const debouncedOnNodePositionsChange = debounce((newPositions: NodePositions) => {
    if (options.saveNodePositions && typeof onNodePositionsChange === "function") {
      onNodePositionsChange(newPositions);
    }
  }, 10);

  const debouncedOnNodeDelete = debounce((nodeId: string) => {
    if (typeof onNodeDelete === "function") {
      onNodeDelete(nodeId);
    }
  }, 10);

  const debouncedOnNodeRestore = debounce((nodeId: string) => {
    if (typeof onNodeRestore === "function") {
      onNodeRestore(nodeId);
    }
  }, 10);

  function updateSelection() {
    updateLinks(
      container,
      options,
      linkThicknessScale,
      opacityScale,
      searchTerm,
      colorScale,
      linkTooltip,
      selectedNodes,
      selectedLinks,
      forceUpdate
    );
    updateNodes(
      container,
      options,
      nodeSizeScale,
      0,
      searchTerm,
      colorScale,
      nodeTooltip,
      links,
      selectedNodes,
      currentZoomScale,
      width,
      height,
      debouncedOnNodeDelete,
      debouncedOnNodeRestore,
      forceUpdate
    );
  }

  const zoomBehavior = zoom()
    .scaleExtent([0.1, 10])
    .on("zoom", (event: any) => {
      container.attr("transform", event.transform);
      currentZoomScale = event.transform.k;
      updateSelection();
    });

  svg.call(zoomBehavior as any);

  function highlightSearch() {
    if (searchTerm) {
      nodes.classed("search-highlight", (d: any) => d.id.toLowerCase().includes(searchTerm.toLowerCase()));
      links.classed("search-highlight", (d: any) =>
        d.source.id.toLowerCase().includes(searchTerm.toLowerCase()) || d.target.id.toLowerCase().includes(searchTerm.toLowerCase())
      );
    } else {
      nodes.classed("search-highlight", false);
      links.classed("search-highlight", false);
    }
  }

  highlightSearch();

  nodes.on("click", function (event: MouseEvent, d: any) {
    startDragging();
    hideTooltip(nodeTooltip);
    hideTooltip(linkTooltip);
    event.stopPropagation();
    selectedNodes.clear();
    selectedNodes.add(d);
    selectedLinks.clear();
    updateSelection();
    updateTooltip(nodeTooltip, d, true, event);
    stopDragging();
  });

  links.on("click", function (event: MouseEvent, d: any) {
    event.stopPropagation();
    hideTooltip(nodeTooltip);
    hideTooltip(linkTooltip);
    if (event.shiftKey) {
      // Shift-click adds to the selection so the user can compare a few
      // links side by side without losing the others.
      if (selectedLinks.has(d)) {
        selectedLinks.delete(d);
      } else {
        selectedLinks.add(d);
      }
    } else {
      selectedLinks.clear();
      selectedLinks.add(d);
    }
    selectedNodes.clear();
    updateSelection();
    updateTooltip(linkTooltip, d, true, event);
  });

  // Click on empty SVG canvas: deselect everything.
  svg.on("click", () => {
    selectedNodes.clear();
    selectedLinks.clear();
    updateSelection();
    hideTooltip(nodeTooltip);
    hideTooltip(linkTooltip);
  });

  const drag = d3drag
    .drag<SVGGElement, NodeType>()
    .on("start", function (event: d3drag.D3DragEvent<SVGGElement, NodeType, unknown>, d: any) {
      if (!event.active && simulation) simulation.alphaTarget(0.3).restart();
      startDragging();
      hideTooltip(nodeTooltip);
      hideTooltip(linkTooltip);
      d.fx = d.x;
      d.fy = d.y;
    })
    .on("drag", function (event: d3drag.D3DragEvent<SVGGElement, NodeType, unknown>, d: any) {
      if (!options.deletedNodes[d.id]) {
        d.fx = event.x;
        d.fy = event.y;
      }
    })
    .on("end", function (event: d3drag.D3DragEvent<SVGGElement, NodeType, unknown>, d: any) {
      if (!event.active && simulation) simulation.alphaTarget(0);
      stopDragging();
      if (!options.deletedNodes[d.id]) {
        d.fx = event.x;
        d.fy = event.y;

        // Persist the drop point as a relative position so it survives a
        // viewport resize.
        if (options.saveNodePositions) {
          const newPositions: NodePositions = {
            [d.id]: { x: d.fx! / width, y: d.fy! / height },
          };
          debouncedOnNodePositionsChange({ ...options.initialNodePositions, ...newPositions });
        }
      }
    });

  nodes.call(drag as any);

  updateSelection();

  simulation.on("tick", () => {
    links
      .attr("x1", (d: any) => (d.source as any).x || 0)
      .attr("y1", (d: any) => (d.source as any).y || 0)
      .attr("x2", (d: any) => (d.target as any).x || 0)
      .attr("y2", (d: any) => (d.target as any).y || 0)
      .on("contextmenu", function (event: MouseEvent, d: any) {
        event.preventDefault();
        event.stopPropagation();
        handleLinkContextMenu(event, d.id, d.source, d.target);
      });

    nodeGroups
      .attr("transform", (d: any) => `translate(${d.x || 0},${d.y || 0})`)
      .on("contextmenu", function (event: MouseEvent, d: any) {
        event.preventDefault();
        event.stopPropagation();
        handleContextMenu(event, d.id);
      });

    nodeGroups.selectAll("circle, text").on("contextmenu", function (event: MouseEvent, d: any) {
      event.preventDefault();
      event.stopPropagation();
      handleContextMenu(event, d.id);
    });
  });
}
