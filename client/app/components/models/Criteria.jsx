import React from "react";
import PropTypes from "prop-types";
import { head, includes, toString, isEmpty } from "lodash";

import Input from "antd/lib/input";
import WarningFilledIcon from "@ant-design/icons/WarningFilled";
import Select from "antd/lib/select";
import Divider from "antd/lib/divider";

import { ModelOptions as ModelOptionsType } from "@/components/proptypes";

import "./Criteria.less";

const CONDITIONS = {
  ">": "\u003e",
  ">=": "\u2265",
  "<": "\u003c",
  "<=": "\u2264",
  "==": "\u003d",
  "!=": "\u2260",
};

const VALID_STRING_CONDITIONS = ["==", "!="];

function DisabledInput({ children, minWidth }) {
  return (
    <div className="criteria-disabled-input" style={{ minWidth }}>
      {children}
    </div>
  );
}

DisabledInput.propTypes = {
  children: PropTypes.node.isRequired,
  minWidth: PropTypes.number.isRequired,
};

export default function Criteria({ columnNames, resultValues, modelOptions, onChange, editMode, criteriaType }) {
  const columnKey = `column_${criteriaType}`;
  const opKey = `op_${criteriaType}`;
  const valueKey = `value_${criteriaType}`;
  const columnValue = !isEmpty(resultValues) ? head(resultValues)[modelOptions[columnKey]] : null;
  const invalidMessage = (() => {
    // bail if condition is valid for strings
    if (includes(VALID_STRING_CONDITIONS, modelOptions[opKey])) {
      return null;
    }

    if (isNaN(modelOptions[valueKey])) {
      return "Value column type doesn't match threshold type.";
    }

    if (isNaN(columnValue)) {
      return "Value column isn't supported by condition type.";
    }

    return null;
  })();

  const columnHint = (
    <small className="model-criteria-hint">
      Top row value is <code className="p-0">{toString(columnValue) || "unknown"}</code>
    </small>
  );

  const handleCriteriaChange = (value) => {
    onChange({ [`${criteriaType}_criteria`]: value });
  };

  const formatCriteriaValue = (value) => {
    switch (value) {
      case "query_refreshed":
        return "When query is refreshed";
      case "based_on_column":
        return "Based on column value";
      case "do_nothing":
        return "Do nothing";
      default:
        return value;
    }
  };

  return (
    <div data-test="Criteria">
      <div className="input-title">
        <span className="input-label">Criteria</span>
        {editMode ? (
          <Select
            value={modelOptions[`${criteriaType}_criteria`]}
            onChange={handleCriteriaChange}
            popupMatchSelectWidth={false}
            style={{ minWidth: 150 }}>
            <Select.Option value="query_refreshed">When query is refreshed</Select.Option>
            <Select.Option value="based_on_column">Based on column value</Select.Option>
            <Select.Option value="do_nothing">Do nothing</Select.Option>
          </Select>
        ) : (
          <DisabledInput minWidth={150}>
            {formatCriteriaValue(modelOptions[`${criteriaType}_criteria`])}
          </DisabledInput>
        )}
      </div>
      {modelOptions[`${criteriaType}_criteria`] === "based_on_column" && (
        <>
          <div className="input-title">
            <span className="input-label">Value column</span>
            {editMode ? (
              <Select
                value={modelOptions[columnKey]}
                onChange={column => onChange({ [columnKey]: column })}
                popupMatchSelectWidth={false}
                style={{ minWidth: 100 }}>
                {columnNames.map(name => (
                  <Select.Option key={name}>{name}</Select.Option>
                ))}
              </Select>
            ) : (
              <DisabledInput minWidth={70}>{modelOptions[columnKey]}</DisabledInput>
            )}
          </div>
          <div className="input-title">
            <span className="input-label">Condition</span>
            {editMode ? (
              <Select
                value={modelOptions[opKey]}
                onChange={op => onChange({ [opKey]: op })}
                optionLabelProp="label"
                popupMatchSelectWidth={false}
                style={{ width: 55 }}>
                <Select.Option value=">" label={CONDITIONS[">"]}>
                  {CONDITIONS[">"]} greater than
                </Select.Option>
                <Select.Option value=">=" label={CONDITIONS[">="]}>
                  {CONDITIONS[">="]} greater than or equals
                </Select.Option>
                <Select.Option disabled key="dv1">
                  <Divider className="select-option-divider m-t-10 m-b-5" />
                </Select.Option>
                <Select.Option value="<" label={CONDITIONS["<"]}>
                  {CONDITIONS["<"]} less than
                </Select.Option>
                <Select.Option value="<=" label={CONDITIONS["<="]}>
                  {CONDITIONS["<="]} less than or equals
                </Select.Option>
                <Select.Option disabled key="dv2">
                  <Divider className="select-option-divider m-t-10 m-b-5" />
                </Select.Option>
                <Select.Option value="==" label={CONDITIONS["=="]}>
                  {CONDITIONS["=="]} equals
                </Select.Option>
                <Select.Option value="!=" label={CONDITIONS["!="]}>
                  {CONDITIONS["!="]} not equal to
                </Select.Option>
              </Select>
            ) : (
              <DisabledInput minWidth={50}>{CONDITIONS[modelOptions[opKey]]}</DisabledInput>
            )}
          </div>
          <div className="input-title">
            <label className="input-label" htmlFor="threshold-criterion">
              Threshold
            </label>
            {editMode ? (
              <Input
                id="threshold-criterion"
                style={{ width: 90 }}
                value={modelOptions[valueKey]}
                onChange={e => onChange({ [valueKey]: e.target.value })}
              />
            ) : (
              <DisabledInput minWidth={50}>{modelOptions[valueKey]}</DisabledInput>
            )}
          </div>
          <div className="ant-form-item-explain">
            {columnHint}
            <br />
            {invalidMessage && (
              <small>
                <WarningFilledIcon className="warning-icon-danger" /> {invalidMessage}
              </small>
            )}
          </div>
        </>
      )}
    </div>
  );
}

Criteria.propTypes = {
  columnNames: PropTypes.arrayOf(PropTypes.string).isRequired,
  resultValues: PropTypes.arrayOf(PropTypes.object).isRequired,
  modelOptions: ModelOptionsType.isRequired,
  onChange: PropTypes.func,
  editMode: PropTypes.bool,
  criteriaType: PropTypes.oneOf(['train', 'predict']).isRequired,
};

Criteria.defaultProps = {
  onChange: () => { },
  editMode: false,
};
