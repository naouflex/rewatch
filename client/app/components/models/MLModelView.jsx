import React from "react";
import PropTypes from "prop-types";
import cx from "classnames";

import Link from "@/components/Link";
import TimeAgo from "@/components/TimeAgo";
import { MLModel as ModelType } from "@/components/proptypes";

import Form from "antd/lib/form";
import Button from "antd/lib/button";
import Tooltip from "@/components/Tooltip";
import AntAlert from "antd/lib/alert";
import * as Grid from "antd/lib/grid";

import Title from "./Title";
import Criteria from "./Criteria";
import Rearm from "./Rearm";
import Query from "./Query";
import ModelDestinations from "./ModelDestinations";
import HorizontalFormItem from "../HorizontalFormItem";
import { STATE_CLASS } from "../../pages/ml-models/MLModelsList";
import DynamicComponent from "@/components/DynamicComponent";
import TrainTestSplitSlider from "./TrainTestSplitSlider";
import RegressorSelect from "./RegressorSelect";
import NotificationTemplate from "./NotificationTemplate";
import "./MLModelView.less";

function ModelState({ text, state, lastTriggered }) {
  return (
    <div className="model-state">
      <span className={`model-state-indicator label ${STATE_CLASS[state]}`}>{text} {state}</span>
      {state === "unknown" && <div className="ant-form-item-explain">Model condition has not been evaluated.</div>}
      {lastTriggered && (
        <div className="ant-form-item-explain">
          Last triggered{" "}
          <span className="model-last-triggered">
            <TimeAgo date={lastTriggered} />
          </span>
        </div>
      )}
    </div>
  );
}

ModelState.propTypes = {
  state: PropTypes.string.isRequired,
  lastTriggered: PropTypes.string,
};

ModelState.defaultProps = {
  lastTriggered: null,
};

export default class ModelView extends React.Component {
  _isMounted = false;

  state = {
    unmuting: false,
    favoriting: false,
    archiving: false,
    training: false,
    predicting: false,
  };

  componentDidMount() {
    this._isMounted = true;
  }

  componentWillUnmount() {
    this._isMounted = false;
  }

  handleTrainSizeChange = (train_size) => {
    this.props.onTrainSizeChange(train_size);
  };

  handleRegressorChange = (regressor) => {
    this.props.onRegressorChange(regressor);
  };

  handleRegressorOptionsChange = (options) => {
    this.props.onRegressorOptionsChange(options);
  };

  handleFeatureChange = (features) => {
    this.props.onFeatureChange(features);
  };

  handleTargetChange = (targets) => {
    this.props.onTargetChange(targets);
  };

  handleCategoryChange = (categories) => {
    this.props.onCategoryChange(categories);
  }

  handleTimestampChange = (timestamp) => {
    this.props.onTimestampChange(timestamp);
  }


  archive = () => {
    this.setState({ archiving: true });
    this.props.archive().finally(() => {
      this.setState({ archiving: false });
    }
    );
  }

  favorite = () => {
    this.setState({ favoriting: true });
    this.props.favorite().finally(() => {
      this.setState({ favoriting: false });
    }
    );
  }

  unarchive = () => {
    this.setState({ archiving: true });
    this.props.unarchive().finally(() => {
      this.setState({ archiving: false });
    }
    );
  }

  unfavorite = () => {
    this.setState({ favoriting: true });
    this.props.unfavorite().finally(() => {
      this.setState({ favoriting: false });
    }
    );
  }

  unmute = () => {
    this.setState({ unmuting: true });
    this.props.unmute().finally(() => {
      this.setState({ unmuting: false });
    });
  };

  trainModel = () => {
    this.setState({ training: true });
    this.props.trainModel().finally(() => {
      this.setState({ training: false });
    }
    );
  }

  stopTraining = () => {
    this.setState({ training: true });
    this.props.stopTraining().finally(() => {
      this.setState({ training: false });
    }
    );
  }

  stopPredicting = () => {
    this.setState({ predicting: true });
    this.props.stopPredicting().finally(() => {
      this.setState({ predicting: false });
    }
    );
  }
  predict = () => {
    this.setState({ predicting: true });
    this.props.predict().finally(() => {
      this.setState({ predicting: false });
    }
    );
  }



