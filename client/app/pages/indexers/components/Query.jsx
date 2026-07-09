import React from "react";
import PropTypes from "prop-types";

import MonitoringQuery from "@/components/monitoring/MonitoringQuery";

const SCHEDULE_WARNING =
  "A query schedule is highly recommended for indexers; without one, indexing will only happen when a user manually executes the query.";

export default function QueryFormItem(props) {
  return <MonitoringQuery scheduleWarning={SCHEDULE_WARNING} {...props} />;
}

QueryFormItem.propTypes = {
  query: PropTypes.object, // eslint-disable-line react/forbid-prop-types
  queryResult: PropTypes.object, // eslint-disable-line react/forbid-prop-types
  onChange: PropTypes.func,
  editMode: PropTypes.bool,
};

QueryFormItem.defaultProps = {
  query: null,
  queryResult: null,
  onChange: () => {},
  editMode: false,
};
