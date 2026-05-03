import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import Select from "antd/lib/select";
import Input from "antd/lib/input";
import Checkbox from "antd/lib/checkbox";
import * as Grid from "antd/lib/grid";
import "./RegressorSelect.css";

const { Option } = Select;

const REGRESSORS = [
  { value: "Regression", label: "Regression (Linear/Logistic)" },
  { value: "RandomForest", label: "Random Forest" },
  { value: "AdaBoost", label: "AdaBoost" },
  { value: "GradientBoosting", label: "Gradient Boosting" },
  { value: "NeuralNetwork", label: "Neural Network" },
];

// Define specific options for each regressor
const REGRESSOR_OPTIONS = {
  Regression: [
    { type: "checkbox", label: "Auto Mode", key: "auto_mode" },
    { type: "checkbox", label: "Fit Intercept", key: "fit_intercept" },
    { type: "input", label: "C", key: "C" },
    { type: "dropdown", label: "Penalty", key: "penalty", options: ["l2"] },
    { type: "dropdown", label: "Solver", key: "solver", options: ["lbfgs", "newton-cg"] },
    { type: "input", label: "Max Iterations", key: "max_iter" },
    { type: "input", label: "Tolerance", key: "tol" },
  ],
  RandomForest: [
    { type: "checkbox", label: "Auto Mode", key: "auto_mode" },
    { type: "input", label: "Number of Trees", key: "n_estimators" },
    { type: "input", label: "Max Depth", key: "max_depth" },
    { type: "input", label: "Min Samples Split", key: "min_samples_split" },
    { type: "input", label: "Min Samples Leaf", key: "min_samples_leaf" },
    { type: "dropdown", label: "Criterion (Regression)", key: "criterion_regression", options: ["squared_error", "absolute_error", "friedman_mse"] },
    { type: "dropdown", label: "Criterion (Classification)", key: "criterion_classification", options: ["gini", "entropy"] },
    { type: "dropdown", label: "Class Weight", key: "class_weight", options: ["balanced_subsample"] },
  ],
  AdaBoost: [
    { type: "checkbox", label: "Auto Mode", key: "auto_mode" },
    { type: "input", label: "Number of Estimators", key: "n_estimators" },
    { type: "input", label: "Learning Rate", key: "learning_rate" },
    { type: "dropdown", label: "Loss", key: "loss", options: ["linear", "square", "exponential"] },
  ],

  GradientBoosting: [
    { type: "checkbox", label: "Auto Mode", key: "auto_mode" },
    { type: "input", label: "Number of Estimators", key: "n_estimators" },
    { type: "input", label: "Learning Rate", key: "learning_rate" },
    { type: "input", label: "Max Depth", key: "max_depth" },
    { type: "input", label: "Min Samples Split", key: "min_samples_split" },
    { type: "input", label: "Min Samples Leaf", key: "min_samples_leaf" },
    { type: "dropdown", label: "Loss (Regression)", key: "loss_regression", options: ["squared_error", "absolute_error", "huber", "quantile"] },
    { type: "dropdown", label: "Loss (Classification)", key: "loss_classification", options: ["log_loss", "exponential"] },
  ],
  NeuralNetwork: [
    { type: "checkbox", label: "Auto Mode", key: "auto_mode" },
    { type: "input", label: "Epochs", key: "epochs" },
    { type: "dropdown", label: "Batch Size", key: "batch_size", options: ["16", "32", "64"] },
    { type: "dropdown", label: "Units 1", key: "units1", options: ["32", "64", "128"] },
    { type: "dropdown", label: "Units 2", key: "units2", options: ["16", "32", "64"] },
    { type: "dropdown", label: "Dropout Rate", key: "dropout_rate", options: ["0.1", "0.2", "0.3"] },
    { type: "dropdown", label: "L2 Regularization", key: "l2_reg", options: ["0.001", "0.01", "0.1"] },
    { type: "dropdown", label: "Optimizer", key: "optimizer", options: ["adam", "rmsprop"] },
    { type: "dropdown", label: "Learning Rate", key: "learning_rate", options: ["0.001", "0.01", "0.1"] },
  ],
};

