import { merge } from "lodash";
import { GraphOptions } from "./types";

export const DEFAULT_OPTIONS: GraphOptions = {
  repulsion: -500,
  colorInterpolatorName: "interpolateWarm",
  sizeNodeBy: "linkCount",
  minNodeSize: 5,
  maxNodeSize: 50,
  minLinkSize: 1,
  maxLinkSize: 25,
  colorNodeBy: "balance",
  initialNodePositions: {},
  saveNodePositions: false,
  deletedNodes: {},
  allowNodeDeletion: false,
};

export default function getOptions(options: Partial<GraphOptions>): GraphOptions {
  return merge({}, DEFAULT_OPTIONS, options);
}
