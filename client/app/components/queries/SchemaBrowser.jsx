import { isNil, map, filter, some, includes, get } from "lodash";
import cx from "classnames";
import React, { useState, useCallback, useMemo, useEffect } from "react";
import PropTypes from "prop-types";
import { useDebouncedCallback } from "use-debounce";
import Input from "antd/lib/input";
import Button from "antd/lib/button";
import Select from "antd/lib/select";
import AutoSizer from "react-virtualized/dist/commonjs/AutoSizer";
import List from "react-virtualized/dist/commonjs/List";
import PlainButton from "@/components/PlainButton";
import Tooltip from "@/components/Tooltip";
import useDataSourceSchema from "@/pages/queries/hooks/useDataSourceSchema";
import useImmutableCallback from "@/lib/hooks/useImmutableCallback";
import LoadingState from "../items-list/components/LoadingState";

const SchemaItemColumnType = PropTypes.shape({
  name: PropTypes.string.isRequired,
  type: PropTypes.string,
  description: PropTypes.string,
  insertValue: PropTypes.string,
});

export const SchemaItemType = PropTypes.shape({
  name: PropTypes.string.isRequired,
  displayName: PropTypes.string,
  description: PropTypes.string,
  insertValue: PropTypes.string,
  size: PropTypes.number,
  loading: PropTypes.bool,
  columns: PropTypes.arrayOf(SchemaItemColumnType).isRequired,
});

const schemaTableHeight = 22;
const schemaColumnHeight = 18;