const RegressorSelect = ({ value, onRegressorChange, onRegressorOptionsChange, modelOptions, editMode }) => {
  const [selectedOptions, setSelectedOptions] = useState(modelOptions.regressor_options || {});
  const [isClassification, setIsClassification] = useState(false);

  useEffect(() => {
    setSelectedOptions(modelOptions.regressor_options || {});
    // Determine if it's a classification task based on the target types
    const targetTypes = JSON.parse(modelOptions.target_types || '{}');
    setIsClassification(Object.values(targetTypes).every(type => type === 'categorical'));
  }, [modelOptions]);

  const handleOptionChange = (key, optionValue) => {
    const newOptions = { ...selectedOptions, [key]: optionValue };
    setSelectedOptions(newOptions);
    onRegressorOptionsChange(newOptions);
  };

  const handleRegressorChange = (newValue) => {
    onRegressorChange(newValue);
    const newOptions = REGRESSOR_OPTIONS[newValue]?.reduce((acc, option) => {
      acc[option.key] = option.default || null;
      return acc;
    }, {}) || {};
    setSelectedOptions(newOptions);
    onRegressorOptionsChange(newOptions);
  };

  const renderOptions = () => {
    if (!value || !REGRESSOR_OPTIONS[value]) {
      return null;
    }

    const autoMode = selectedOptions.auto_mode || false;

    return (
      <Grid.Row gutter={[16, 16]} className="regressor-options">
        {REGRESSOR_OPTIONS[value].map((option) => {
          if (option.key === "auto_mode") {
            return (
              <Grid.Col xs={24} md={12} key={option.key} className="regressor-option">
                <Checkbox
                  checked={selectedOptions[option.key] || false}
                  onChange={(e) => handleOptionChange(option.key, e.target.checked)}
                  disabled={!editMode}
                  style={{ opacity: !editMode ? 0.5 : 1 }}
                >
                  {option.label}
                </Checkbox>
              </Grid.Col>
            );
          }

          if (autoMode && option.key !== "auto_mode") {
            return null; // Don't render other options when auto mode is enabled
          }

          if (option.type === "checkbox") {
            return (
              <Grid.Col xs={24} md={12} key={option.key} className="regressor-option">
                <Checkbox
                  checked={selectedOptions[option.key] || false}
                  onChange={(e) => handleOptionChange(option.key, e.target.checked)}
                  disabled={!editMode}
                  style={{ opacity: !editMode ? 0.5 : 1 }}
                >
                  {option.label}
                </Checkbox>
              </Grid.Col>
            );
          }

          if (option.type === "dropdown") {
            return (
              <Grid.Col xs={24} md={12} key={option.key} className="regressor-option">
                <label>{option.label}</label>
                <Select
                  value={selectedOptions[option.key]}
                  onChange={(value) => handleOptionChange(option.key, value)}
                  className="ant-input"
                  disabled={!editMode}
                  style={{ opacity: !editMode ? 0.5 : 1 }}
                >
                  {option.options.map((opt) => (
                    <Option key={opt} value={opt}>
                      {opt}
                    </Option>
                  ))}
                </Select>
              </Grid.Col>
            );
          }

          if (option.type === "input") {
            return (
              <Grid.Col xs={24} md={12} key={option.key} className="regressor-option">
                <label>{option.label}</label>
                <Input
                  value={selectedOptions[option.key] || ""}
                  onChange={(e) => handleOptionChange(option.key, e.target.value)}
                  className="ant-input"
                  disabled={!editMode}
                  style={{ opacity: !editMode ? 0.5 : 1 }}
                  type="number"
                />
              </Grid.Col>
            );
          }

          return null;
        })}
      </Grid.Row>
    );
  };

  return (
    <div className="regressor-select">
      {editMode ? (
        <>
          <Select
            value={value}
            onChange={handleRegressorChange}
            className="ant-input"
            placeholder="Select a regressor algorithm"
            disabled={!editMode}
            style={{ opacity: !editMode ? 0.5 : 1 }}
          >
            {REGRESSORS.map((option) => (
              <Option key={option.value} value={option.value}>
                {option.label}
              </Option>
            ))}
          </Select>
          {renderOptions()}
        </>
      ) : (
        <>
          {REGRESSORS.find((r) => r.value === value)?.label || value}
        </>
      )}
    </div>
  );
};

RegressorSelect.propTypes = {
  value: PropTypes.string.isRequired,
  onRegressorChange: PropTypes.func.isRequired,
  onRegressorOptionsChange: PropTypes.func,
  modelOptions: PropTypes.shape({
    regressor_options: PropTypes.object
  }).isRequired,
  editMode: PropTypes.bool.isRequired,
};

RegressorSelect.defaultProps = {
  onRegressorOptionsChange: () => {},
};

export default RegressorSelect;
