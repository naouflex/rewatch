import React, { useState, useMemo, useEffect } from "react";
import PropTypes from "prop-types";
import Select from "antd/lib/select";
import Alert from "antd/lib/alert";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import Card from "antd/lib/card";
import Row from "antd/lib/row";
import Col from "antd/lib/col";
import Table from "antd/lib/table";
import LoadingState from "@/components/items-list/components/LoadingState";
import { useTheme } from "@/components/ThemeProvider";
import "./MLModelMetricsHistoryTrain.less";

const MLModelMetricsHistoryTrain = ({ versions }) => {
  const { isDarkMode } = useTheme();
  const [selectedColumn, setSelectedColumn] = useState(null);
  const [selectedMetric, setSelectedMetric] = useState(null);

  const columnOptions = useMemo(() => {
    if (!versions || versions.length === 0) return [];

    const allColumns = new Set();
    versions.forEach(version => {
      if (version.metrics && typeof version.metrics === 'object') {
        Object.keys(version.metrics).forEach(key => allColumns.add(key));
      }
    });
    return Array.from(allColumns).map(column => ({ value: column, label: column }));
  }, [versions]);

  const metricOptions = useMemo(() => {
    if (!selectedColumn || !versions || versions.length === 0) return [];

    const allMetrics = new Set();
    versions.forEach(version => {
      if (version.metrics && 
          version.metrics[selectedColumn] && 
          typeof version.metrics[selectedColumn] === 'object') {
        Object.keys(version.metrics[selectedColumn]).forEach(key => allMetrics.add(key));
      }
    });
    return Array.from(allMetrics).map(metric => ({ value: metric, label: metric }));
  }, [versions, selectedColumn]);

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

    const data = versions
      .filter(version => {
        if (selectedColumn === 'metrics') {
          return version.metrics && version.metrics[selectedMetric] !== undefined;
        } else {
          return version.metrics && 
                 version.metrics[selectedColumn] && 
                 version.metrics[selectedColumn][selectedMetric] !== undefined;
        }
      })
      .map(version => ({
        date: new Date(version.created_at).toLocaleString(),
        value: selectedColumn === 'metrics' ? version.metrics[selectedMetric] : version.metrics[selectedColumn][selectedMetric],
        regressor: version.options?.regressor,
        regressorOptions: version.options?.regressor_options,
      }))
      .sort((a, b) => new Date(a.date) - new Date(b.date));

    return data;
  }, [versions, selectedColumn, selectedMetric]);

  const isChartable = useMemo(() => {
    return chartData.length > 0 && typeof chartData[0].value === 'number';
  }, [chartData]);

  const handleColumnChange = (value) => {
    setSelectedColumn(value);
    setSelectedMetric(null);
  };

  const handleMetricChange = (value) => {
    setSelectedMetric(value);
  };

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const { value, regressor, regressorOptions } = payload[0].payload;
      return (
        <div className="custom-tooltip">
          <p className="label">{`Date: ${label}`}</p>
          <p className="intro">{`Value: ${value}`}</p>
          {regressor && <p className="intro">{`Regressor: ${regressor}`}</p>}
          {regressorOptions && (
            <div className="intro">
              <p>Regressor Options:</p>
              <Table
                dataSource={Object.entries(regressorOptions).map(([key, val]) => ({ key, val: JSON.stringify(val) }))}
                columns={[
                  { title: 'Option', dataIndex: 'key', key: 'key' },
                  { title: 'Value', dataIndex: 'val', key: 'val' },
                ]}
                pagination={false}
                size="small"
              />
            </div>
          )}
        </div>
      );
    }
    return null;
  };

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

    return (
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis domain={[0, 1]} />
          <Tooltip content={<CustomTooltip />} />
          <Line type="monotone" dataKey="value" stroke="#8884d8" activeDot={{ r: 8 }} />
        </LineChart>
      </ResponsiveContainer>
    );
  };

  if (!versions) {
    return <LoadingState className="m-t-30" />;
  }

  if (versions.length === 0) {
    return <div className="text-center">No versions available.</div>;
  }

  return (
    <div className={`ml-model-metrics-history ${isDarkMode ? 'dark-mode' : ''}`}>
      <h3>Training Metrics History</h3>
      <Card className="ml-model-metrics-history-card">
        <Row gutter={[16, 16]}>
          <Col xs={24}>
            <Select
              style={{ width: 200, marginRight: 10, marginBottom: 20 }}
              placeholder="Select a column"
              onChange={handleColumnChange}
              value={selectedColumn}
              options={columnOptions}
            />
            <Select
              style={{ width: 200, marginBottom: 20 }}
              placeholder="Select a metric"
              onChange={handleMetricChange}
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

MLModelMetricsHistoryTrain.propTypes = {
  versions: PropTypes.arrayOf(
    PropTypes.shape({
      created_at: PropTypes.string.isRequired,
      metrics: PropTypes.object,
      options: PropTypes.object,
    })
  ),
};

MLModelMetricsHistoryTrain.defaultProps = {
  versions: [],
};

export default MLModelMetricsHistoryTrain;