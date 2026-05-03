export interface GraphOptions {
  repulsion: number;
  minNodeSize: number;
  maxNodeSize: number;
  minLinkSize: number;
  maxLinkSize: number;
  colorNodeBy: string;
  sizeNodeBy: string;
  colorInterpolatorName: string;
  saveNodePositions: boolean;
  initialNodePositions: NodePositions;
  deletedNodes: DeletedNodes;
  allowNodeDeletion: boolean;
}

export interface GraphDataType {
  rows: any[];
  columns: any[];
}

export interface NodeType {
  id: string;
  x?: number;
  y?: number;
  fx?: number;
  fy?: number;
  balance?: number;
  total_received?: number;
  total_sent?: number;
  link_count?: number;
  groups: string[];
  grouping_id?: string;
  connected_nodes?: string[];
  [key: string]: any;
}

export interface LinkType {
  source: string | NodeType;
  target: string | NodeType;
  value: number;
  id: string;
}

export interface NodePositions {
  // Positions are stored relative to the rendering area (0..1) so they survive
  // resizes. Conversion to absolute pixel coordinates happens in the renderer.
  [key: string]: { x: number; y: number };
}

export interface ExtendedGraphDataType extends GraphDataType {
  nodes: NodeType[];
  links: LinkType[];
}

export interface DeletedNodes {
  [key: string]: boolean;
}
