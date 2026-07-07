import React from "react";
import PropTypes from "prop-types";
import { wrap as wrapDialog, DialogPropType } from "@/components/DialogWrapper";
import { ModalShell } from "@/components/ModalShell";
import { FiltersType } from "@/components/Filters";
import VisualizationRenderer from "@/components/visualizations/VisualizationRenderer";
import VisualizationName from "@/components/visualizations/VisualizationName";

function ExpandedWidgetDialog({ dialog, widget, filters }) {
  return (
    <ModalShell
      dialog={dialog}
      title={
        <>
          <VisualizationName visualization={widget.visualization} /> <span>{widget.getQuery().name}</span>
        </>
      }
      description="Full-size preview of this dashboard widget."
      width="95%"
      footer="close"
      bodyClassName="modal-shell__body modal-shell__body--flush">
      <VisualizationRenderer
        visualization={widget.visualization}
        queryResult={widget.getQueryResult()}
        filters={filters}
        context="widget"
      />
    </ModalShell>
  );
}

ExpandedWidgetDialog.propTypes = {
  dialog: DialogPropType.isRequired,
  widget: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
  filters: FiltersType,
};

ExpandedWidgetDialog.defaultProps = {
  filters: [],
};

export default wrapDialog(ExpandedWidgetDialog);
