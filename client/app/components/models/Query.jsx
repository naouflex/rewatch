import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";

import Link from "@/components/Link";
import QuerySelector from "@/components/QuerySelector";
import SchedulePhrase from "@/components/queries/SchedulePhrase";
import { Query as QueryType } from "@/components/proptypes";

import Tooltip from "@/components/Tooltip";

import WarningFilledIcon from "@ant-design/icons/WarningFilled";
import QuestionCircleTwoToneIcon from "@ant-design/icons/QuestionCircleTwoTone";
import LoadingOutlinedIcon from "@ant-design/icons/LoadingOutlined";

import "./Query.less"; 

export default function QueryFormItem({
  query,
  queryResult,
  modelOptions,
  onChange,
  editMode,
  onFeatureChange,
  onTargetChange,
  onModelOptionsChange, // Add this new prop
}) {
  const [selectedColumns, setSelectedColumns] = useState({
    features: modelOptions?.features || [],
    targets: modelOptions?.targets || [],
  });

  useEffect(() => {
    if (queryResult && queryResult.getColumnNames) {
      const columnNames = queryResult.getColumnNames();

      setSelectedColumns({
        features: columnNames?.filter((col) => modelOptions?.features?.includes(col)),
        targets: columnNames?.filter((col) => modelOptions?.targets?.includes(col)),
      });
    }
  }, [queryResult, modelOptions]);

  const handleColumnSelection = (column, type) => {
    setSelectedColumns((prev) => {
      const newSelection = { ...prev };
      if (type === "features" || type === "targets") {
        if (newSelection[type].includes(column)) {
          // Unselect the column from the current type
          newSelection[type] = newSelection[type].filter((col) => col !== column);
        } else {
          // Select the column for the current type
          newSelection[type] = [...newSelection[type], column];
          
          // If selecting as a feature, unselect from targets (and vice versa)
          const oppositeType = type === "features" ? "targets" : "features";
          newSelection[oppositeType] = newSelection[oppositeType].filter((col) => col !== column);
        }
        
        // Call the appropriate change handler
        if (type === "features") {
          onFeatureChange(newSelection.features);
          onTargetChange(newSelection.targets);
        } else {
          onTargetChange(newSelection.targets);
          onFeatureChange(newSelection.features);
        }
      }
      return newSelection;
    });
  };

  const queryHint = query && query.schedule ? (
    <small>
      Scheduled to refresh{" "}
      <i className="model-query-schedule">
        <SchedulePhrase schedule={query.schedule} isNew={false} />
      </i>
    </small>
  ) : (
    <small>
      <WarningFilledIcon className="warning-icon-danger" /> This query has no <i>refresh schedule</i>.{" "}
      <Tooltip title="A query schedule is not necessary but is highly recommended for models. A Model without a query schedule will only send notifications if a user in your organization manually executes this query.">
        <a role="presentation" className="model-query-link">
          Why it&apos;s recommended <QuestionCircleTwoToneIcon />
        </a>
      </Tooltip>
    </small>
  );

  const handleQueryChange = (newQuery) => {
    // Call the original onChange function
    onChange(newQuery);

    // Reset features and targets
    onFeatureChange([]);
    onTargetChange([]);

  };

  return (
    <>
      {editMode ? (
        <QuerySelector onChange={handleQueryChange} selectedQuery={query} className="model-query-selector" type="select" />
      ) : (
        <Tooltip title="Open query in a new tab.">
          <Link href={`queries/${query.id}`} target="_blank" rel="noopener noreferrer" className="model-query-link">
            {query.name} <i className="fa fa-external-link" aria-hidden="true" />
            <span className="sr-only">(opens in a new tab)</span>
          </Link>
        </Tooltip>
      )}
      <div className="ant-form-item-explain">{query && queryHint}</div>
      {query && !queryResult && (
        <div className="m-t-30">
          <LoadingOutlinedIcon className="m-r-5" /> Loading query data
        </div>
      )}
      {queryResult && queryResult.getColumnNames && queryResult.getColumnNames().length > 0 && (
        <div className="column-selector-form m-t-30">
          <h4>Define Columns</h4>
          <br />
          <div className="column-selector-grid">
            <div>
              <strong>Column</strong>
            </div>
            <div>
              <strong>Feature</strong>
            </div>
            <div>
              <strong>Target</strong>
            </div>
            {queryResult.getColumnNames().map((column) => (
              <React.Fragment key={column}>
                <div>{column}</div>
                <div>
                  <input
                    type="checkbox"
                    checked={selectedColumns.features.includes(column)}
                    onChange={() => handleColumnSelection(column, "features")}
                    disabled={!editMode}
                    style={{ opacity: !editMode ? 0.5 : 1 }}
                  />
                </div>
                <div>
                  <input
                    type="checkbox"
                    checked={selectedColumns.targets.includes(column)}
                    onChange={() => handleColumnSelection(column, "targets")}
                    disabled={!editMode}
                    style={{ opacity: !editMode ? 0.5 : 1 }}
                  />
                </div>
              </React.Fragment>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

QueryFormItem.propTypes = {
  query: QueryType,
  queryResult: PropTypes.object, // eslint-disable-line react/forbid-prop-types
  modelOptions: PropTypes.shape({
    features: PropTypes.array,
    targets: PropTypes.array,
  }).isRequired,
  onChange: PropTypes.func,
  editMode: PropTypes.bool,
  onFeatureChange: PropTypes.func,
  onTargetChange: PropTypes.func,
  onModelOptionsChange: PropTypes.func.isRequired,
};

QueryFormItem.defaultProps = {
  query: null,
  queryResult: null,
  onChange: () => {},
  editMode: false,
  onFeatureChange: () => {},
  onTargetChange: () => {},
  onModelOptionsChange: () => {},
};