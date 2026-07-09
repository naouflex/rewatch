import React from "react";
import PropTypes from "prop-types";

import Button from "antd/lib/button";
import Checkbox from "antd/lib/checkbox";
import LoadingOutlinedIcon from "@ant-design/icons/LoadingOutlined";

import ConfigSection from "@/components/ConfigSection/ConfigSection";
import CreatePageLayout from "@/components/items-list/CreatePageLayout";
import "@/components/ConfigSection/ConfigSection.less";

import Title from "./components/Title";
import Query from "./components/Query";
import IndexerDestination from "./components/IndexerDestination";
import IndexerInsertStrategy from "./components/IndexerInsertStrategy";
import IndexerTargetTable from "./components/IndexerTargetTable";

export default class IndexerNew extends React.Component {
  state = { saving: false };

  save = () => {
    this.setState({ saving: true });
    this.props.save().catch(() => {
      this.setState({ saving: false });
    });
  };

  render() {
    const { indexer, queryResult, onQuerySelected, onNameChange, onOptionsChange, onDataSourceChange } = this.props;
    const { query, name, options, data_source: dataSource } = indexer;
    const { saving } = this.state;
    const dataSourceId = dataSource ? dataSource.id : null;
    const canCreate = !!query && !!dataSourceId;

    return (
      <>
        <CreatePageLayout backHref="indexers" backLabel="Back to Indexers" />
        <div className="create-page-form__header">
          <Title indexer={indexer} name={name} onChange={onNameChange} editMode />
        </div>
        <div className="create-page-form__body">
          <p className="create-page-form__intro">
            Select the query whose results you want to copy into another data source. Indexers run after every
            successful query execution, so a refresh schedule is highly recommended.
          </p>

          <ConfigSection title="Query">
            <Query query={query} queryResult={queryResult} onChange={onQuerySelected} editMode />
          </ConfigSection>

          {queryResult && options && (
            <ConfigSection title="Target">
              <div className="indexer-form-field">
                <label className="indexer-form-field__label">Target data source</label>
                <IndexerDestination value={dataSourceId} onChange={onDataSourceChange} />
              </div>
              <div className="indexer-form-field">
                <label className="indexer-form-field__label">Target table</label>
                <IndexerTargetTable
                  targetTable={options.target_table || ""}
                  onChange={value => onOptionsChange({ target_table: value })}
                />
              </div>
              <div className="indexer-form-field">
                <label className="indexer-form-field__label">Insert strategy</label>
                <IndexerInsertStrategy
                  insertStrategy={options.insert_strategy}
                  onChange={value => onOptionsChange({ insert_strategy: value })}
                />
              </div>
              <div className="indexer-form-field">
                <label className="indexer-form-field__label">Timestamp column</label>
                <input
                  type="text"
                  className="ant-input"
                  style={{ maxWidth: 320 }}
                  placeholder="e.g. inserted_at"
                  value={options.timestamp_field || ""}
                  onChange={e => onOptionsChange({ timestamp_field: e.target.value })}
                />
              </div>
              <div className="indexer-form-field">
                <Checkbox
                  checked={!!options.remove_duplicates}
                  onChange={e => onOptionsChange({ remove_duplicates: e.target.checked })}>
                  Remove duplicate rows after indexing (requires an <code>id</code> column on the target table).
                </Checkbox>
              </div>
            </ConfigSection>
          )}

          <div className="create-page-form__footer">
            <Button type="primary" onClick={this.save} disabled={!canCreate} loading={saving}>
              {saving && <LoadingOutlinedIcon />}
              Create Indexer
            </Button>
          </div>
        </div>
      </>
    );
  }
}

IndexerNew.propTypes = {
  indexer: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
  queryResult: PropTypes.object, // eslint-disable-line react/forbid-prop-types
  onQuerySelected: PropTypes.func.isRequired,
  save: PropTypes.func.isRequired,
  onNameChange: PropTypes.func.isRequired,
  onOptionsChange: PropTypes.func.isRequired,
  onDataSourceChange: PropTypes.func.isRequired,
};

IndexerNew.defaultProps = {
  queryResult: null,
};
