import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { find, sortBy } from "lodash";

import Select from "antd/lib/select";
import DataSource, { getDataSourceIconUrl } from "@/services/data-source";

const SUPPORTED_TYPES = new Set([
  "pg",
  "postgresql",
  "postgres",
  "mysql",
  "mariadb",
  "mssql",
  "redshift",
  "clickhouse",
  "snowflake",
  "sqlite",
  "trino",
  "presto",
]);

export default function IndexerDestination({ value, onChange, viewMode, disabled }) {
  const [dataSources, setDataSources] = useState([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    DataSource.query()
      .then(items => {
        if (cancelled) return;
        const compatible = items.filter(ds => SUPPORTED_TYPES.has(ds.type));
        setDataSources(sortBy(compatible, ds => ds.name.toLowerCase()));
      })
      .finally(() => {
        if (!cancelled) setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selected = find(dataSources, ds => ds.id === value);

  if (viewMode) {
    if (!selected) return <div className="text-muted">{value ? `Data source #${value}` : "Not set"}</div>;
    return (
      <div className="indexer-destination-view">
        <img
          src={getDataSourceIconUrl(selected)}
          alt={selected.type}
          style={{ width: 16, height: 16, marginRight: 6 }}
        />
        {selected.name}
      </div>
    );
  }

  return (
    <Select
      style={{ minWidth: 320 }}
      placeholder={loaded ? "Pick a target data source" : "Loading…"}
      value={selected ? selected.id : undefined}
      loading={!loaded}
      disabled={disabled || !loaded}
      onChange={onChange}
      allowClear>
      {dataSources.map(ds => (
        <Select.Option key={ds.id} value={ds.id}>
          <img
            src={getDataSourceIconUrl(ds)}
            alt={ds.type}
            style={{ width: 16, height: 16, marginRight: 6 }}
          />
          {ds.name}
        </Select.Option>
      ))}
    </Select>
  );
}

IndexerDestination.propTypes = {
  value: PropTypes.number,
  onChange: PropTypes.func,
  viewMode: PropTypes.bool,
  disabled: PropTypes.bool,
};

IndexerDestination.defaultProps = {
  value: null,
  onChange: () => {},
  viewMode: false,
  disabled: false,
};
