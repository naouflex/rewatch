import React from "react";
import PropTypes from "prop-types";
import Select from "antd/lib/select";

const INSERT_STRATEGIES = [
  { value: "append", label: "Append (add new rows)" },
  { value: "overwrite", label: "Overwrite (clear existing data first)" },
];

export function getStrategyDisplayName(strategy) {
  const found = INSERT_STRATEGIES.find(s => s.value === strategy);
  return found ? found.label : INSERT_STRATEGIES[0].label;
}

export default function IndexerInsertStrategy({ insertStrategy, onChange, viewMode, disabled }) {
  if (viewMode) {
    return <div className="indexer-insert-strategy">{getStrategyDisplayName(insertStrategy)}</div>;
  }

  return (
    <Select
      className="indexer-insert-strategy"
      style={{ minWidth: 280 }}
      value={insertStrategy || "append"}
      onChange={onChange}
      disabled={disabled}>
      {INSERT_STRATEGIES.map(s => (
        <Select.Option key={s.value} value={s.value}>
          {s.label}
        </Select.Option>
      ))}
    </Select>
  );
}

IndexerInsertStrategy.propTypes = {
  insertStrategy: PropTypes.string,
  onChange: PropTypes.func,
  viewMode: PropTypes.bool,
  disabled: PropTypes.bool,
};

IndexerInsertStrategy.defaultProps = {
  insertStrategy: "append",
  onChange: () => {},
  viewMode: false,
  disabled: false,
};
