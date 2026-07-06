import React from "react";
import { RendererPropTypes } from "@/visualizations/prop-types";
import NivoRenderer from "./NivoRenderer";

export default function Renderer(props: any) {
  return <NivoRenderer {...props} />;
}

Renderer.propTypes = RendererPropTypes;