  render() {
    const { model, queryResult, canEdit, onEdit, menuButton, onChange, setModelTags } = this.props; // Ensure this is passed correctly
    const { query, name, description, version, options } = model;
    const { train_template, predict_template, train_last_triggered_at, predict_last_triggered_at } = options;


    return (
      <>
        <Title name={name} model={model} editMode={false} tagsExtra={null} onChange={onChange} canEdit={canEdit} setModelTags={setModelTags}>
          <DynamicComponent name="ModelView.HeaderExtra" model={model} />
          <Tooltip title={canEdit ? "" : "You do not have sufficient permissions to edit this model"}>
            <Button type="default" onClick={canEdit ? onEdit : null} className={cx({ disabled: !canEdit })}>
              <i className="fa fa-edit m-r-5" aria-hidden="true" />
              Edit
            </Button>
            {menuButton}
          </Tooltip>
        </Title>
        <h3>Model Settings</h3>
        <div className="bg-white tiled p-20">
          <Grid.Row type="flex" gutter={16}>
            <Grid.Col xs={24} md={16} className="d-flex">
              <Form className="flex-fill">
                <HorizontalFormItem>
                  <ModelState text="Status :" state={model.state} lastTriggered={null} />
                  <ModelState text="Training :" state={model.state_train} lastTriggered={train_last_triggered_at} />
                  <ModelState text="Predicting :" state={model.state_predict} lastTriggered={predict_last_triggered_at} />
                </HorizontalFormItem>
                <HorizontalFormItem label="Query">
                  <Query
                    query={query}
                    queryResult={queryResult}
                    modelOptions={options}
                  />
                </HorizontalFormItem>
                <HorizontalFormItem label="Description">
                  <p>{description}</p>
                </HorizontalFormItem>
                <HorizontalFormItem label="Version">
                  <Form.Item>
                    <input
                      type="number"
                      value={version}
                      className="ant-input"
                      disabled={true}
                    />
                  </Form.Item>
                </HorizontalFormItem>
                <HorizontalFormItem label="Regressor">
                  <RegressorSelect
                    value={options.regressor}
                    modelOptions={options}
                    disabled={true}
                  />
                </HorizontalFormItem>
                <HorizontalFormItem label="Training Size">
                  <TrainTestSplitSlider
                    trainSize={options.train_size}
                    onTrainSizeChange={() => {}} // No-op in view mode
                    editMode={false}
                    timestampData={queryResult && queryResult.getColumnNames().includes("timestamp") ? {
                      dates: queryResult.getData().map(row => row["timestamp"]),
                      column: "timestamp"
                    } : null}
                  />
                </HorizontalFormItem>
                <HorizontalFormItem label="Random State">
                  <p>{options.random_state}</p>
                </HorizontalFormItem>

                {queryResult && options && (
                  <>
                    <h4>Training Options</h4>
                    <HorizontalFormItem label={<span style={{ display: 'inline-block', marginBottom: '8px' }}>Retrain when</span>} className="model-criteria">
                      <Criteria
                        columnNames={queryResult.getColumnNames()}
                        resultValues={queryResult.getData()}
                        modelOptions={options}
                        criteriaType={"train"}
                        disabled={true}
                      />
                    </HorizontalFormItem>
                    <HorizontalFormItem label={<span style={{ display: 'inline-block', marginBottom: '8px' }}>When trained</span>}>
                      <Rearm
                        value={options.rearm_train || 'unknown'}
                        rearmType="train"
                        disabled={true}
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
                        templateType="train"
                        disabled={true}
                      />
                    </HorizontalFormItem>
                    <h4>Prediction Options</h4>
                    <HorizontalFormItem label={<span style={{ display: 'inline-block', marginBottom: '8px' }}>Predict when</span>} className="model-criteria">
                      <Criteria
                        columnNames={queryResult.getColumnNames()}
                        resultValues={queryResult.getData()}
                        modelOptions={options}
                        criteriaType={"predict"}
                        disabled={true}
                      />
                    </HorizontalFormItem>
                    <HorizontalFormItem label={<span style={{ display: 'inline-block', marginBottom: '8px' }}>When predicted</span>}>
                      <Rearm
                        value={options.rearm_predict || 'unknown'}
                        rearmType="predict"
                        disabled={true}
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
                        templateType="predict"
                        disabled={true}
                      />
                    </HorizontalFormItem>
                  </>
                )}
              </Form>
            </Grid.Col>
            <Grid.Col xs={24} md={8}>
              {options.muted && (
                <AntAlert
                  className="m-b-20"
                  message={
                    <>
                      <i className="fa fa-bell-slash-o" aria-hidden="true" /> Notifications are muted
                    </>
                  }
                  description={
                    <>
                      Notifications for this model will not be sent.
                      <br />
                      {canEdit && (
                        <>
                          To restore notifications click
                          <Button
                            size="small"
                            type="primary"
                            onClick={this.unmute}
                            loading={this.state.unmuting}
                            className="m-t-5 m-l-5">
                            Unmute
                          </Button>
                        </>
                      )}
                    </>
                  }
                  type="warning"
                />
              )}
              <h4>
                Destinations{" "}
                <Tooltip title="Open Model Destinations page in a new tab.">
                  <Link href="destinations" target="_blank">
                    <i className="fa fa-external-link f-13" aria-hidden="true" />
                    <span className="sr-only">(opens in a new tab)</span>
                  </Link>
                </Tooltip>
              </h4>
              <ModelDestinations modelId={model.id} />
            </Grid.Col>
          </Grid.Row>
        </div>
      </>
    );
  }
}

ModelView.propTypes = {
  model: ModelType.isRequired,
  queryResult: PropTypes.object, // eslint-disable-line react/forbid-prop-types,
  modelOptions: PropTypes.shape({
    features: PropTypes.array,
    targets: PropTypes.array,
    categories: PropTypes.array,
    timestamp: PropTypes.string,
  }).isRequired,
  canEdit: PropTypes.bool.isRequired,
  onEdit: PropTypes.func.isRequired,
  menuButton: PropTypes.node.isRequired,
  unmute: PropTypes.func,
  favorite: PropTypes.func.isRequired,
  unfavorite: PropTypes.func.isRequired,
  archive: PropTypes.func.isRequired,
  unarchive: PropTypes.func.isRequired,
  trainModel: PropTypes.func.isRequired,
  stopTraining: PropTypes.func.isRequired,
  stopPredicting: PropTypes.func.isRequired,
  predict: PropTypes.func.isRequired,

};

ModelView.defaultProps = {
  queryResult: null,
  unmute: null,
};
