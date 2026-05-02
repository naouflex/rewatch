import React from "react";
import PropTypes from "prop-types";

import Form from "antd/lib/form";
import Button from "antd/lib/button";
import Select from "antd/lib/select";
import Checkbox from "antd/lib/checkbox";

import Title from "./components/Title";
import Query from "./components/Query";
import HorizontalFormItem from "./components/HorizontalFormItem";
import IndexerDestination from "./components/IndexerDestination";
import IndexerInsertStrategy from "./components/IndexerInsertStrategy";
import IndexerTargetTable from "./components/IndexerTargetTable";

export default class IndexerEdit extends React.Component {
  _isMounted = false;

  state = {
    saving: false,
  };

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

  cancel = () => {
    this.props.cancel();
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
    } = this.props;
    const { query, name, options, tags, data_source: dataSource } = indexer;
    const { saving } = this.state;
    const dataSourceId = dataSource ? dataSource.id : null;

    return (
      <>
        <Title indexer={indexer} name={name} onChange={onNameChange} editMode>
          <Button className="m-r-5" onClick={() => this.cancel()}>
            <i className="fa fa-times m-r-5" aria-hidden="true" />
            Cancel
          </Button>
          <Button type="primary" onClick={() => this.save()}>
            {saving ? (
              <span role="status" aria-live="polite" aria-relevant="additions removals">
                <i className="fa fa-spinner fa-pulse m-r-5" aria-hidden="true" />
                <span className="sr-only">Saving...</span>
              </span>
            ) : (
              <i className="fa fa-check m-r-5" aria-hidden="true" />
            )}
            Save Changes
          </Button>
          {menuButton}
        </Title>
        <div className="bg-white tiled p-20">
          <div className="d-flex">
            <Form className="flex-fill">
              <HorizontalFormItem label="Query">
                <Query query={query} queryResult={queryResult} onChange={onQuerySelected} editMode />
              </HorizontalFormItem>
              <HorizontalFormItem label="Tags" help="Press enter to add a tag.">
                <Select
                  mode="tags"
                  style={{ minWidth: 240 }}
                  value={tags || []}
                  onChange={onTagsChange}
                  tokenSeparators={[","]}
                  placeholder="Add tags"
                />
              </HorizontalFormItem>
              {queryResult && options && (
                <>
                  <HorizontalFormItem label="Target data source">
                    <IndexerDestination value={dataSourceId} onChange={onDataSourceChange} />
                  </HorizontalFormItem>
                  <HorizontalFormItem
                    label="Target table"
                    help={`If left empty, results will be written to "indexed_data_<id>".`}>
                    <IndexerTargetTable
                      targetTable={options.target_table || ""}
                      onChange={value => onOptionsChange({ target_table: value })}
                    />
                  </HorizontalFormItem>
                  <HorizontalFormItem label="Insert strategy">
                    <IndexerInsertStrategy
                      insertStrategy={options.insert_strategy}
                      onChange={value => onOptionsChange({ insert_strategy: value })}
                    />
                  </HorizontalFormItem>
                  <HorizontalFormItem
                    label="Timestamp column"
                    help="Optional. If set, missing values are filled with the current timestamp at indexing time.">
                    <input
                      type="text"
                      style={{ minWidth: 280 }}
                      className="ant-input"
                      placeholder="e.g. inserted_at"
                      value={options.timestamp_field || ""}
                      onChange={e => onOptionsChange({ timestamp_field: e.target.value })}
                    />
                  </HorizontalFormItem>
                  <HorizontalFormItem label="Options">
                    <Checkbox
                      checked={!!options.remove_duplicates}
                      onChange={e => onOptionsChange({ remove_duplicates: e.target.checked })}>
                      Remove duplicate rows after indexing (requires an <code>id</code> column on the target table).
                    </Checkbox>
                  </HorizontalFormItem>
                </>
              )}
            </Form>
          </div>
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
