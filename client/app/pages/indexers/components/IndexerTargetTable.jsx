import React from "react";
import PropTypes from "prop-types";
import Input from "antd/lib/input";

export default function IndexerTargetTable({ targetTable, onChange, viewMode, disabled, placeholder }) {
  if (viewMode) {
    return <div className="indexer-target-table">{targetTable || placeholder}</div>;
  }

  return (
    <Input
      style={{ minWidth: 280 }}
      placeholder={placeholder}
      value={targetTable || ""}
      disabled={disabled}
      onChange={e => onChange(e.target.value)}
    />
  );
}

IndexerTargetTable.propTypes = {
  targetTable: PropTypes.string,
  onChange: PropTypes.func,
  viewMode: PropTypes.bool,
  disabled: PropTypes.bool,
  placeholder: PropTypes.string,
};

IndexerTargetTable.defaultProps = {
  targetTable: "",
  onChange: () => {},
  viewMode: false,
  disabled: false,
  placeholder: "indexed_data_<id>",
};
