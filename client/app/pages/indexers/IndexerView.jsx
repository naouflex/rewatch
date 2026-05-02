import React from "react";
import PropTypes from "prop-types";
import { get } from "lodash";

import Button from "antd/lib/button";
import Form from "antd/lib/form";

import Title from "./components/Title";
import Query from "./components/Query";
import HorizontalFormItem from "./components/HorizontalFormItem";
import IndexerDestination from "./components/IndexerDestination";
import { getStrategyDisplayName } from "./components/IndexerInsertStrategy";

export default function IndexerView({ indexer, queryResult, canEdit, onEdit, menuButton }) {
  const { query, name, options, data_source: dataSource } = indexer;
  const dataSourceId = dataSource ? dataSource.id : null;
  const targetTable = get(options, "target_table") || `indexed_data_${indexer.id}`;
  const strategyLabel = getStrategyDisplayName(get(options, "insert_strategy"));

  return (
    <>
      <Title indexer={indexer} name={name}>
        {canEdit && (
          <Button type="default" onClick={() => onEdit()}>
            <i className="fa fa-edit m-r-5" aria-hidden="true" />
            Edit
          </Button>
        )}
        {menuButton}
      </Title>
      <div className="bg-white tiled p-20">
        <Form>
          <HorizontalFormItem label="Query">
            <Query query={query} queryResult={queryResult} editMode={false} />
          </HorizontalFormItem>
          <HorizontalFormItem label="Target data source">
            <IndexerDestination value={dataSourceId} viewMode />
          </HorizontalFormItem>
          <HorizontalFormItem label="Target table">{targetTable}</HorizontalFormItem>
          <HorizontalFormItem label="Insert strategy">{strategyLabel}</HorizontalFormItem>
          {options && options.timestamp_field && (
            <HorizontalFormItem label="Timestamp column">{options.timestamp_field}</HorizontalFormItem>
          )}
          {options && options.remove_duplicates && (
            <HorizontalFormItem label="Options">Removes duplicates after each run.</HorizontalFormItem>
          )}
          {indexer.last_triggered_at && (
            <HorizontalFormItem label="Last run">
              {new Date(indexer.last_triggered_at).toLocaleString()}
            </HorizontalFormItem>
          )}
        </Form>
      </div>
    </>
  );
}

IndexerView.propTypes = {
  indexer: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
  queryResult: PropTypes.object, // eslint-disable-line react/forbid-prop-types
  canEdit: PropTypes.bool,
  onEdit: PropTypes.func,
  menuButton: PropTypes.node,
};

IndexerView.defaultProps = {
  queryResult: null,
  canEdit: false,
  onEdit: () => {},
  menuButton: null,
};
