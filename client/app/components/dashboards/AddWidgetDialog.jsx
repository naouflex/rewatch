import { map, includes, groupBy, first, find } from "lodash";
import React, { useState, useMemo, useCallback } from "react";
import PropTypes from "prop-types";
import Select from "antd/lib/select";
import { wrap as wrapDialog, DialogPropType } from "@/components/DialogWrapper";
import { ModalShell, ModalSection } from "@/components/ModalShell";
import { MappingType, ParameterMappingListInput } from "@/components/ParameterMappingInput";
import QuerySelector from "@/components/QuerySelector";
import notification from "@/services/notification";
import { Query } from "@/services/query";
import { useUniqueId } from "@/lib/hooks/useUniqueId";
import { getModalFormProps } from "@/styles/formStyle";
import Form from "antd/lib/form";

function VisualizationSelect({ query, visualization, onChange }) {
  const visualizationGroups = useMemo(() => {
    return query ? groupBy(query.visualizations, "type") : {};
  }, [query]);

  const vizSelectId = useUniqueId("visualization-select");

  const handleChange = useCallback(
    visualizationId => {
      const selectedVisualization = query ? find(query.visualizations, { id: visualizationId }) : null;
      onChange(selectedVisualization || null);
    },
    [query, onChange]
  );

  if (!query) {
    return null;
  }

  return (
    <Form.Item label="Visualization" htmlFor={vizSelectId}>
      <Select
        id={vizSelectId}
        className="w-100"
        value={visualization ? visualization.id : undefined}
        onChange={handleChange}
        size="large">
        {map(visualizationGroups, (visualizations, groupKey) => (
          <Select.OptGroup key={groupKey} label={groupKey}>
            {map(visualizations, viz => (
              <Select.Option key={`${viz.id}`} value={viz.id}>
                {viz.name}
              </Select.Option>
            ))}
          </Select.OptGroup>
        ))}
      </Select>
    </Form.Item>
  );
}

VisualizationSelect.propTypes = {
  query: PropTypes.object,
  visualization: PropTypes.object,
  onChange: PropTypes.func,
};

VisualizationSelect.defaultProps = {
  query: null,
  visualization: null,
  onChange: () => {},
};

function AddWidgetDialog({ dialog, dashboard }) {
  const [selectedQuery, setSelectedQuery] = useState(null);
  const [selectedVisualization, setSelectedVisualization] = useState(null);
  const [parameterMappings, setParameterMappings] = useState([]);

  const selectQuery = useCallback(
    queryId => {
      setSelectedQuery(null);
      setSelectedVisualization(null);
      setParameterMappings([]);

      if (queryId) {
        Query.get({ id: queryId }).then(query => {
          if (query) {
            const existingParamNames = map(dashboard.getParametersDefs(), param => param.name);
            setSelectedQuery(query);
            setParameterMappings(
              map(query.getParametersDefs(), param => ({
                name: param.name,
                type: includes(existingParamNames, param.name)
                  ? MappingType.DashboardMapToExisting
                  : MappingType.DashboardAddNew,
                mapTo: param.name,
                value: param.normalizedValue,
                title: "",
                param,
              }))
            );
            if (query.visualizations.length > 0) {
              setSelectedVisualization(first(query.visualizations));
            }
          }
        });
      }
    },
    [dashboard]
  );

  const saveWidget = useCallback(() => {
    dialog.close({ visualization: selectedVisualization, parameterMappings }).catch(() => {
      notification.error("Widget could not be added");
    });
  }, [dialog, selectedVisualization, parameterMappings]);

  const existingParams = dashboard.getParametersDefs();
  const parameterMappingsId = useUniqueId("parameter-mappings");

  return (
    <ModalShell
      dialog={dialog}
      title="Add Widget"
      description="Pick a query, visualization, and map parameters for this dashboard."
      size="lg"
      onOk={saveWidget}
      okText="Add to Dashboard"
      okButtonProps={{
        ...dialog.props.okButtonProps,
        disabled: !selectedQuery || dialog.props.okButtonProps.disabled,
      }}
      wrapProps={{ "data-test": "AddWidgetDialog" }}>
      <Form {...getModalFormProps()} data-test="AddWidgetDialog">
        <ModalSection title="Query">
          <QuerySelector onChange={query => selectQuery(query ? query.id : null)} />
        </ModalSection>
        {selectedQuery && (
          <ModalSection title="Visualization">
            <VisualizationSelect
              query={selectedQuery}
              visualization={selectedVisualization}
              onChange={setSelectedVisualization}
            />
          </ModalSection>
        )}
        {parameterMappings.length > 0 && (
          <ModalSection title="Parameters">
            <ParameterMappingListInput
              id={parameterMappingsId}
              mappings={parameterMappings}
              existingParams={existingParams}
              onChange={setParameterMappings}
            />
          </ModalSection>
        )}
      </Form>
    </ModalShell>
  );
}

AddWidgetDialog.propTypes = {
  dialog: DialogPropType.isRequired,
  dashboard: PropTypes.object.isRequired,
};

export default wrapDialog(AddWidgetDialog);
