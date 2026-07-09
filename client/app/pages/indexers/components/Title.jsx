import React from "react";
import PropTypes from "prop-types";

import PageTitle from "@/components/PageTitle/PageTitle";
import { getDefaultName } from "../Indexer";

import "@/components/PageTitle/PageTitle.less";

export default function Title({ indexer, editMode, name, onChange, children }) {
  const defaultName = getDefaultName(indexer);
  return (
    <PageTitle
      editMode={editMode}
      name={name}
      defaultName={defaultName}
      placeholder={indexer.query ? defaultName : "Indexer name"}
      onChange={onChange}>
      {children}
    </PageTitle>
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
