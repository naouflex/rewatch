import React from "react";
import PropTypes from "prop-types";

import Button from "antd/lib/button";
import Select from "antd/lib/select";
import Checkbox from "antd/lib/checkbox";
import CloseOutlinedIcon from "@ant-design/icons/CloseOutlined";
import CheckOutlinedIcon from "@ant-design/icons/CheckOutlined";
import LoadingOutlinedIcon from "@ant-design/icons/LoadingOutlined";

import ConfigSection from "@/components/ConfigSection/ConfigSection";
import "@/components/ConfigSection/ConfigSection.less";

import Title from "./components/Title";
import Query from "./components/Query";
import IndexerDestination from "./components/IndexerDestination";
import IndexerInsertStrategy from "./components/IndexerInsertStrategy";
import IndexerTargetTable from "./components/IndexerTargetTable";
import IndexerStatusStrip from "./components/IndexerStatusStrip";

export default class IndexerEdit extends React.Component {
  _isMounted = false;

  state = { saving: false };

  componentDidMount() {
    this._isMounted = true;
  }

  componentWillUnmount() {
    this._isMounted = false;
  }

  save = () => {
    this.setState({ saving: true });
    this.props.save().catch(() => {
      if (this._isMounted) this.setState({ saving: false });
    });
  };

  render() {
    const {
      indexer,
      queryResult,
      menuButton,
      onTagsChange,
      onQuerySelected,
      onNameChange,
      onOptionsChange,
      onDataSourceChange,
      cancel,
    } = this.props;
    const { query, name, options, tags, data_source: dataSource } = indexer;
    const { saving } = this.state;
    const dataSourceId = dataSource ? dataSource.id : null;
    const dataSourceName = dataSource ? dataSource.name : null;
    const targetTable = (options && options.target_table) || `indexed_data_${indexer.id}`;

    return (
      <>
        <div className="create-page-form__header">
          <Title indexer={indexer} name={name} onChange={onNameChange} editMode>
            <Button onClick={() => cancel()}>
              <CloseOutlinedIcon /> Cancel
            </Button>
            <Button type="primary" onClick={() => this.save()} loading={saving}>
              {saving ? <LoadingOutlinedIcon /> : <CheckOutlinedIcon />}
              Save Changes
            </Button>
            {menuButton}
          </Title>
        </div>

        {indexer.id && (
          <IndexerStatusStrip
            indexer={indexer}
            queryResult={queryResult}
            dataSourceName={dataSourceName}
            targetTable={targetTable}
          />
        )}

        <div className="create-page-form__body">
          <ConfigSection title="Query">
            <Query query={query} queryResult={queryResult} onChange={onQuerySelected} editMode />
          </ConfigSection>

          <ConfigSection title="Tags" help="Press enter to add a tag.">
            <Select
              mode="tags"
              style={{ width: "100%", maxWidth: 400 }}
              value={tags || []}
              onChange={onTagsChange}
              tokenSeparators={[","]}
              placeholder="Add tags"
            />
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
                <p className="indexer-form-field__help">If left empty, results will be written to indexed_data_&lt;id&gt;.</p>
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
                <p className="indexer-form-field__help">Optional. Missing values are filled with the current timestamp.</p>
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
        </div>
      </>
    );
  }
}

IndexerEdit.propTypes = {
  indexer: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
  queryResult: PropTypes.object, // eslint-disable-line react/forbid-prop-types
  menuButton: PropTypes.node.isRequired,
  save: PropTypes.func.isRequired,
  cancel: PropTypes.func.isRequired,
  onQuerySelected: PropTypes.func.isRequired,
  onNameChange: PropTypes.func.isRequired,
  onOptionsChange: PropTypes.func.isRequired,
  onDataSourceChange: PropTypes.func.isRequired,
  onTagsChange: PropTypes.func.isRequired,
};

IndexerEdit.defaultProps = {
  queryResult: null,
};
