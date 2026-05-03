import React from "react";
import PropTypes from "prop-types";
import HelpTrigger from "@/components/HelpTrigger";
import DynamicComponent from "@/components/DynamicComponent";
import { MLModel as ModelType } from "@/components/proptypes";
import Form from "antd/lib/form";
import Button from "antd/lib/button";
import Title from "./Title";
import Criteria from "./Criteria";
import NotificationTemplate from "./NotificationTemplate";
import Rearm from "./Rearm";
import Query from "./Query";
import HorizontalFormItem from "../HorizontalFormItem";
import RegressorSelect from "./RegressorSelect";
import TrainTestSplitSlider from "./TrainTestSplitSlider";

export default class ModelEdit extends React.Component {
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
    this.props.save().catch((error) => {
      console.error("Save failed:", error);
      if (this._isMounted) {
        this.setState({ saving: false });
      }
    });
  };

  cancel = () => {
    this.props.cancel();
  };

  handleModelOptionsChange = (newOptions) => {
    const { model } = this.props;
    this.props.onOptionsChange({ ...model.options, ...newOptions });
  };

  render() {
    const { 
      model, 
      queryResult, 
      onNotificationPredictTemplateChange, 
      onNotificationTrainTemplateChange, 
      menuButton,
      onQuerySelected,
      onNameChange,
      onRearmTrainChange,
      onRearmPredictChange,
      onTrainCriteriaChange,
      onPredictCriteriaChange,
      onDescriptionChange,
      onVersionChange,
      onFeatureChange,
      onTargetChange,
      onCategoryChange,
      onTimestampChange,
      onRegressorChange,
      onRegressorOptionsChange,
      onTrainSizeChange,
      onRandomStateChange
    } = this.props;

    const { query, name, description, version, options } = model;
    const { saving } = this.state;
    const { predict_template, train_template, random_state } = options

    return (
      <>
        <Title name={name} model={model} onChange={onNameChange} editMode>
          <DynamicComponent name="ModelEdit.HeaderExtra" model={model} />
          <Button className="m-r-5" onClick={this.cancel}>
            <i className="fa fa-times m-r-5" aria-hidden="true" />
            Cancel
          </Button>
          <Button type="primary" onClick={this.save}>
            {saving ? (
              <span role="status" aria-live="polite" aria-relevant="additions removals">
                <i className="fa fa-spinner fa-pulse m-r-5" aria-hidden="true" />
                <span className="sr-only">Saving...</span>
              </span>
            ) : (
              <>
                <i className="fa fa-check m-r-5" aria-hidden="true" />
                Save Changes
              </>
            )}
          </Button>
          {menuButton}
        </Title>
        <div className="bg-white tiled p-20">
          <div className="d-flex">
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
                  onModelOptionsChange={this.handleModelOptionsChange}
                />
              </HorizontalFormItem>
              <HorizontalFormItem label="Description">
                <Form.Item>
                  <textarea
                    value={description}
                    onChange={(e) => onDescriptionChange(e.target.value)}
                    className="ant-input"
                    placeholder="Enter a description for the model"
                    editMode
                  />
                </Form.Item>
              </HorizontalFormItem>
              <HorizontalFormItem label="Version">
                <Form.Item>
                  <input
                    type="number"
                    value={version}
                    onChange={(e) => onVersionChange(e.target.value)}
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
                  onTrainSizeChange={onTrainSizeChange}
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
                    value={random_state ?? ''}
                    onChange={(e) => onRandomStateChange(e)}
                    className="ant-input"
                    placeholder="Enter the random state"
                  />
                </Form.Item>
              </HorizontalFormItem>
              {queryResult && options && (
                <>
                      <h4>Training Options</h4>
                      <HorizontalFormItem label={<span style={{ display: 'inline-block', marginBottom: '8px' }}>Retrain when</span>} className="model-criteria">
                        <Criteria
                          columnNames={queryResult.getColumnNames()}
                          resultValues={queryResult.getData()}
                          modelOptions={options}
                          onChange={onTrainCriteriaChange}
                          criteriaType={"train"}
                          editMode
                        />
                      </HorizontalFormItem>
                      <HorizontalFormItem label={<span style={{ display: 'inline-block', marginBottom: '8px' }}>When trained</span>}>
                        <Rearm
                          value={options.rearm_train || 'unknown'}
                          onChange={onRearmTrainChange}
                          rearmType="train"
                          editMode
                        />
                      </HorizontalFormItem>
                      <HorizontalFormItem label={<span style={{ display: 'inline-block', marginBottom: '8px' }}>Template</span>}>
                        <NotificationTemplate
                          model={model}
                          query={query}
                          columnNames={queryResult.getColumnNames()}
                          resultValues={queryResult.getData()}
                          subject={train_template?.custom_subject}
                          body={train_template?.custom_body}
                          setSubject={(subject) => onNotificationTrainTemplateChange({ custom_subject: subject })}
                          setBody={(body) => onNotificationTrainTemplateChange({ custom_body: body })}
                          templateType="train"
                        />
                      </HorizontalFormItem>
                      <h4>Prediction Options</h4>
                      <HorizontalFormItem label={<span style={{ display: 'inline-block', marginBottom: '8px' }}>Predict when</span>} className="model-criteria">
                        <Criteria
                          columnNames={queryResult.getColumnNames()}
                          resultValues={queryResult.getData()}
                          modelOptions={options}
                          onChange={onPredictCriteriaChange}
                          criteriaType={"predict"}
                          editMode
                        />
                      </HorizontalFormItem>
                      <HorizontalFormItem label={<span style={{ display: 'inline-block', marginBottom: '8px' }}>When predicted</span>}>
                        <Rearm
                          value={options.rearm_predict || 'unknown'}
                          onChange={onRearmPredictChange}
                          rearmType="predict"
                          editMode
                        />
                      </HorizontalFormItem>
                      <HorizontalFormItem label={<span style={{ display: 'inline-block', marginBottom: '8px' }}>Template</span>}>
                        <NotificationTemplate
                          model={model}
                          query={query}
                          columnNames={queryResult.getColumnNames()}
                          resultValues={queryResult.getData()}
                          subject={predict_template?.custom_subject}
                          body={predict_template?.custom_body}
                          setSubject={(subject) => onNotificationPredictTemplateChange({ custom_subject: subject })}
                          setBody={(body) => onNotificationPredictTemplateChange({ custom_body: body })}
                          templateType="predict"
                        />
                      </HorizontalFormItem>
                      </>
              )}
            </Form>
            <div>
              <HelpTrigger className="f-13" type="MODEL_SETUP">
                Setup Instructions <i className="fa fa-question-circle" aria-hidden="true" />
                <span className="sr-only">(help)</span>
              </HelpTrigger>
            </div>
          </div>
        </div>
      </>
    );
  }
}

