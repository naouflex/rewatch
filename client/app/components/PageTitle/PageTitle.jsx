import React from "react";
import PropTypes from "prop-types";
import Input from "antd/lib/input";

import "./PageTitle.less";

export default function PageTitle({ editMode, name, defaultName, placeholder, onChange, children }) {
  return (
    <div className="page-title">
      <div className="page-title__name">
        {editMode ? (
          <div className="page-title-field">
            <label htmlFor="page-title-input" className="page-title-field__label">
              Name
            </label>
            <Input
              id="page-title-input"
              className="page-title-field__input"
              placeholder={placeholder || defaultName || "Name"}
              value={name}
              onChange={e => onChange(e.target.value)}
            />
          </div>
        ) : (
          <h3>{name || defaultName}</h3>
        )}
      </div>
      {children && <div className="page-title__actions">{children}</div>}
    </div>
  );
}

PageTitle.propTypes = {
  editMode: PropTypes.bool,
  name: PropTypes.string,
  defaultName: PropTypes.string,
  placeholder: PropTypes.string,
  onChange: PropTypes.func,
  children: PropTypes.node,
};

PageTitle.defaultProps = {
  editMode: false,
  name: null,
  defaultName: null,
  placeholder: null,
  onChange: null,
  children: null,
};
