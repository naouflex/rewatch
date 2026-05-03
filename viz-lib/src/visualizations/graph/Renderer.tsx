import React, { useState, useEffect, useCallback, useRef } from "react";
import * as d3zoom from "d3-zoom";
import { select } from "d3-selection";
import { UndoOutlined } from "@ant-design/icons";

import { GraphDataType, GraphOptions, NodePositions, ExtendedGraphDataType } from "./types";
import initGraphFunc from "./graphInit";
import updateGraphFunc from "./graphUpdate";
import { initializeTooltipListeners, hideTooltip } from "./graphTooltip";
import "./renderer.less";

type RendererProps = {
  data: GraphDataType;
  options: GraphOptions;
  onOptionsChange: (newOptions: Partial<GraphOptions>) => void;
};

export default function Renderer({ data, options, onOptionsChange }: RendererProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [currentZoomLevel, setCurrentZoomLevel] = useState(1);
  const [graphData, setGraphData] = useState<ExtendedGraphDataType>(data as ExtendedGraphDataType);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; nodeId: string } | null>(null);
  const [linkContextMenu, setLinkContextMenu] = useState<{
    x: number;
    y: number;
    linkId: string;
    source: { id: string };
    target: { id: string };
  } | null>(null);
  const [, setForceUpdate] = useState({});

  const containerRef = useRef<HTMLDivElement>(null);
  const initNeededRef = useRef(true);
  const graphInitializedRef = useRef(false);
  const zoomRef = useRef<d3zoom.ZoomBehavior<Element, unknown>>();

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  const closeContextMenu = useCallback(() => {
    setContextMenu(null);
  }, []);

  const closeLinkContextMenu = useCallback(() => {
    setLinkContextMenu(null);
  }, []);

  const handleContextMenu = useCallback(
    (event: MouseEvent, nodeId: string) => {
      hideTooltip(select(containerRef.current).selectAll(".nodeTooltip"));
      hideTooltip(select(containerRef.current).selectAll(".linkTooltip"));
      event.preventDefault();
      event.stopPropagation();
      const rect = containerRef.current?.getBoundingClientRect();
      if (rect) {
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        closeLinkContextMenu();
        setContextMenu({ x, y, nodeId });
      }
    },
    [closeLinkContextMenu]
  );

  const handleLinkContextMenu = useCallback(
    (event: MouseEvent, linkId: string, source: { id: string }, target: { id: string }) => {
      event.preventDefault();
      event.stopPropagation();
      hideTooltip(select(containerRef.current).selectAll(".nodeTooltip"));
      hideTooltip(select(containerRef.current).selectAll(".linkTooltip"));
      const rect = containerRef.current?.getBoundingClientRect();
      if (rect) {
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        closeContextMenu();
        setLinkContextMenu({ x, y, linkId, source, target });
      }
    },
    [closeContextMenu]
  );

  const onNodePositionsChange = useCallback(
    (newPositions: NodePositions) => {
      if (options.saveNodePositions && onOptionsChange) {
        onOptionsChange({ ...options, initialNodePositions: newPositions });
      }
    },
    [options, onOptionsChange]
  );

  const onNodeDelete = useCallback(
    (nodeId: string) => {
      if (options.saveNodePositions && onOptionsChange) {
        onOptionsChange({ ...options, initialNodePositions: {} });
      }
      if (options.allowNodeDeletion && onOptionsChange) {
        const newDeletedNodes = { ...options.deletedNodes, [nodeId]: true };
        onOptionsChange({ ...options, deletedNodes: newDeletedNodes });
      }
      initNeededRef.current = true;
    },
    [options, onOptionsChange]
  );

  const onNodeRestore = useCallback(
    (nodeId: string) => {
      if (options.saveNodePositions && onOptionsChange) {
        onOptionsChange({ ...options, initialNodePositions: {} });
      }
      if (options.allowNodeDeletion && onOptionsChange) {
        const newDeletedNodes = { ...options.deletedNodes };
        delete newDeletedNodes[nodeId];
        onOptionsChange({ ...options, deletedNodes: newDeletedNodes });
      }
      initNeededRef.current = true;
    },
    [options, onOptionsChange]
  );

  const onNodePositionDelete = useCallback(
    (nodeId: string) => {
      if (options.saveNodePositions && onOptionsChange) {
        const newPositions = { ...options.initialNodePositions };
        delete newPositions[nodeId];
        onOptionsChange({ ...options, initialNodePositions: newPositions });
      }
      initNeededRef.current = true;
    },
    [options, onOptionsChange]
  );

  const initializeGraph = useCallback(() => {
    const element = containerRef.current;
    if (element && (!graphInitializedRef.current || initNeededRef.current)) {
      const renderGraph = initGraphFunc(graphData, options, onNodePositionsChange, onNodeDelete, onNodeRestore, () =>
        setGraphData({ ...graphData })
      );
      renderGraph(element);

      const svg = select(element).select("svg");
      const container: any = svg.select("g");

      // Wide scale extent so users can zoom way out on huge graphs.
      zoomRef.current = d3zoom
        .zoom()
        .scaleExtent([0.05, 20])
        .on("zoom", event => {
          container.attr("transform", event.transform);
          setCurrentZoomLevel(event.transform.k);
        });
      svg.call(zoomRef.current as any);

      graphInitializedRef.current = true;
      initNeededRef.current = false;
    }
  }, [options, graphData, onNodePositionsChange, onNodeDelete, onNodeRestore]);

  const updateGraph = useCallback(() => {
    const element = containerRef.current;
    if (element && graphInitializedRef.current && !initNeededRef.current) {
      updateGraphFunc(
        element,
        searchTerm,
        options,
        currentZoomLevel,
        onNodePositionsChange,
        onNodeDelete,
        onNodeRestore,
        handleContextMenu,
        handleLinkContextMenu,
        () => setForceUpdate({})
      );
    }
  }, [
    options,
    searchTerm,
    currentZoomLevel,
    onNodePositionsChange,
    onNodeDelete,
    onNodeRestore,
    handleContextMenu,
    handleLinkContextMenu,
  ]);

  useEffect(() => {
    initializeGraph();
    initializeTooltipListeners();
  }, [initializeGraph, data]);

  useEffect(() => {
    updateGraph();
  }, [updateGraph, options.deletedNodes, options.initialNodePositions, data]);

  useEffect(() => {
    // Click anywhere outside a node/link: hide tooltips and close any
    // open context menu.
    const handleClickOutside = () => {
      const nodeTooltip = select(containerRef.current).selectAll(".nodeTooltip");
      const linkTooltip = select(containerRef.current).selectAll(".linkTooltip");
      hideTooltip(nodeTooltip);
      hideTooltip(linkTooltip);

      if (contextMenu) {
        closeContextMenu();
      }
      if (linkContextMenu) {
        closeLinkContextMenu();
      }
    };

    document.addEventListener("click", handleClickOutside);
    return () => {
      document.removeEventListener("click", handleClickOutside);
    };
  }, [contextMenu, closeContextMenu, linkContextMenu, closeLinkContextMenu]);

  return (
    <div className="graph-visualization-container">
      <div className="graph-and-parameters-container">
        <div className="graph-parameter-box">
          <div>
            <strong>
              <em>Search:</em>
            </strong>
          </div>
          <div className="graph-search-container">
            <input
              type="text"
              value={searchTerm}
              onChange={handleSearchChange}
              placeholder="Search nodes or links..."
              className="graph-search"
            />
            <button onClick={() => setSearchTerm("")} className="graph-clear-button">
              X
            </button>
          </div>

          {options.allowNodeDeletion && Object.keys(options.deletedNodes).length > 0 && (
            <div className="deleted-nodes-section">
              <div>
                <strong>
                  <em>Deleted Nodes:</em>
                </strong>
              </div>
              <ul className="deleted-nodes-list">
                {Object.keys(options.deletedNodes).map(nodeId => (
                  <li key={nodeId}>
                    <span>{nodeId}</span>
                    <button onClick={() => onNodeRestore(nodeId)} className="restore-node-button">
                      <UndoOutlined />
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
        <div className="graph-visualization-container" ref={containerRef}></div>
      </div>
      {contextMenu && (
        <div
          className="context-menu"
          style={{
            position: "absolute",
            left: `${contextMenu.x}px`,
            top: `${contextMenu.y}px`,
            zIndex: 1000,
          }}>
          {options.saveNodePositions ? (
            <button
              onClick={() => {
                onNodePositionDelete(contextMenu.nodeId);
                closeContextMenu();
              }}>
              Reset Position
            </button>
          ) : null}
          {options.allowNodeDeletion ? (
            <button
              onClick={() => {
                onNodeDelete(contextMenu.nodeId);
                closeContextMenu();
              }}>
              Delete Node
            </button>
          ) : null}
        </div>
      )}
      {linkContextMenu && (
        <div
          className="context-menu"
          style={{
            position: "absolute",
            left: `${linkContextMenu.x}px`,
            top: `${linkContextMenu.y}px`,
            zIndex: 1000,
          }}>
          <button
            onClick={() => {
              navigator.clipboard?.writeText(linkContextMenu.linkId);
              closeLinkContextMenu();
            }}>
            Copy Link ID
          </button>
          <button
            onClick={() => {
              navigator.clipboard?.writeText(linkContextMenu.source.id);
              closeLinkContextMenu();
            }}>
            Copy Source ID
          </button>
          <button
            onClick={() => {
              navigator.clipboard?.writeText(linkContextMenu.target.id);
              closeLinkContextMenu();
            }}>
            Copy Target ID
          </button>
        </div>
      )}
    </div>
  );
}
