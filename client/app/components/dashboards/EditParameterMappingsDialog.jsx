import { isMatch, map, find, sortBy } from "lodash";
import React from "react";
import PropTypes from "prop-types";
import { wrap as wrapDialog, DialogPropType } from "@/components/DialogWrapper";
import { ModalShell, ModalSection } from "@/components/ModalShell";
import {
  MappingType,
  ParameterMappingListInput,
  parameterMappingsToEditableMappings,
  editableMappingsToParameterMappings,
  synchronizeWidgetTitles,
} from "@/components/ParameterMappingInput";
import notification from "@/services/notification";

export function getParamValuesSnapshot(mappings, dashboardParameters) {
  return map(
    sortBy(mappings, m => m.name),
    m => {
      let param;
      switch (m.type) {
        case MappingType.StaticValue:
          return [m.name, m.value];
        case MappingType.WidgetLevel:
          param = find(dashboardParameters, p => p.name === (m.mapTo || m.name));
          return [m.name, param ? param.value : m.param.value];
        case MappingType.DashboardAddNew:
        case MappingType.DashboardMapToExisting:
          param = find(dashboardParameters, p => p.name === m.mapTo);
          return [m.name, param ? param.value : null];
        // no default
      }
    }
  );
}

class EditParameterMappingsDialog extends React.Component {
  static propTypes = {
    dashboard: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
    widget: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
    dialog: DialogPropType.isRequired,
  };

  originalParamValuesSnapshot = null;

  constructor(props) {
    super(props);

    const parameterMappings = parameterMappingsToEditableMappings(
      props.widget.getParameterMappings(),
      props.widget.query.getParametersDefs(),
      map(this.props.dashboard.getParametersDefs(), p => p.name)
    );

    this.originalParamValuesSnapshot = getParamValuesSnapshot(
      parameterMappings,
      this.props.dashboard.getParametersDefs()
    );

    this.state = {
      saveInProgress: false,
      parameterMappings,
    };
  }

  saveWidget() {
    const widget = this.props.widget;

    this.setState({ saveInProgress: true });

    const newMappings = editableMappingsToParameterMappings(this.state.parameterMappings);
    widget.options.parameterMappings = newMappings;

    const valuesChanged = !isMatch(
      this.originalParamValuesSnapshot,
      getParamValuesSnapshot(this.state.parameterMappings, this.props.dashboard.getParametersDefs())
    );

    const widgetsToSave = [
      widget,
      ...synchronizeWidgetTitles(widget.options.parameterMappings, this.props.dashboard.widgets),
    ];

    Promise.all(map(widgetsToSave, w => w.save()))
      .then(() => {
        this.props.dialog.close(valuesChanged);
      })
      .catch(() => {
        notification.error("Widget cannot be updated");
      })
      .finally(() => {
        this.setState({ saveInProgress: false });
      });
  }

  updateParamMappings(parameterMappings) {
    this.setState({ parameterMappings });
  }

  render() {
    const { dialog } = this.props;
    return (
      <ModalShell
        dialog={dialog}
        title="Parameters"
        description="Map query parameters to dashboard-level values."
        size="lg"
        onOk={() => this.saveWidget()}
        okButtonProps={{ loading: this.state.saveInProgress }}>
        {this.state.parameterMappings.length > 0 && (
          <ModalSection title="Parameter mappings">
            <ParameterMappingListInput
              mappings={this.state.parameterMappings}
              existingParams={this.props.dashboard.getParametersDefs()}
              onChange={mappings => this.updateParamMappings(mappings)}
            />
          </ModalSection>
        )}
      </ModalShell>
    );
  }
}

export default wrapDialog(EditParameterMappingsDialog);
