import getOptions from "./getOptions";
import Renderer from "./Renderer";
import Editor from "./Editor";
import { GraphOptions, GraphDataType, NodeType, LinkType, ExtendedGraphDataType } from "./types";

export { GraphOptions, GraphDataType, NodeType, LinkType, ExtendedGraphDataType };

export default {
  type: "GRAPH",
  name: "Graph",
  getOptions,
  Renderer,
  Editor,

  defaultRows: 7,
};
