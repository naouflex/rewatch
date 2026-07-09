import React from "react";
import PropTypes from "prop-types";

import TimeAgo from "@/components/TimeAgo";
import StatusStrip from "@/components/StatusStrip/StatusStrip";
import { getStrategyDisplayName } from "./IndexerInsertStrategy";

import "@/components/StatusStrip/StatusStrip.less";

export default function IndexerStatusStrip({ indexer, queryResult, dataSourceName, targetTable }) {
  const items = [{ label: "Indexer", color: "info" }];

  if (indexer.last_triggered_at) {
    items.push({ label: <>Last run <TimeAgo date={indexer.last_triggered_at} /></> });
  } else {
    items.push({ label: "Not run yet" });
  }

  if (dataSourceName && targetTable) {
    items.push({ label: `→ ${dataSourceName}.${targetTable}` });
  }

  if (indexer.options?.insert_strategy) {
    items.push({ label: getStrategyDisplayName(indexer.options.insert_strategy) });
  }

  if (queryResult) {
    items.push({ label: <>Query data from <TimeAgo date={queryResult.getUpdatedAt()} /></> });
  }

  return <StatusStrip items={items} />;
}

IndexerStatusStrip.propTypes = {
  indexer: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
  queryResult: PropTypes.object, // eslint-disable-line react/forbid-prop-types
  dataSourceName: PropTypes.string,
  targetTable: PropTypes.string,
};

IndexerStatusStrip.defaultProps = {
  queryResult: null,
  dataSourceName: null,
  targetTable: null,
};
