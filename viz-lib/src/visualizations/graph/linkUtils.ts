import { Selection } from "d3-selection";
import { select } from "d3-selection";
import { LinkType, GraphOptions } from "./types";
import { scaleLinear } from "d3-scale";
import { min, max } from "d3-array";
import { generateLinkTooltipHtml, updateTooltip, hideTooltip, tooltipCache, CACHE_TIMEOUT } from "./graphTooltip";
import { getNodeColor } from "./nodeUtils";

// Look up cached HTML before re-generating; the cache survives across hovers
// so repeatedly mousing over the same link is cheap.
function fetchLinkTooltipData(d: any, linkTooltip: any) {
  const linkId = d.id;
  const cachedData = tooltipCache[linkId];
  const now = Date.now();

  if (cachedData && now - cachedData.timestamp < CACHE_TIMEOUT) {
    linkTooltip.html(cachedData.data);
  } else {
    const tooltipHtml = generateLinkTooltipHtml(d);
    tooltipCache[linkId] = { data: tooltipHtml, timestamp: now };
    linkTooltip.html(tooltipHtml);
  }
}

export function getLinkThicknessScale(links: LinkType[], minLinkSize: number, maxLinkSize: number) {
  return scaleLinear<number>()
    .domain([min(links, (d: any) => d.value)!, max(links, (d: any) => d.value)!])
    .range([minLinkSize, maxLinkSize]);
}

export function getLinkOpacityScale(links: LinkType[]) {
  // Heavier links are slightly less transparent so the eye gravitates to them.
  return scaleLinear()
    .domain([min(links, (d: any) => d.value)!, max(links, (d: any) => d.value)!])
    .range([0.5, 0.1]);
}

export const getLinkColor = (l: any, searchTerm: string, colorNodeBy: any, colorScale: any): string => {
  if (!searchTerm) {
    return getNodeColor(l.source, searchTerm, colorNodeBy, colorScale);
  }
  return l.source.id.toLowerCase().includes(searchTerm.toLowerCase()) ? "orange" : "var(--graph-text-color)";
};

export function createLinks(container: Selection<SVGGElement, unknown, null, undefined>, links: any[]) {
  const link = container
    .append("g")
    .attr("class", "links")
    .selectAll<SVGLineElement, unknown>(".link")
    .data(links)
    .enter()
    .append<SVGLineElement>("line");
  return link;
}

export function updateLinks(
  container: Selection<SVGGElement, unknown, null, undefined>,
  options: GraphOptions,
  linkThicknessScale: (value: number) => number,
  opacityScale: (value: number) => number,
  searchTerm: string,
  colorScale: (d: any) => string,
  linkTooltip: any,
  selectedNodes: Set<any>,
  selectedLinks: Set<any>,
  forceUpdate: () => void
) {
  const linksUpdate = container.selectAll<SVGLineElement, unknown>("line");

  linksUpdate
    .style("stroke-width", (d: any) => linkThicknessScale(d.value))
    .style("stroke", (d: any) => getLinkColor(d, searchTerm, options.colorNodeBy, colorScale))
    .style("opacity", (d: any) => opacityScale(d.value))
    .sort((a: any, b: any) => b.value - a.value)
    .classed("selected", (d: any) => selectedLinks.has(d))
    .classed("connected", (d: any) => {
      if (selectedNodes.size === 0) return false;
      return Array.from(selectedNodes).some((selectedNode: any) => d.source === selectedNode || d.target === selectedNode);
    })
    .classed("search-highlight", (d: any) => {
      if (!searchTerm) return false;
      return (
        d.source.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        d.target.id.toLowerCase().includes(searchTerm.toLowerCase())
      );
    })
    .on("mouseover", function (event: MouseEvent, d: any) {
      if (selectedLinks.has(d)) {
        return;
      }
      select(this).style("stroke", "orange");
      fetchLinkTooltipData(d, linkTooltip);
      updateTooltip(linkTooltip, d, false, event);
    })
    .on("mousemove", function (event: MouseEvent, d: any) {
      updateTooltip(linkTooltip, d, false, event);
    })
    .on("mouseout", function (this: SVGLineElement, event: MouseEvent, d: any) {
      select(this).style("stroke", () => getLinkColor(d, searchTerm, options.colorNodeBy, colorScale));
      if (!selectedLinks.has(d)) {
        hideTooltip(linkTooltip);
      }
    })
    .on("click", function (this: SVGLineElement, event: MouseEvent, d: any) {
      event.stopPropagation();
      if (selectedLinks.has(d)) {
        selectedLinks.delete(d);
        select(this).style("stroke", () => getLinkColor(d, searchTerm, options.colorNodeBy, colorScale));
        hideTooltip(linkTooltip);
      } else {
        selectedLinks.clear();
        selectedLinks.add(d);
        select(this).style("stroke", "orange");
        fetchLinkTooltipData(d, linkTooltip);
        updateTooltip(linkTooltip, d, true, event);
      }

      forceUpdate();
    });

  // A node was just removed; drop any link that touched it before redrawing.
  linksUpdate
    .filter((d: any) => options.deletedNodes[d.source.id] || options.deletedNodes[d.target.id])
    .remove();
}
