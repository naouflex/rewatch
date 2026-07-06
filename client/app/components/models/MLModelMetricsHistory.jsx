import React, { useState, useMemo, useEffect } from "react";
import PropTypes from "prop-types";
import Select from "antd/lib/select";
import Alert from "antd/lib/alert";
import Card from "antd/lib/card";
import Row from "antd/lib/row";
import Col from "antd/lib/col";
import LoadingState from "@/components/items-list/components/LoadingState";
import { useTheme } from "@/components/ThemeProvider";
import EChartsLineChart from "./EChartsLineChart";
import "./MLModelMetricsHistory.less";

const MLModelMetricsHistory = ({ predictions }) => {
  const { isDarkMode } = useTheme();
  const [selectedColumn, setSelectedColumn] = useState(null);
  const [selectedMetric, setSelectedMetric] = useState(null);

  const columnOptions = useMemo(() => {
    if (!predictions || predictions.length === 0) return [];

    const allColumns = new Set();
    predictions.forEach(prediction => {
      if (prediction.additional_properties && typeof prediction.additional_properties === "object") {
        Object.keys(prediction.additional_properties).forEach(key => allColumns.add(key));
      }
    });
    return Array.from(allColumns).map(column => ({ value: column, label: column }));
  }, [predictions]);

  const metricOptions = useMemo(() => {
    if (!selectedColumn || !predictions || predictions.length === 0) return [];

    const allMetrics = new Set();
    predictions.forEach(prediction => {
      if (
        prediction.additional_properties &&
        prediction.additional_properties[selectedColumn] &&
        typeof prediction.additional_properties[selectedColumn] === "object"
      ) {
        Object.keys(prediction.additional_properties[selectedColumn]).forEach(key => allMetrics.add(key));
      }
    });
    return Array.from(allMetrics).map(metric => ({ value: metric, label: metric }));
  }, [predictions, selectedColumn]);

  useEffect(() => {
    if (columnOptions.length > 0 && !selectedColumn) {
      setSelectedColumn(columnOptions[0].value);
    }
  }, [columnOptions, selectedColumn]);

  useEffect(() => {
    if (metricOptions.length > 0 && !selectedMetric) {
      setSelectedMetric(metricOptions[0].value);
    }
  }, [metricOptions, selectedMetric]);

  const chartData = useMemo(() => {
    if (!selectedColumn || !selectedMetric) return [];

    return predictions
      .filter(prediction => {
        if (selectedColumn === "additional_properties") {
          return prediction.additional_properties && prediction.additional_properties[selectedMetric] !== undefined;
        }
        return (
          prediction.additional_properties &&
          prediction.additional_properties[selectedColumn] &&
          prediction.additional_properties[selectedColumn][selectedMetric] !== undefined
        );
      })
      .map(prediction => ({
        date: new Date(prediction.created_at).toLocaleString(),
        value:
          selectedColumn === "additional_properties"
            ? prediction.additional_properties[selectedMetric]
            : prediction.additional_properties[selectedColumn][selectedMetric],
      }))
      .sort((a, b) => new Date(a.date) - new Date(b.date));
  }, [predictions, selectedColumn, selectedMetric]);

  const isChartable = useMemo(() => {
    return chartData.length > 0 && typeof chartData[0].value === "number";
  }, [chartData]);

  const renderContent = () => {
    if (!selectedColumn || !selectedMetric) {
      return <Alert message="Please select a column and a metric to view its history." type="info" />;
    }
    if (chartData.length === 0) {
      return <Alert message="No data available for the selected metric." type="warning" />;
    }
    if (!isChartable) {
      return (
        <Alert
          message="The selected metric cannot be represented as a chart."
          description="It may contain invalid data."
          type="error"
        />
      );
    }
    return <EChartsLineChart data={chartData} height={300} />;
  };

  if (!predictions) {
    return <LoadingState className="m-t-30" />;
  }

  if (predictions.length === 0) {
    return <div className="text-center">No predictions available.</div>;
  }

  return (
    <div className={`ml-model-metrics-history ${isDarkMode ? "dark-mode" : ""}`}>
      <h3>Prediction Metrics History</h3>
      <Card className="ml-model-metrics-history-card">
        <Row gutter={[16, 16]}>
          <Col xs={24}>
            <Select
              style={{ width: 200, marginRight: 10, marginBottom: 20 }}
              placeholder="Select a column"
              onChange={value => {
                setSelectedColumn(value);
                setSelectedMetric(null);
              }}
              value={selectedColumn}
              options={columnOptions}
            />
            <Select
              style={{ width: 200, marginBottom: 20 }}
              placeholder="Select a metric"
              onChange={setSelectedMetric}
              value={selectedMetric}
              options={metricOptions}
              disabled={!selectedColumn}
            />
            {renderContent()}
          </Col>
        </Row>
      </Card>
    </div>
  );
};

MLModelMetricsHistory.propTypes = {
  predictions: PropTypes.arrayOf(
    PropTypes.shape({
      created_at: PropTypes.string.isRequired,
      additional_properties: PropTypes.object,
    })
  ),
};

MLModelMetricsHistory.defaultProps = {
  predictions: [],
};

export default MLModelMetricsHistory;
