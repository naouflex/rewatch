import React from "react";
import PropTypes from "prop-types";
import { get } from "lodash";

import Button from "antd/lib/button";
import Select from "antd/lib/select";
import Checkbox from "antd/lib/checkbox";
import Tag from "antd/lib/tag";
import EditOutlinedIcon from "@ant-design/icons/EditOutlined";

import ConfigSection from "@/components/ConfigSection/ConfigSection";
import "@/components/ConfigSection/ConfigSection.less";

import Title from "./components/Title";
import Query from "./components/Query";
import IndexerDestination from "./components/IndexerDestination";
import IndexerInsertStrategy from "./components/IndexerInsertStrategy";
import IndexerTargetTable from "./components/IndexerTargetTable";
import IndexerTablePreview from "./components/IndexerTablePreview";
import IndexerStatusStrip from "./components/IndexerStatusStrip";
import { getStrategyDisplayName } from "./components/IndexerInsertStrategy";

export default function IndexerView({ indexer, queryResult, canEdit, onEdit, menuButton }) {
  const { query, name, options, data_source: dataSource } = indexer;
  const dataSourceId = dataSource ? dataSource.id : null;
  const dataSourceName = dataSource ? dataSource.name : null;
  const targetTable = get(options, "target_table") || `indexed_data_${indexer.id}`;
  const strategyLabel = getStrategyDisplayName(get(options, "insert_strategy"));

  return (
    <>
      <div className="create-page-form__header">
        <Title indexer={indexer} name={name}>
          {canEdit && (
            <Button type="primary" onClick={() => onEdit()}>
              <EditOutlinedIcon /> Edit
            </Button>
          )}
          {menuButton}
        </Title>
      </div>

      <IndexerStatusStrip
        indexer={indexer}
        queryResult={queryResult}
        dataSourceName={dataSourceName}
        targetTable={targetTable}
      />

      <div className="create-page-form__body">
        <ConfigSection title="Query">
          <Query query={query} queryResult={queryResult} editMode={false} />
        </ConfigSection>

        {queryResult && options && (
          <>
            <ConfigSection title="Target">
              <dl className="indexer-detail-list">
                <div className="indexer-detail-list__row">
                  <dt>Data source</dt>
                  <dd>
                    <IndexerDestination value={dataSourceId} viewMode />
                  </dd>
                </div>
                <div className="indexer-detail-list__row">
                  <dt>Table</dt>
                  <dd>{targetTable}</dd>
                </div>
                <div className="indexer-detail-list__row">
                  <dt>Strategy</dt>
                  <dd>{strategyLabel}</dd>
                </div>
                {options.timestamp_field && (
                  <div className="indexer-detail-list__row">
                    <dt>Timestamp column</dt>
                    <dd>{options.timestamp_field}</dd>
                  </div>
                )}
                {options.remove_duplicates && (
                  <div className="indexer-detail-list__row">
                    <dt>Options</dt>
                    <dd>Removes duplicates after each run</dd>
                  </div>
                )}
              </dl>
            </ConfigSection>
          </>
        )}

        {indexer.tags && indexer.tags.length > 0 && (
          <ConfigSection title="Tags">
            {indexer.tags.map(t => (
              <Tag key={t} color="blue">
                {t}
              </Tag>
            ))}
          </ConfigSection>
        )}

        {indexer.id && dataSourceId && (
          <ConfigSection title="Output preview">
            <IndexerTablePreview indexerId={indexer.id} targetTable={targetTable} embedded />
          </ConfigSection>
        )}
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
