import React, { useState, useMemo, useEffect, useCallback } from "react";
import PropTypes from "prop-types";
import { filter, includes } from "lodash";
import { useDebouncedCallback } from "use-debounce";
import Input from "antd/lib/input";
import Button from "antd/lib/button";
import Select from "antd/lib/select";
import SyncOutlinedIcon from "@ant-design/icons/SyncOutlined";
import Tooltip from "@/components/Tooltip";
import useDataSourceSchema from "@/pages/queries/hooks/useDataSourceSchema";
import useImmutableCallback from "@/lib/hooks/useImmutableCallback";
import {
  SchemaList,
  applyFilterOnSchema,
  extractSchemaCategories,
  filterSchemaByCategory,
} from "@/components/queries/SchemaBrowser";

import "./ApiSchemaBrowser.less";

const CATEGORY_LABELS = {
  all: "All categories",
  other: "Other",
  market: "Market Data",
  reference: "Reference",
  detail: "Coin Detail",
  coins: "Popular Coins",
  tvl: "TVL",
  stablecoins: "Stablecoins",
  yields: "Yields",
  dex: "DEX Volumes",
  fees: "Fees & Revenue",
  analytics: "Analytics",
  bridges: "Bridges",
  etfs: "ETFs",
};

function formatCategoryLabel(category) {
  return CATEGORY_LABELS[category] || category;
}

export default function ApiSchemaBrowser({
  dataSource,
  options,
  onOptionsUpdate,
  onSchemaUpdate,
  onItemSelect,
  ...props
}) {
  const [schema, isLoading, refreshSchema] = useDataSourceSchema(dataSource);
  const [filterString, setFilterString] = useState("");
  const [categoryFilterString, setCategoryFilterString] = useState("");
  const [isCategorySelectOpen, setIsCategorySelectOpen] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const categories = useMemo(() => extractSchemaCategories(schema), [schema]);
  const selectedCategory = options?.selectedCategory || "all";

  const categoryFilteredSchema = useMemo(
    () => filterSchemaByCategory(schema, categories.length > 0 ? selectedCategory : "all"),
    [schema, categories, selectedCategory]
  );

  const filteredSchema = useMemo(
    () => applyFilterOnSchema(categoryFilteredSchema, filterString),
    [categoryFilteredSchema, filterString]
  );

  const filteredCategories = useMemo(
    () =>
      filter(categories, (category) =>
        includes(formatCategoryLabel(category).toLowerCase(), categoryFilterString.toLowerCase())
      ),
    [categories, categoryFilterString]
  );

  const [handleFilterChange] = useDebouncedCallback(setFilterString, 500);
  const [handleCategoryFilterChange, cancelCategoryFilterChange] = useDebouncedCallback(setCategoryFilterString, 500);
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

  const handleCategoryChange = useCallback(
    (category) => {
      handleOptionsUpdate?.({
        ...(options || {}),
        selectedCategory: category,
      });
      cancelCategoryFilterChange();
      setCategoryFilterString("");
    },
    [cancelCategoryFilterChange, handleOptionsUpdate, options]
  );

  const handleRefresh = useCallback(() => {
    setRefreshing(true);
    refreshSchema(true).finally(() => setRefreshing(false));
  }, [refreshSchema]);

  function toggleTable(tableName) {
    setExpandedFlags({
      ...expandedFlags,
      [tableName]: !expandedFlags[tableName],
    });
  }

  if (schema.length === 0 && !isLoading) {
    return null;
  }

  const showCategorySelect = categories.length > 0;

  return (
    <div className="api-schema-browser schema-container" {...props}>
      <div className="schema-control">
        <Input
          className={isCategorySelectOpen ? "category-select-open" : ""}
          placeholder="Filter endpoints..."
          aria-label="Search schema"
          disabled={isLoading && schema.length === 0}
          onChange={(event) => handleFilterChange(event.target.value)}
          addonBefore={
            showCategorySelect ? (
              <Select
                classNames={{ popup: { root: "api-schema-browser-category-dropdown" } }}
                disabled={isLoading && schema.length === 0}
                value={selectedCategory}
                onChange={handleCategoryChange}
                showSearch
                onSearch={handleCategoryFilterChange}
                onOpenChange={setIsCategorySelectOpen}
                dropdownMatchSelectWidth={false}
                placeholder={
                  <>
                    <i className="fa fa-folder-open-o m-r-5" aria-hidden="true" />
                    Category
                  </>
                }>
                {filteredCategories.map((category) => (
                  <Select.Option key={category} value={category}>
                    {formatCategoryLabel(category)}
                  </Select.Option>
                ))}
              </Select>
            ) : null
          }
        />
      </div>
      <div className="schema-list-wrapper">
        <SchemaList
          loading={isLoading && schema.length === 0}
          schema={filteredSchema}
          expandedFlags={expandedFlags}
          onTableExpand={toggleTable}
          onItemSelect={onItemSelect}
        />
        {!(isLoading && schema.length === 0) && (
          <div className="load-button">
            <Tooltip title={!refreshing ? "Refresh schema" : null}>
              <Button type="link" onClick={handleRefresh} disabled={refreshing || isLoading}>
                <SyncOutlinedIcon spin={refreshing || isLoading} />
              </Button>
            </Tooltip>
          </div>
        )}
      </div>
    </div>
  );
}

ApiSchemaBrowser.propTypes = {
  dataSource: PropTypes.object, // eslint-disable-line react/forbid-prop-types
  options: PropTypes.object, // eslint-disable-line react/forbid-prop-types
  onOptionsUpdate: PropTypes.func,
  onSchemaUpdate: PropTypes.func,
  onItemSelect: PropTypes.func,
};

ApiSchemaBrowser.defaultProps = {
  dataSource: null,
  options: null,
  onOptionsUpdate: () => {},
  onSchemaUpdate: () => {},
  onItemSelect: () => {},
};
