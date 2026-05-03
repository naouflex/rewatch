import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import TimeAgo from "@/components/TimeAgo";
import Paginator from "@/components/Paginator";
import Link from "@/components/Link";
import Tooltip from "@/components/Tooltip";
import ItemsTable, { Columns } from "@/components/items-list/components/ItemsTable";
import LoadingState from "@/components/items-list/components/LoadingState";
import * as Grid from "antd/lib/grid";
import JsonViewInteractive from "@/components/json-view-interactive/JsonViewInteractive";
import { PredictionsTagsControl } from "@/components/tags-control/TagsControl";
import Button from "antd/lib/button";
import { useTheme } from "@/components/ThemeProvider";
import "./MLModelPredictions.less";

// Add this helper function at the top of the file, after the imports
const formatDate = (date) => {
  if (!date) return 'N/A';
  return new Intl.DateTimeFormat('en-GB', {
    year: '2-digit', 
    month: '2-digit', 
    day: '2-digit', 
    hour: '2-digit', 
    minute: '2-digit'
  }).format(new Date(date)).replace(/,/g, '');
};

const columns = [
  Columns.custom.sortable(
    (text, prediction) => (
      <div>
        <Link className="table-main-title" href={"predictions/" + prediction.id}>{prediction.id}</Link>
        <PredictionsTagsControl className="d-block" tags={prediction.tags || []} />
      </div>
    ),
    {
      title: "ID",
      field: "id",
      width: "1%",
    }
  ),
  Columns.custom.sortable(
    (text, prediction) => (
      <div>
        <Tooltip title={<div align="center">{formatDate(prediction.created_at)}<br/><TimeAgo date={prediction.created_at} /></div>}>
          {formatDate(prediction.created_at)}
        </Tooltip>
      </div>
    ),
    {
      title: "Date", 
      field: "created_at", 
      width: "10%" 
    }
  ),
  Columns.custom.sortable(
    (text, prediction) => prediction.model_version,
    { title: "Model Version", field: "model_version", width: "10%" }
  ),
  Columns.custom.sortable(
    (text, prediction) => (
      <div className="json-cell">
        {typeof prediction.content === "object" ? (
          <JsonViewInteractive value={prediction.content || {}} />
        ) : (
          <pre>{String(prediction.content || '')}</pre>
        )}
      </div>
    ),
    { title: "Content", field: "content", width: "30%" }
  ),
  Columns.custom.sortable(
    (text, prediction) => (
      <div className="json-cell">
        {typeof prediction.additional_properties === "object" ? (
          <JsonViewInteractive value={prediction.additional_properties || {}} />
        ) : (
          <pre>{String(prediction.additional_properties || '')}</pre>
        )}
      </div>
    ),
    { title: "Additional Properties", field: "additional_properties", width: "30%" }
  ),
  Columns.custom.sortable(
    (text, prediction) => (
      <div>
        <Button type="primary" size="small" href={"predictions/" + prediction.id} style={{ marginTop: "5px" }}>
          Go to Prediction
        </Button>
      </div>
    ),
    {
      title: "Actions",
      field: "actions",
      width: "1%",
    }
  ),
];

function MLModelPredictions({ predictions }) {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [loading, setLoading] = useState(true);
  const [sortedPredictions, setSortedPredictions] = useState([]);
  const [orderByField, setOrderByField] = useState(null);
  const [orderByReverse, setOrderByReverse] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const { isDarkMode } = useTheme();

  useEffect(() => {
    if (predictions === null || predictions === undefined) {
      setLoading(true);
      setSortedPredictions([]);
    } else {
      setSortedPredictions(predictions);
      setLoading(false);
    }
  }, [predictions]);

  const toggleSorting = (field) => {
    const isReverse = orderByField === field ? !orderByReverse : false;
    setOrderByField(field);
    setOrderByReverse(isReverse);

    const sorted = [...predictions].sort((a, b) => {
      const getValue = (obj, path) => path.split('.').reduce((o, p) => (o ? o[p] : undefined), obj);

      const aValue = getValue(a, field);
      const bValue = getValue(b, field);

      const isDateField = field === 'created_at';
      const aValueProcessed = isDateField ? new Date(aValue) : aValue;
      const bValueProcessed = isDateField ? new Date(bValue) : bValue;

      if (aValueProcessed < bValueProcessed) return isReverse ? 1 : -1;
      if (aValueProcessed > bValueProcessed) return isReverse ? -1 : 1;
      return 0;
    });

    setSortedPredictions(sorted);
  };

  const filteredPredictions = sortedPredictions.filter(prediction =>
    Object.values(prediction).some(value => {
      const stringValue = value !== null && value !== undefined ? String(value) : "";
      return stringValue.toLowerCase().includes(searchTerm.toLowerCase());
    })
  );
  const currentItems = filteredPredictions.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  if (loading) {
    return <LoadingState className="m-t-30" />;
  }

  if (sortedPredictions.length === 0) {
    return <div className="text-center">No predictions available.</div>;
  }

  return (
    <div className={`model-predictions ${isDarkMode ? 'dark-mode' : ''}`}>
      <h3 className={`model-predictions-title ${isDarkMode ? 'dark-mode' : ''}`}>Model Predictions</h3>
      <div className={`bg-white tiled p-20 ${isDarkMode ? 'dark-mode' : ''}`}>
        <input
          type="text"
          placeholder="Search..."
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          className={`search-input ${isDarkMode ? 'dark-mode' : ''}`}
          style={{ marginBottom: "20px", padding: "10px", width: "100%", borderRadius: "2px" }}
        />
        <Grid.Row gutter={16}>
          <Grid.Col xs={24}>
            <div className={`bg-white tiled table-responsive ${isDarkMode ? 'dark-mode' : ''}`}>
              <ItemsTable
                items={currentItems}
                columns={columns}
                orderByField={orderByField}
                orderByReverse={orderByReverse}
                toggleSorting={toggleSorting}
                className={isDarkMode ? 'dark-mode' : ''}
              />
              <Paginator
                showPageSizeSelect
                totalCount={filteredPredictions.length}
                pageSize={pageSize}
                onPageSizeChange={setPageSize}
                page={currentPage}
                onChange={setCurrentPage}
                className={isDarkMode ? 'dark-mode' : ''}
              />
            </div>
          </Grid.Col>
        </Grid.Row>
      </div>
    </div>
  );
}

MLModelPredictions.propTypes = {
  predictions: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      created_at: PropTypes.string.isRequired,
      model_version: PropTypes.number.isRequired,
      content: PropTypes.oneOfType([PropTypes.object, PropTypes.string]).isRequired,
      additional_properties: PropTypes.oneOfType([PropTypes.object, PropTypes.string]).isRequired,
      tags: PropTypes.arrayOf(PropTypes.string),
      model: PropTypes.shape({
        id: PropTypes.string.isRequired,
        name: PropTypes.string.isRequired
      }),
      query: PropTypes.shape({
        id: PropTypes.string.isRequired,
        name: PropTypes.string.isRequired
      }),
      user: PropTypes.shape({
        id: PropTypes.number.isRequired,
        name: PropTypes.string.isRequired
      })
    })
  ),
};

MLModelPredictions.defaultProps = {
  predictions: [],
};

export default MLModelPredictions;
