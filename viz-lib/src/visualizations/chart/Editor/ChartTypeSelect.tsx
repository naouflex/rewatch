import { filter, includes, map } from "lodash";
import React, { useMemo } from "react";
import { Select } from "@/components/visualizations/editor";
import { CHART_TYPES } from "../chartTypes";
import { visualizationsSettings } from "@/visualizations/visualizationsSettings";

const allChartTypes = CHART_TYPES.map(({ type, name, icon }) => ({ type, name, icon }));

type OwnProps = {
  hiddenChartTypes?: any[]; // TODO: PropTypes.oneOf(map(allChartTypes, "type"))
};

const chartTypeSelectDefaultProps = {
  hiddenChartTypes: [],
};

type Props = OwnProps & typeof chartTypeSelectDefaultProps;

export default function ChartTypeSelect({ hiddenChartTypes, ...props }: Props) {
  const chartTypes = useMemo(() => {
    const result = [...allChartTypes];

    if (visualizationsSettings.allowCustomJSVisualizations) {
      result.push({ type: "custom", name: "Custom", icon: "code" });
    }

    if (hiddenChartTypes.length > 0) {
      return filter(result, ({ type }) => !includes(hiddenChartTypes, type));
    }

    return result;
  }, []);

  return (
    <Select {...props}>
      {map(chartTypes, ({ type, name, icon }) => (
        // @ts-expect-error ts-migrate(2339) FIXME: Property 'Option' does not exist on type '({ class... Remove this comment to see the full error message
        <Select.Option key={type} value={type} data-test={`Chart.ChartType.${type}`}>
          <i className={`fa fa-${icon}`} style={{ marginRight: 5 }} />
          {name}
          {/* @ts-expect-error ts-migrate(2339) FIXME: Property 'Option' does not exist on type '({ class... Remove this comment to see the full error message */}
        </Select.Option>
      ))}
    </Select>
  );
}

ChartTypeSelect.defaultProps = chartTypeSelectDefaultProps;
