import React from "react";
import PropTypes from "prop-types";

import Table from "antd/lib/table";
import Button from "antd/lib/button";
import Alert from "antd/lib/alert";

import ReloadOutlinedIcon from "@ant-design/icons/ReloadOutlined";

import IndexerService from "@/services/indexer";

import "@/components/items-list/list-page-layout.less";
import "./IndexerTablePreview.less";

function formatCellValue(value) {
  if (value === null || value === undefined) {
    return "—";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function buildColumns(columns) {
  return (columns || []).map(column => ({
    title: column.friendly_name || column.name,
    dataIndex: column.name,
    key: column.name,
    ellipsis: true,
    render: formatCellValue,
  }));
}

export default class IndexerTablePreview extends React.Component {
  static propTypes = {
    indexerId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
    targetTable: PropTypes.string,
    embedded: PropTypes.bool,
  };

  static defaultProps = {
    targetTable: null,
    embedded: false,
  };

  state = {
    preview: null,
    loading: true,
    error: null,
  };

  componentDidMount() {
    this.refresh();
  }

  componentDidUpdate(prevProps) {
    if (prevProps.indexerId !== this.props.indexerId) {
      this.refresh();
    }
  }

  refresh = () => {
    const { indexerId } = this.props;
    this.setState({ loading: true, error: null });
    IndexerService.preview({ id: indexerId })
      .then(preview => this.setState({ preview, loading: false, error: null }))
      .catch(error => {
        const message = error?.response?.data?.message || "Failed to load table preview.";
        this.setState({ preview: null, loading: false, error: message });
      });
  };

  render() {
    const { targetTable, embedded } = this.props;
    const { preview, loading, error } = this.state;
    const tableName = preview?.target_table || targetTable;
    const columns = buildColumns(preview?.columns);
    const rows = (preview?.rows || []).map((row, index) => ({ ...row, __rowKey: index }));

    return (
      <div
        className={`indexer-table-preview ${embedded ? "indexer-table-preview--embedded" : ""}`}
        data-test="IndexerTablePreview">
        <div className="indexer-table-preview__header">
          {!embedded && (
            <h4 className="indexer-table-preview__title">Table preview{tableName ? `: ${tableName}` : ""}</h4>
          )}
          {embedded && tableName && <span className="indexer-table-preview__table-name">{tableName}</span>}
          <Button size="small" onClick={this.refresh} loading={loading}>
            <ReloadOutlinedIcon /> Refresh
          </Button>
        </div>
        {error && !loading && (
          <Alert type="warning" showIcon message={error} className="indexer-table-preview__error" />
        )}
        <div className="list-page-table">
          <Table
            className="table-data"
            rowKey="__rowKey"
            size="small"
            loading={loading}
            dataSource={rows}
            columns={columns}
            scroll={{ x: true }}
            pagination={{ pageSize: 10, hideOnSinglePage: true, showSizeChanger: false }}
            locale={{
              emptyText: error
                ? "Preview unavailable."
                : "No rows in the target table yet. Run the indexer to populate it.",
            }}
          />
        </div>
        {preview?.row_count > 0 && (
          <p className="indexer-table-preview__footnote">
            Showing up to {preview.limit} rows{preview.row_count >= preview.limit ? " (preview limit reached)" : ""}.
          </p>
        )}
      </div>
    );
  }
}
