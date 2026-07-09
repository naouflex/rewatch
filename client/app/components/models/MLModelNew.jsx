import React from "react";
import PropTypes from "prop-types";
import Form from "antd/lib/form";
import Button from "antd/lib/button";
import HelpTrigger from "@/components/HelpTrigger";
import CreatePageLayout from "@/components/items-list/CreatePageLayout";
import { MLModel as ModelType } from "@/components/proptypes";
import Title from "./Title";
import Criteria from "./Criteria";
import NotificationTemplate from "./NotificationTemplate";
import Rearm from "./Rearm";
import Query from "./Query";
import HorizontalFormItem from "../HorizontalFormItem";
import RegressorSelect from "./RegressorSelect";
import TrainTestSplitSlider from "./TrainTestSplitSlider";
import ConfigSection from "@/components/ConfigSection/ConfigSection";
import "@/components/ConfigSection/ConfigSection.less";

import DynamicComponent from "@/components/DynamicComponent";

export default class ModelNew extends React.Component {
  _isMounted = false;
  state = {
    saving: false,
  };

  componentDidMount() {
    this._isMounted = true;
  }

  componentWillUnmount() {
    this._isMounted = false;
  }

  save = () => {
    this.setState({ saving: true });
    this.props.save().catch(() => {
      this.setState({ saving: false });
    });
  };

  handleTrainSizeChange = (trainSize) => {
    this.props.onTrainSizeChange(trainSize);
  };

  handleRegressorChange = (regressor) => {
    this.props.onRegressorChange(regressor);
  };

  handleRegressorOptionsChange = (regressor_options) => {
    this.props.onRegressorOptionsChange(regressor_options);
  };

  handleVersionChange = (version) => {
    this.props.onVersionChange(version);
  };

  handleRandomStateChange = (random_state) => {
    this.props.onRandomStateChange(random_state);
  };

