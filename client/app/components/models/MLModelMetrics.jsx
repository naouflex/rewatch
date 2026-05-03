import React from "react";
import PropTypes from "prop-types";
import Card from "antd/lib/card";
import Row from "antd/lib/row";
import Col from "antd/lib/col";
import { useTheme } from "@/components/ThemeProvider";
import "./MLModelMetrics.less";

const MLModelMetricsHeader = ({ metrics }) => {
  const { isDarkMode } = useTheme();

  const formatMetricName = (name) => {
    return name.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
  };

  const formatMetricValue = (value) => {
    if (typeof value === "boolean") {
      return value ? "Yes" : "No";
    }
    if (typeof value === "number") {
      if (Math.abs(value) < 0.01 || Math.abs(value) > 999999) {
        return value.toExponential(2);
      }
      return value.toFixed(4);
    }
    return value;
  };

  const getQualificationColor = (metricName, value) => {
    const colors = ['#ff4d4f', '#ffa39e', '#ffd666', '#95de64', '#52c41a'];
    let thresholds;

    switch (metricName) {
      case 'accuracy':
      case 'precision':
      case 'recall':
      case 'f1_score':
      case 'r2_score':
        thresholds = [0.2, 0.4, 0.6, 0.8];
        break;
      case 'mean_absolute_error':
      case 'mean_squared_error':
        thresholds = [0.4, 0.3, 0.2, 0.1];
        return colors[thresholds.findIndex(t => value <= t) + 1] || colors[0];
      default:
        return 'var(--text-color)';
    }

    return colors[thresholds.findIndex(t => value <= t)] || colors[4];
  };

  const renderMetrics = (metricsObj, columnName) => {
    return (
      <ul style={{ paddingLeft: '20px', marginBottom: '0' }}>
        {Object.entries(metricsObj).map(([key, value]) => {
          const formattedValue = formatMetricValue(value);
          const color = typeof value === "boolean" ? 'var(--text-color)' : getQualificationColor(key, value);
          return (
            <li key={`${columnName}-${key}`}>
              <span>{formatMetricName(key)}: </span>
              <span style={{ color, fontWeight: 'bold' }}>{formattedValue}</span>
            </li>
          );
        })}
      </ul>
    );
  };

  const getCardColor = (metricsObj) => {
    const primaryMetric = metricsObj.r2_score || metricsObj.accuracy || metricsObj.f1_score;
    if (primaryMetric && typeof primaryMetric === 'number') {
      return getQualificationColor('r2_score', primaryMetric);
    }
    return 'var(--card-background-color)';
  };

  // Remove the filter for 'overall' metrics
  const columnMetrics = Object.entries(metrics);
  
  return (
    <div className={`ml-model-metrics-header ${isDarkMode ? 'dark-mode' : ''}`}>
      <h3>Model Metrics</h3>
      <Row gutter={[16, 16]} align="stretch">
        {columnMetrics.map(([columnName, columnMetrics]) => (
          <Col xs={24} sm={12} md={8} lg={6} key={columnName} style={{ display: 'flex' }}>
            <Card 
              title={formatMetricName(columnName)}
              headStyle={{ 
                backgroundColor: getCardColor(columnMetrics),
                color: isDarkMode ? '#ffffff' : '#000000'
              }}
              style={{ width: '100%' }}
            >
              {renderMetrics(columnMetrics, columnName)}
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
};

MLModelMetricsHeader.propTypes = {
  metrics: PropTypes.object.isRequired,
};

export default MLModelMetricsHeader;