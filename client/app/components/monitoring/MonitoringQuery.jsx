import React from "react";
import PropTypes from "prop-types";

import Link from "@/components/Link";
import QuerySelector from "@/components/QuerySelector";
import SchedulePhrase from "@/components/queries/SchedulePhrase";
import TimeAgo from "@/components/TimeAgo";
import Tooltip from "@/components/Tooltip";

import WarningFilledIcon from "@ant-design/icons/WarningFilled";
import QuestionCircleOutlined from "@ant-design/icons/QuestionCircleOutlined";
import LoadingOutlinedIcon from "@ant-design/icons/LoadingOutlined";
import ExportOutlinedIcon from "@ant-design/icons/ExportOutlined";
import Tag from "antd/lib/tag";
import Table from "antd/lib/table";

import "./MonitoringQuery.less";

function QueryPreviewTable({ queryResult }) {
  const columns = queryResult.getColumnNames().map(name => ({
    title: name,
    dataIndex: name,
    key: name,
    ellipsis: true,
  }));
  const data = (queryResult.getData() || []).slice(0, 1).map((row, index) => ({ ...row, key: index }));

  if (!data.length) {
    return <small className="monitoring-query-preview-empty">No rows in cached result.</small>;
  }

  return (
    <div className="monitoring-query-preview">
      <div className="list-page-table">
        <Table
          className="table-data"
          columns={columns}
          dataSource={data}
          size="small"
          pagination={false}
          showHeader
        />
      </div>
    </div>
  );
}

QueryPreviewTable.propTypes = {
  queryResult: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
};

export default function MonitoringQuery({
  query,
  queryResult,
  onChange,
  editMode,
  scheduleWarning,
  className,
}) {
  const hasSchedule = query && query.schedule && query.schedule.interval;
  const queryDataAt = queryResult ? queryResult.getUpdatedAt() : null;

  const scheduleHint =
    query && !hasSchedule && scheduleWarning ? (
      <small className="monitoring-query-warning">
        <WarningFilledIcon className="warning-icon-danger" /> No refresh schedule.{" "}
        <Tooltip title={scheduleWarning}>
          <span role="presentation" className="monitoring-query-warning-link">
            Why it&apos;s recommended <QuestionCircleOutlined />
          </span>
        </Tooltip>
      </small>
    ) : null;

  return (
    <div className={`monitoring-query ${className || ""}`}>
      {editMode ? (
        <QuerySelector onChange={onChange} selectedQuery={query} className="monitoring-query-selector" type="select" />
      ) : (
        <Link href={`queries/${query.id}`} target="_blank" rel="noopener noreferrer" className="monitoring-query-link">
          {query.name} <ExportOutlinedIcon aria-hidden="true" />
          <span className="sr-only">(opens in a new tab)</span>
        </Link>
      )}

      {query && (
        <div className="monitoring-query-context">
          {hasSchedule ? (
            <Tag className="monitoring-query-schedule-tag">
              <SchedulePhrase schedule={query.schedule} isNew={false} />
            </Tag>
          ) : (
            scheduleHint
          )}
          {queryDataAt && (
            <span className="monitoring-query-data-at">
              Data from <TimeAgo date={queryDataAt} />
            </span>
          )}
        </div>
      )}

      {query && queryResult && <QueryPreviewTable queryResult={queryResult} />}

      {query && !queryResult && (
        <div className="monitoring-query-loading">
          <LoadingOutlinedIcon className="m-r-5" /> Loading query data
        </div>
      )}
    </div>
  );
}

MonitoringQuery.propTypes = {
  query: PropTypes.object, // eslint-disable-line react/forbid-prop-types
  queryResult: PropTypes.object, // eslint-disable-line react/forbid-prop-types
  onChange: PropTypes.func,
  editMode: PropTypes.bool,
  scheduleWarning: PropTypes.string,
  className: PropTypes.string,
};

MonitoringQuery.defaultProps = {
  query: null,
  queryResult: null,
  onChange: () => {},
  editMode: false,
  scheduleWarning: null,
  className: null,
};
