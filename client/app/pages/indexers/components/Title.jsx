import React from "react";
import PropTypes from "prop-types";
import Input from "antd/lib/input";
import { getDefaultName } from "../Indexer";

export default function Title({ indexer, editMode, name, onChange, children }) {
  const defaultName = getDefaultName(indexer);
  return (
    <div className="alert-header">
      <div className="alert-title">
        <h3>
          {editMode ? (
            <Input
              className="f-inherit"
              placeholder={indexer.query ? defaultName : "Indexer name"}
              value={name}
              aria-label="Indexer title"
              onChange={e => onChange(e.target.value)}
            />
          ) : (
            name || defaultName
          )}
        </h3>
      </div>
      <div className="alert-actions">{children}</div>
    </div>
  );
}

Title.propTypes = {
  indexer: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
  name: PropTypes.string,
  children: PropTypes.node,
  onChange: PropTypes.func,
  editMode: PropTypes.bool,
};

Title.defaultProps = {
  name: null,
  children: null,
  onChange: null,
  editMode: false,
};
