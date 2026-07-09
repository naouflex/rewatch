import React from "react";
import PropTypes from "prop-types";

import TimeAgo from "@/components/TimeAgo";
import StatusStrip from "@/components/StatusStrip/StatusStrip";

import "@/components/StatusStrip/StatusStrip.less";

const STATE_COLORS = {
  unknown: "warning",
  ok: "success",
  triggered: "error",
  training: "info",
  predicting: "info",
};

function stateLabel(state) {
  if (!state) return "Unknown";
  return state.charAt(0).toUpperCase() + state.slice(1);
}

export default function ModelStatusStrip({ model, queryDataAt }) {
  const { options = {} } = model;
  const items = [
    {
      label: stateLabel(model.state),
      color: STATE_COLORS[model.state] || "warning",
    },
    {
      label: (
        <>
          Training: <strong>{stateLabel(model.state_train)}</strong>
          {options.train_last_triggered_at && (
            <>
              {" "}
              · <TimeAgo date={options.train_last_triggered_at} />
            </>
          )}
        </>
      ),
    },
    {
      label: (
        <>
          Predicting: <strong>{stateLabel(model.state_predict)}</strong>
          {options.predict_last_triggered_at && (
            <>
              {" "}
              · <TimeAgo date={options.predict_last_triggered_at} />
            </>
          )}
        </>
      ),
    },
  ];

  if (queryDataAt) {
    items.push({ label: <>Query data from <TimeAgo date={queryDataAt} /></> });
  }

  if (options.muted) {
    items[0].tag = "Muted";
    items[0].tagColor = "warning";
  }

  return <StatusStrip items={items} />;
}

ModelStatusStrip.propTypes = {
  model: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
  queryDataAt: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
};

ModelStatusStrip.defaultProps = {
  queryDataAt: null,
};
