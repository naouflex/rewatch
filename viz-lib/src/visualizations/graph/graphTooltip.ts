import { select } from "d3-selection";
import { formatNumber } from "./graphUtils";

// In-memory tooltip cache (kept for parity with the original implementation,
// even though we no longer fetch async data). Some node-id collisions across
// updates would otherwise rebuild the same HTML on every hover.
interface CacheItem {
  data: string;
  timestamp: number;
}

let activeTooltip: any = null;
const tooltipCache: { [key: string]: CacheItem } = {};
const CACHE_TIMEOUT = 5 * 60 * 1000; // 5 minutes

export function createTooltip(id: string): any {
  // The tooltip is appended to <body> rather than the chart container so it
  // can escape `overflow: hidden` and SVG clipping. Pointer events are off by
  // default; we re-enable them when the tooltip becomes "sticky" (clicked).
  const tooltip = select("body")
    .append("div")
    .attr("id", id)
    .attr("class", "graph-tooltip")
    .style("opacity", 0)
    .style("position", "absolute")
    .style("pointer-events", "none")
    .style("background", "rgba(255, 255, 255, 0.95)")
    .style("border", "1px solid #ddd")
    .style("border-radius", "5px")
    .style("padding", "10px")
    .style("max-width", "300px")
    .style("font-size", "12px")
    .style("line-height", "1.4")
    .style("transition", "opacity 0.3s");

  tooltip
    .append("button")
    .attr("class", "close-button")
    .style("position", "absolute")
    .style("top", "5px")
    .style("right", "5px")
    .style("background", "none")
    .style("border", "none")
    .style("font-size", "16px")
    .style("cursor", "pointer")
    .html("&times;")
    .on("click", () => hideTooltip(tooltip));

  return tooltip;
}

export function generateNodeTooltipHtml(d: any): string {
  return `
    <strong>Node:</strong> ${escapeHtml(d.id)}<br>
    <strong>Balance:</strong> ${formatNumber(d.balance)}<br>
    <strong>Total Sent:</strong> ${formatNumber(d.total_sent)}<br>
    <strong>Total Received:</strong> ${formatNumber(d.total_received)}<br>
    <strong>Connections:</strong> ${d.link_count || "N/A"}<br>
    <strong>Groups:</strong> ${d.grouping_id || "N/A"}<br>
  `;
}

export function generateLinkTooltipHtml(d: any): string {
  const value = d.value || 0;
  const sourceId = (d.source && d.source.id) || "Unknown";
  const targetId = (d.target && d.target.id) || "Unknown";
  const linkId = d.id || "";

  return `
    <strong>From:</strong> ${escapeHtml(sourceId)}<br>
    <strong>To:</strong> ${escapeHtml(targetId)}<br>
    <strong>Value:</strong> ${formatNumber(value)}
    ${linkId ? `<br><strong>Id:</strong> ${escapeHtml(linkId)}` : ""}
  `;
}

// Just move an already-shown tooltip to follow the cursor.
export function updateTooltipPosition(tooltip: any, event?: MouseEvent) {
  if (!tooltip) return;

  const tooltipNode = tooltip.node();
  if (!tooltipNode) return;

  const tooltipRect = tooltipNode.getBoundingClientRect();
  const margin = 10;

  let left = 0;
  let top = 0;

  if (event) {
    left = event.pageX + margin;
    top = event.pageY + margin;
  } else {
    left = window.innerWidth / 2 - tooltipRect.width / 2;
    top = window.innerHeight / 2 - tooltipRect.height / 2;
  }

  tooltip.style("left", `${left}px`).style("top", `${top}px`);
}

export function updateTooltip(tooltip: any, d: any, isSticky: boolean, event?: MouseEvent) {
  if (!tooltip || !d) return;

  const tooltipNode = tooltip.node();
  if (!tooltipNode) return;

  const tooltipRect = tooltipNode.getBoundingClientRect();
  const margin = 10;

  let left = 0;
  let top = 0;

  if (event) {
    left = event.pageX + margin;
    top = event.pageY + margin;

    // Flip side if the tooltip would overflow the viewport.
    if (left + tooltipRect.width > window.innerWidth) {
      left = event.pageX - tooltipRect.width - margin;
    }
    if (top + tooltipRect.height > window.innerHeight) {
      top = event.pageY - tooltipRect.height - margin;
    }
  } else {
    left = window.innerWidth / 2 - tooltipRect.width / 2;
    top = window.innerHeight / 2 - tooltipRect.height / 2;
  }

  tooltip
    .style("left", `${left}px`)
    .style("top", `${top}px`)
    .style("opacity", 1)
    .style("pointer-events", isSticky ? "auto" : "none");

  if (isSticky) {
    tooltip.classed("sticky", true);
    activeTooltip = tooltip;
    tooltip.select(".close-button").style("display", "block");
  } else {
    tooltip.classed("sticky", false);
    tooltip.select(".close-button").style("display", "none");
  }

  // The link case (`d.source` set) generates richer HTML; the node case is
  // handled the same way.
  if (d.source) {
    tooltip.html(generateLinkTooltipHtml(d));
  } else {
    tooltip.html(generateNodeTooltipHtml(d));
  }
}

export function hideTooltip(tooltip: any) {
  if (!tooltip) return;
  tooltip.style("opacity", 0).style("pointer-events", "none");
  if (activeTooltip === tooltip) {
    activeTooltip = null;
  }
  tooltip.select(".close-button").style("display", "none");
}

export function initializeTooltipListeners() {
  document.addEventListener("click", event => {
    if (activeTooltip && !activeTooltip.node().contains(event.target as any)) {
      hideTooltip(activeTooltip);
    }
  });
}

function escapeHtml(value: string): string {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export { tooltipCache, CACHE_TIMEOUT };