ModelEdit.propTypes = {
  model: ModelType.isRequired,
  queryResult: PropTypes.object, // eslint-disable-line react/forbid-prop-types,
  pendingRearmTrain: PropTypes.string,
  pendingRearmPredict: PropTypes.string,
  menuButton: PropTypes.node.isRequired,
  save: PropTypes.func.isRequired,
  cancel: PropTypes.func.isRequired,
  onQuerySelected: PropTypes.func.isRequired,
  onNameChange: PropTypes.func.isRequired,
  onTrainCriteriaChange: PropTypes.func.isRequired,
  onPredictCriteriaChange: PropTypes.func.isRequired,
  onRearmTrainChange: PropTypes.func.isRequired,
  onRearmPredictChange: PropTypes.func.isRequired,
  onNotificationTrainTemplateChange: PropTypes.func.isRequired,
  onNotificationPredictTemplateChange: PropTypes.func.isRequired,
  onDescriptionChange: PropTypes.func.isRequired,
  onVersionChange: PropTypes.func.isRequired,
  onRegressorChange: PropTypes.func.isRequired,
  onRegressorOptionsChange: PropTypes.func.isRequired,
  onTrainSizeChange: PropTypes.func.isRequired,
  onRandomStateChange: PropTypes.func.isRequired,
  onFeatureChange: PropTypes.func.isRequired,
  onTargetChange: PropTypes.func.isRequired,
  onCategoryChange: PropTypes.func.isRequired,
  onTimestampChange: PropTypes.func.isRequired,
  onOptionsChange: PropTypes.func.isRequired,
};

ModelEdit.defaultProps = {
  queryResult: null,
  pendingRearmTrain: "never",
  pendingRearmPredict: "never",
};
