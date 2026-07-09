import React from "react";
import PropTypes from "prop-types";

import Link from "@/components/Link";
import QuerySelector from "@/components/QuerySelector";
import SchedulePhrase from "@/components/queries/SchedulePhrase";
import TimeAgo from "@/components/TimeAgo";
import { Query as QueryType } from "@/components/proptypes";
import Tooltip from "@/components/Tooltip";

import WarningFilledIcon from "@ant-design/icons/WarningFilled";
import QuestionCircleOutlined from "@ant-design/icons/QuestionCircleOutlined";
import LoadingOutlinedIcon from "@ant-design/icons/LoadingOutlined";
import ExportOutlinedIcon from "@ant-design/icons/ExportOutlined";
import Tag from "antd/lib/tag";
import Table from "antd/lib/table";

import "./Query.less";

function QueryPreviewTable({ queryResult }) {
  const columns = queryResult.getColumnNames().map(name => ({
    title: name,
    dataIndex: name,
    key: name,
    ellipsis: true,
  }));
  const data = (queryResult.getData() || []).slice(0, 1).map((row, index) => ({ ...row, key: index }));

  if (!data.length) {
    return <small className="alert-query-preview-empty">No rows in cached result.</small>;
  }

  return (
    <div className="alert-query-preview">
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

export default function QueryFormItem({ query, queryResult, onChange, editMode }) {
  const hasSchedule = query && query.schedule && query.schedule.interval;
  const queryDataAt = queryResult ? queryResult.getUpdatedAt() : null;

  const scheduleWarning = query && !hasSchedule && (
    <small className="alert-query-warning">
      <WarningFilledIcon className="warning-icon-danger" /> No refresh schedule.{" "}
      <Tooltip title="A query schedule is not necessary but is highly recommended for alerts. An Alert without a query schedule will only send notifications if a user in your organization manually executes this query.">
        <span role="presentation" className="alert-query-warning-link">
          Why it&apos;s recommended <QuestionCircleOutlined />
        </span>
      </Tooltip>
    </small>
  );

  return (
    <div className="alert-query">
      {editMode ? (
        <QuerySelector onChange={onChange} selectedQuery={query} className="alert-query-selector" type="select" />
      ) : (
        <Link href={`queries/${query.id}`} target="_blank" rel="noopener noreferrer" className="alert-query-link">
          {query.name} <ExportOutlinedIcon aria-hidden="true" />
          <span className="sr-only">(opens in a new tab)</span>
        </Link>
      )}

      {query && (
        <div className="alert-query-context">
          {hasSchedule ? (
            <Tag className="alert-query-schedule-tag">
              <SchedulePhrase schedule={query.schedule} isNew={false} />
            </Tag>
          ) : (
            scheduleWarning
          )}
          {queryDataAt && (
            <span className="alert-query-data-at">
              Data from <TimeAgo date={queryDataAt} />
            </span>
          )}
        </div>
      )}

      {query && queryResult && <QueryPreviewTable queryResult={queryResult} />}

      {query && !queryResult && (
        <div className="alert-query-loading">
          <LoadingOutlinedIcon className="m-r-5" /> Loading query data
        </div>
      )}
    </div>
  );
}

QueryFormItem.propTypes = {
  query: QueryType,
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
