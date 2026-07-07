import React from "react";
import PropTypes from "prop-types";

import * as Sidebar from "./Sidebar";

import "../list-page-layout.less";

export default function ListPageToolbar({
  searchPlaceholder,
  searchLabel,
  searchValue,
  onSearchChange,
  menu,
  selected,
  tagsUrl,
  onTagsChange,
  selectedTags,
  showUnselectAll,
}) {
  return (
    <div className="list-page-toolbar">
      <Sidebar.SearchInput
        placeholder={searchPlaceholder}
        label={searchLabel}
        value={searchValue}
        onChange={onSearchChange}
        showIcon
        className="page-toolbar-search"
      />
      {menu?.length > 0 && (
        <div className="list-page-toolbar__filters">
          <Sidebar.FilterMenu items={menu} selected={selected} />
        </div>
      )}
      {tagsUrl && (
        <Sidebar.Tags
          url={tagsUrl}
          onChange={onTagsChange}
          showUnselectAll={showUnselectAll}
          layout="inline"
          selectedTags={selectedTags}
        />
      )}
    </div>
  );
}

ListPageToolbar.propTypes = {
  searchPlaceholder: PropTypes.string,
  searchLabel: PropTypes.string,
  searchValue: PropTypes.string.isRequired,
  onSearchChange: PropTypes.func.isRequired,
  menu: PropTypes.arrayOf(PropTypes.object),
  selected: PropTypes.string,
  tagsUrl: PropTypes.string,
  onTagsChange: PropTypes.func,
  selectedTags: PropTypes.arrayOf(PropTypes.string),
  showUnselectAll: PropTypes.bool,
};

ListPageToolbar.defaultProps = {
  searchPlaceholder: "Search...",
  searchLabel: "Search",
  menu: [],
  selected: null,
  tagsUrl: null,
  onTagsChange: null,
  selectedTags: undefined,
  showUnselectAll: true,
};