function SchemaItem({ item, expanded, onToggle, onSelect, ...props }) {
  const handleSelect = useCallback(
    (event, ...args) => {
      event.preventDefault();
      event.stopPropagation();
      onSelect(...args);
    },
    [onSelect]
  );

  if (!item) {
    return null;
  }

  const tableDisplayName = item.displayName || item.name;

  return (
    <div {...props}>
      <div className="schema-list-item">
        <Tooltip
          title={item.description}
          mouseEnterDelay={0}
          mouseLeaveDelay={0}
          placement="rightTop"
          trigger={item.description ? "hover" : ""}
          overlayStyle={{ whiteSpace: "pre-line" }}
        >
          <PlainButton className="table-name" onClick={onToggle}>
            <i className="fa fa-table m-r-5" aria-hidden="true" />
            <strong>
              <span title={item.name}>{tableDisplayName}</span>
              {!isNil(item.size) && <span> ({item.size})</span>}
            </strong>
          </PlainButton>
        </Tooltip>
        <Tooltip
          title="Insert table name into query text"
          mouseEnterDelay={0}
          mouseLeaveDelay={0}
          placement="topRight"
          arrow={{ pointAtCenter: true }}
        >
          <PlainButton className="copy-to-editor" onClick={(e) => handleSelect(e, item.insertValue || item.name)}>
            <i className="fa fa-angle-double-right" aria-hidden="true" />
          </PlainButton>
        </Tooltip>
      </div>
      {expanded && (
        <div className="table-open">
          {item.loading ? (
            <div className="table-open">Loading...</div>
          ) : (
            map(item.columns, (column) => {
              const columnName = get(column, "name");
              const columnType = get(column, "type");
              const columnDescription = get(column, "description");
              return (
                <Tooltip
                  title={"Insert column name into query text" + (columnDescription ? "\n" + columnDescription : "")}
                  mouseEnterDelay={0}
                  mouseLeaveDelay={0}
                  placement="rightTop"
                  overlayStyle={{ whiteSpace: "pre-line" }}
                >
                  <PlainButton
                    key={columnName}
                    className="table-open-item"
                    onClick={(e) => handleSelect(e, column.insertValue || columnName)}
                  >
                    <div>
                      {columnName} {columnType && <span className="column-type">{columnType}</span>}
                    </div>

                    <div className="copy-to-editor">
                      <i className="fa fa-angle-double-right" aria-hidden="true" />
                    </div>
                  </PlainButton>
                </Tooltip>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}

SchemaItem.propTypes = {
  item: SchemaItemType,
  expanded: PropTypes.bool,
  onToggle: PropTypes.func,
  onSelect: PropTypes.func,
};

SchemaItem.defaultProps = {
  item: null,
  expanded: false,
  onToggle: () => {},
  onSelect: () => {},
};

function SchemaLoadingState() {
  return (
    <div className="schema-loading-state">
      <LoadingState className="" />
    </div>
  );
}

export function SchemaList({ loading, schema, expandedFlags, onTableExpand, onItemSelect }) {
  const [listRef, setListRef] = useState(null);

  useEffect(() => {
    if (listRef) {
      listRef.recomputeRowHeights();
    }
  }, [listRef, schema, expandedFlags]);

  return (
    <div className="schema-browser">
      {loading && <SchemaLoadingState />}
      {!loading && (
        <AutoSizer>
          {({ width, height }) => (
            <List
              ref={setListRef}
              width={width}
              height={height}
              rowCount={schema.length}
              rowHeight={({ index }) => {
                const item = schema[index];
                const columnsLength = !item.loading ? item.columns.length : 1;
                let columnCount = expandedFlags[item.name] ? columnsLength : 0;
                return schemaTableHeight + schemaColumnHeight * columnCount;
              }}
              rowRenderer={({ key, index, style }) => {
                const item = schema[index];
                return (
                  <SchemaItem
                    key={key}
                    style={style}
                    item={item}
                    expanded={expandedFlags[item.name]}
                    onToggle={() => onTableExpand(item.name)}
                    onSelect={onItemSelect}
                  />
                );
              }}
            />
          )}
        </AutoSizer>
      )}
    </div>
  );
}

export function extractSchemaCategories(schema) {
  const categories = new Set();
  let hasUncategorized = false;

  schema.forEach((item) => {
    const dotIndex = item.name.indexOf(".");
    if (dotIndex > 0) {
      categories.add(item.name.slice(0, dotIndex));
    } else {
      hasUncategorized = true;
    }
  });

  if (categories.size <= 1) {
    return [];
  }

  const sorted = Array.from(categories).sort();
  return hasUncategorized ? ["all", ...sorted, "other"] : ["all", ...sorted];
}

export function filterSchemaByCategory(schema, category) {
  if (!category || category === "all") {
    return schema;
  }

  if (category === "other") {
    return filter(schema, (item) => item.name.indexOf(".") === -1);
  }

  const prefix = category + ".";
  return filter(schema, (item) => item.name.startsWith(prefix));
}

export function applyFilterOnSchema(schema, filterString) {
  const filters = filter(filterString.toLowerCase().split(/\s+/), (s) => s.length > 0);

  // Empty string: return original schema
  if (filters.length === 0) {
    return schema;
  }

  // Single word: matches table or column
  if (filters.length === 1) {
    const nameFilter = filters[0];
    const columnFilter = filters[0];
    return filter(
      schema,
      (item) => {
        const displayName = (item.displayName || "").toLowerCase();
        const description = (item.description || "").toLowerCase();
        return (
          includes(item.name.toLowerCase(), nameFilter) ||
          includes(displayName, nameFilter) ||
          includes(description, nameFilter) ||
          some(item.columns, (column) => includes(get(column, "name").toLowerCase(), columnFilter))
        );
      }
    );
  }

  // Two (or more) words: first matches table, seconds matches column
  const nameFilter = filters[0];
  const columnFilter = filters[1];
  return filter(
    map(schema, (item) => {
      if (includes(item.name.toLowerCase(), nameFilter)) {
        item = {
          ...item,
          columns: filter(item.columns, (column) => includes(get(column, "name").toLowerCase(), columnFilter)),
        };
        return item.columns.length > 0 ? item : null;
      }
    })
  );
}

export default function SchemaBrowser({
  dataSource,
  onSchemaUpdate,
  onItemSelect,
  options,
  onOptionsUpdate,
  ...props
}) {
  const [schema, isLoading, refreshSchema] = useDataSourceSchema(dataSource);
  const [filterString, setFilterString] = useState("");
  const categories = useMemo(() => extractSchemaCategories(schema), [schema]);
  const selectedCategory = get(options, "selectedCategory", "all");
  const categoryFilteredSchema = useMemo(
    () => filterSchemaByCategory(schema, categories.length > 0 ? selectedCategory : "all"),
    [schema, categories, selectedCategory]
  );
  const filteredSchema = useMemo(
    () => applyFilterOnSchema(categoryFilteredSchema, filterString),
    [categoryFilteredSchema, filterString]
  );
  const [handleFilterChange] = useDebouncedCallback(setFilterString, 500);
  const [expandedFlags, setExpandedFlags] = useState({});

  const handleSchemaUpdate = useImmutableCallback(onSchemaUpdate);
  const handleOptionsUpdate = useImmutableCallback(onOptionsUpdate);

  useEffect(() => {
    setExpandedFlags({});
    handleSchemaUpdate(schema);
  }, [schema, handleSchemaUpdate]);

  useEffect(() => {
    setExpandedFlags({});
  }, [selectedCategory]);

  if (schema.length === 0 && !isLoading) {
    return null;
  }

  function toggleTable(tableName) {
    setExpandedFlags({
      ...expandedFlags,
      [tableName]: !expandedFlags[tableName],
    });
  }

  function handleCategoryChange(category) {
    if (handleOptionsUpdate) {
      handleOptionsUpdate({
        ...(options || {}),
        selectedCategory: category,
      });
    }
  }

  return (
    <div className="schema-container" {...props}>
      <div className="schema-control">
        {categories.length > 0 && (
          <Select
            className="schema-category-select m-r-5"
            value={selectedCategory}
            onChange={handleCategoryChange}
            disabled={schema.length === 0}
            aria-label="Filter schema by category"
            dropdownMatchSelectWidth={false}>
            {categories.map((category) => (
              <Select.Option key={category} value={category}>
                {category === "all" ? "All categories" : category === "other" ? "Other" : category}
              </Select.Option>
            ))}
          </Select>
        )}
        <Input
          className="m-r-5"
          placeholder="Search schema..."
          aria-label="Search schema"
          disabled={schema.length === 0}
          onChange={(event) => handleFilterChange(event.target.value)}
        />

        <Tooltip title="Refresh Schema">
          <Button onClick={() => refreshSchema(true)}>
            <i className={cx("zmdi zmdi-refresh", { "zmdi-hc-spin": isLoading })} aria-hidden="true" />
            <span className="sr-only">{isLoading ? "Loading, please wait." : "Press to refresh."}</span>
          </Button>
        </Tooltip>
      </div>
      <SchemaList
        loading={isLoading && schema.length === 0}
        schema={filteredSchema}
        expandedFlags={expandedFlags}
        onTableExpand={toggleTable}
        onItemSelect={onItemSelect}
      />
    </div>
  );
}

SchemaBrowser.propTypes = {
  dataSource: PropTypes.object, // eslint-disable-line react/forbid-prop-types
  onSchemaUpdate: PropTypes.func,
  onItemSelect: PropTypes.func,
};

SchemaBrowser.defaultProps = {
  dataSource: null,
  onSchemaUpdate: () => {},
  onItemSelect: () => {},
};
