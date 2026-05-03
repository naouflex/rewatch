import React from "react";
import { CheckboxChangeEvent } from "antd/lib/checkbox";

import { Section, InputNumber, Checkbox, Select as BaseSelect } from "@/components/visualizations/editor";
import { EditorPropTypes } from "@/visualizations/prop-types";
import { GraphOptions, NodePositions } from "./types";

const Select = BaseSelect as typeof BaseSelect & {
  Option: React.ComponentType<{ value: string; children: React.ReactNode }>;
};

type EditorProps = {
  options: GraphOptions & {
    initialNodePositions: NodePositions;
  };
  onOptionsChange: (options: any) => void;
};

export default function Editor({ options, onOptionsChange }: EditorProps) {
  const handleOptionChange = (key: keyof EditorProps["options"], value: any) => {
    // Toggling these flags off should also wipe whatever state the feature
    // accumulated, otherwise the user is left with stale node positions /
    // deletions that they can't see in the UI.
    if (key === "saveNodePositions" && !value) {
      onOptionsChange({ ...options, [key]: value, initialNodePositions: {} });
    } else if (key === "allowNodeDeletion") {
      onOptionsChange({ ...options, [key]: value, deletedNodes: {} });
    } else {
      onOptionsChange({ ...options, [key]: value });
    }
  };

  return (
    <React.Fragment>
      {/* @ts-expect-error ts-migrate(2745) FIXME: Rest types may only be created from object types. */}
      <Section>
        <InputNumber
          label="Repulsion Force"
          data-test="Graph.Repulsion"
          value={options.repulsion}
          onChange={(value: number) => handleOptionChange("repulsion", value)}
        />
      </Section>
      {/* @ts-expect-error ts-migrate(2745) FIXME: Rest types may only be created from object types. */}
      <Section>
        <Select
          label="Color Scheme"
          data-test="Graph.ColorScheme"
          value={options.colorInterpolatorName}
          onChange={(value: string) => handleOptionChange("colorInterpolatorName", value)}>
          {[
            "interpolateWarm",
            "interpolateCool",
            "interpolateBlues",
            "interpolateGreens",
            "interpolateGreys",
            "interpolateOranges",
            "interpolatePurples",
            "interpolateReds",
            "interpolateViridis",
            "interpolateInferno",
            "interpolateMagma",
            "interpolatePlasma",
            "interpolateCividis",
            "interpolateTurbo",
          ].map(value => (
            <Select.Option key={value} value={value}>
              {value.replace("interpolate", "")}
            </Select.Option>
          ))}
        </Select>
      </Section>
      {/* @ts-expect-error ts-migrate(2745) FIXME: Rest types may only be created from object types. */}
      <Section>
        <Select
          label="Color Nodes by"
          data-test="Graph.ColorNodesBy"
          value={options.colorNodeBy}
          onChange={(value: string) => handleOptionChange("colorNodeBy", value)}>
          {(
            [
              ["balance", "Balance"],
              ["totalSent", "Total Sent"],
              ["totalReceived", "Total Received"],
              ["linkCount", "Number of Links"],
              ["group", "Group"],
            ] as [string, string][]
          ).map(([value, label]) => (
            <Select.Option key={value} value={value}>
              {label}
            </Select.Option>
          ))}
        </Select>
      </Section>
      {/* @ts-expect-error ts-migrate(2745) FIXME: Rest types may only be created from object types. */}
      <Section>
        <Select
          label="Size Nodes by"
          data-test="Graph.SizeNodesBy"
          value={options.sizeNodeBy}
          onChange={(value: string) => handleOptionChange("sizeNodeBy", value)}>
          {(
            [
              ["linkCount", "Number of Links"],
              ["balance", "Balance"],
              ["totalSent", "Total Sent"],
              ["totalReceived", "Total Received"],
            ] as [string, string][]
          ).map(([value, label]) => (
            <Select.Option key={value} value={value}>
              {label}
            </Select.Option>
          ))}
        </Select>
      </Section>
      {/* @ts-expect-error ts-migrate(2745) FIXME: Rest types may only be created from object types. */}
      <Section>
        <InputNumber
          label="Min Node Size"
          data-test="Graph.MinNodeSize"
          value={options.minNodeSize}
          onChange={(value: number) => handleOptionChange("minNodeSize", value)}
        />
      </Section>
      {/* @ts-expect-error ts-migrate(2745) FIXME: Rest types may only be created from object types. */}
      <Section>
        <InputNumber
          label="Max Node Size"
          data-test="Graph.MaxNodeSize"
          value={options.maxNodeSize}
          onChange={(value: number) => handleOptionChange("maxNodeSize", value)}
        />
      </Section>
      {/* @ts-expect-error ts-migrate(2745) FIXME: Rest types may only be created from object types. */}
      <Section>
        <InputNumber
          label="Min Link Size"
          data-test="Graph.MinLinkSize"
          value={options.minLinkSize}
          onChange={(value: number) => handleOptionChange("minLinkSize", value)}
        />
      </Section>
      {/* @ts-expect-error ts-migrate(2745) FIXME: Rest types may only be created from object types. */}
      <Section>
        <InputNumber
          label="Max Link Size"
          data-test="Graph.MaxLinkSize"
          value={options.maxLinkSize}
          onChange={(value: number) => handleOptionChange("maxLinkSize", value)}
        />
      </Section>
      {/* @ts-expect-error ts-migrate(2745) FIXME: Rest types may only be created from object types. */}
      <Section>
        <Checkbox
          data-test="Graph.SaveNodePositions"
          checked={options.saveNodePositions}
          onChange={(e: CheckboxChangeEvent) => handleOptionChange("saveNodePositions", e.target.checked)}>
          Save Node Positions
        </Checkbox>
      </Section>
      {/* @ts-expect-error ts-migrate(2745) FIXME: Rest types may only be created from object types. */}
      <Section>
        <Checkbox
          data-test="Graph.AllowNodeDeletion"
          checked={options.allowNodeDeletion}
          onChange={(e: CheckboxChangeEvent) => handleOptionChange("allowNodeDeletion", e.target.checked)}>
          Allow Node Deletion
        </Checkbox>
      </Section>

      <p>This visualization expects the query result to have rows in the following format:</p>
      <ul>
        <li>
          <strong>from</strong> &mdash; source node (string)
        </li>
        <li>
          <strong>to</strong> &mdash; target node (string)
        </li>
        <li>
          <strong>value</strong> &mdash; strength of the link (number)
        </li>
        <li>
          <strong>id</strong> (optional) &mdash; identifier for the link (string)
        </li>
        <li>
          <strong>group</strong> (optional) &mdash; grouping label for the link (string)
        </li>
      </ul>
    </React.Fragment>
  );
}

Editor.propTypes = EditorPropTypes;