  render() {
    const {
      model,
      queryResult,
      onNotificationTemplateChange,
      onQuerySelected,
      onNameChange,
      onRearmTrainChange,
      onRearmPredictChange,
      onTrainCriteriaChange,
      onPredictCriteriaChange,
      onDescriptionChange,
      onVersionChange,
      onRegressorChange,
      onRegressorOptionsChange,
      onRandomStateChange,
      onFeatureChange,
      onTimestampChange,
      onCategoryChange,
      onTargetChange,
      menuButton,
    } = this.props;

    const { query, name, description, version, options } = model;
    const { saving } = this.state;
    const { train_template } = options;

    return (
      <>
        <CreatePageLayout backHref="ml_models" backLabel="Back to Models" />
        <div className="create-page-form__header">
          <Title name={name} model={model} onChange={onNameChange} editMode>
            <DynamicComponent name="ModelNew.HeaderExtra" model={model} />
            <Button type="primary" onClick={this.save} disabled={!query}>
              {saving && (
                <span role="status" aria-live="polite" aria-relevant="additions removals">
                  <i className="fa fa-spinner fa-pulse m-r-5" aria-hidden="true" />
                  <span className="sr-only">Saving...</span>
                </span>
              )}
              Create Model
            </Button>
            {menuButton}
          </Title>
        </div>
        <div className="create-page-form__body">
          <p className="create-page-form__intro">
            Select the query you want to use for training and predictions. Models do not work with queries that use
            parameters.
          </p>
          <ConfigSection title="Query & data">
            <Form className="flex-fill">
              <HorizontalFormItem label="Query">
                <Query
                  query={query}
                  queryResult={queryResult}
                  onChange={onQuerySelected}
                  onFeatureChange={onFeatureChange}
                  onTimestampChange={onTimestampChange}
                  onCategoryChange={onCategoryChange}
                  onTargetChange={onTargetChange}
                  modelOptions={options}
                  editMode

                />
              </HorizontalFormItem>
              <HorizontalFormItem label="Description">
                <Form.Item>
                  <textarea
                    value={description}
                    onChange={e => onDescriptionChange(e.target.value)}
                    className="ant-input"
                    placeholder="Enter a description for the model"
                  />
                </Form.Item>
              </HorizontalFormItem>
              <HorizontalFormItem label="Version">
                <Form.Item>
                  <input
                    type="number"
                    value={version}
                    onChange={e => onVersionChange(e.target.value)}
                    className="ant-input"
                    placeholder="Version will automatically increment"
                    disabled={true}
                  />
                </Form.Item>
              </HorizontalFormItem>
              <HorizontalFormItem label="Regressor">
                <Form.Item>
                  <RegressorSelect
                    value={options.regressor}
                    onRegressorChange={onRegressorChange}
                    onRegressorOptionsChange={onRegressorOptionsChange}
                    modelOptions={options}
                    editMode
                  />
                </Form.Item>
              </HorizontalFormItem>
              <HorizontalFormItem label="Train / Test Split">
                <TrainTestSplitSlider
                  trainSize={options.train_size}
                  onTrainSizeChange={this.handleTrainSizeChange}
                  editMode
                  timestampData={queryResult && queryResult.getColumnNames().includes("timestamp") ? {
                    dates: queryResult.getData().map(row => row["timestamp"]),
                    column: "timestamp"
                  } : null}
                />
              </HorizontalFormItem>
              <HorizontalFormItem label="Random State">
                <Form.Item>
                  <input
                    type="number"
                    value={options.random_state}
                    onChange={e => onRandomStateChange(e.target.value)}
                    className="ant-input"
                    placeholder="Enter the random state"
                  />
                </Form.Item>
              </HorizontalFormItem>
            </Form>
            <div className="m-t-10">
              <HelpTrigger className="f-13" type="MODEL_SETUP">
                Setup Instructions <i className="fa fa-question-circle" aria-hidden="true" />
                <span className="sr-only">(help)</span>
              </HelpTrigger>
            </div>
          </ConfigSection>

          {queryResult && options && (
            <>
              <ConfigSection title="Training">
                <Form>
                  <HorizontalFormItem label="Retrain when" className="model-criteria">
                    <Criteria
                      columnNames={queryResult.getColumnNames()}
                      resultValues={queryResult.getData()}
                      modelOptions={options}
                      onChange={onTrainCriteriaChange}
                      criteriaType={"train"}
                      editMode
                    />
                  </HorizontalFormItem>
                  <HorizontalFormItem label="When trained, send notification">
                    <Rearm
                      modelOptions={options}
                      onChange={onRearmTrainChange}
                      rearmType="train"
                      editMode
                    />
                  </HorizontalFormItem>
                  <HorizontalFormItem label="Train Template">
                    <NotificationTemplate
                      model={model}
                      query={query}
                      columnNames={queryResult.getColumnNames()}
                      resultValues={queryResult.getData()}
                      subject={train_template?.custom_subject}
                      body={train_template?.custom_body}
                      setSubject={subject => onNotificationTemplateChange({ custom_subject: subject })}
                      setBody={body => onNotificationTemplateChange({ custom_body: body })}
                      templateType="train"
                    />
                  </HorizontalFormItem>
                </Form>
              </ConfigSection>
              <ConfigSection title="Prediction">
                <Form>
                  <HorizontalFormItem label="Predict when" className="model-criteria">
                    <Criteria
                      columnNames={queryResult.getColumnNames()}
                      resultValues={queryResult.getData()}
                      modelOptions={options}
                      onChange={onPredictCriteriaChange}
                      criteriaType={"predict"}
                      editMode
                    />
                  </HorizontalFormItem>
                  <HorizontalFormItem label="When predicted, send notification">
                    <Rearm
                      modelOptions={options}
                      onChange={onRearmPredictChange}
                      rearmType="predict"
                      editMode
                    />
                  </HorizontalFormItem>
                  <HorizontalFormItem label="Predict Template">
                    <NotificationTemplate
                      model={model}
                      query={query}
                      columnNames={queryResult.getColumnNames()}
                      resultValues={queryResult.getData()}
                      subject={options?.predict_template?.custom_subject}
                      body={options?.predict_template?.custom_body}
                      setSubject={subject => onNotificationTemplateChange({ custom_subject: subject })}
                      setBody={body => onNotificationTemplateChange({ custom_body: body })}
                    />
                  </HorizontalFormItem>
                </Form>
              </ConfigSection>
            </>
          )}

          <HorizontalFormItem>
            <Button type="primary" onClick={this.save} disabled={!query} className="btn-create-model">
              {saving && (
                <span role="status" aria-live="polite" aria-relevant="additions removals">
                  <i className="fa fa-spinner fa-pulse m-r-5" aria-hidden="true" />
                  <span className="sr-only">Saving...</span>
                </span>
              )}
              Create Model
            </Button>
          </HorizontalFormItem>
        </div>
      </>
    );
  }
}

ModelNew.propTypes = {
  model: ModelType.isRequired,
  queryResult: PropTypes.object, // eslint-disable-line react/forbid-prop-types,
  pendingRearm: PropTypes.number,
  onQuerySelected: PropTypes.func.isRequired,
  save: PropTypes.func.isRequired,
  onNameChange: PropTypes.func.isRequired,
  onCriteriaChange: PropTypes.func.isRequired,
  onTrainCriteriaChange: PropTypes.func.isRequired,
  onPredictCriteriaChange: PropTypes.func.isRequired,
  onRearmTrainChange: PropTypes.func.isRequired,
  onRearmPredictChange: PropTypes.func.isRequired,
  onNotificationTemplateChange: PropTypes.func.isRequired,
  onDescriptionChange: PropTypes.func.isRequired,
  onVersionChange: PropTypes.func.isRequired,
  onRegressorChange: PropTypes.func.isRequired,
  onRegressorOptionsChange: PropTypes.func.isRequired,
  onTrainSizeChange: PropTypes.func.isRequired,
  onTestSizeChange: PropTypes.func.isRequired,
  onRandomStateChange: PropTypes.func.isRequired,
  onFeatureChange: PropTypes.func.isRequired,
  onTimestampChange: PropTypes.func.isRequired,
  onCategoryChange: PropTypes.func.isRequired,
  onTargetChange: PropTypes.func.isRequired,
  menuButton: PropTypes.node,
  onNotificationTrainTemplateChange: PropTypes.func.isRequired,
  onNotificationPredictTemplateChange: PropTypes.func.isRequired,
};

ModelNew.defaultProps = {
  queryResult: null,
  pendingRearm: null,
  pendingRearmTrain: null,
  pendingRearmPredict: null,
  menuButton: null,
};
