// File: model.jsx

import React from "react";
import PropTypes from "prop-types";
import { head, includes, trim, template, values } from "lodash";

import LoadingState from "@/components/items-list/components/LoadingState";
import routeWithUserSession from "@/components/ApplicationArea/routeWithUserSession";
import navigateTo from "@/components/ApplicationArea/navigateTo";

import { currentUser } from "@/services/auth";
import notification from "@/services/notification";
import ModelService from "@/services/ml-model";

import { Query as QueryService } from "@/services/query";
import routes from "@/services/routes";

import MenuButton from "../../components/models/MenuButton";
import MLModelView from "../../components/models/MLModelView";
import MLModelEdit from "../../components/models/MLModelEdit";
import MLModelNew from "../../components/models/MLModelNew";
import MLModelPredictions from "../../components/models/MLModelPredictions";
import MLModelVersions from "../../components/models/MLModelVersions";
import MLModelMetrics from "../../components/models/MLModelMetrics";
import MLModelMetricsHistory from "../../components/models/MLModelMetricsHistory";
import MLModelMetricsHistoryTrain from "../../components/models/MLModelMetricsHistoryTrain";


const MODES = {
  NEW: 0,
  VIEW: 1,
  EDIT: 2,
  PREDICTIONS: 3,
  VERSIONS: 4,
  OVERVIEW: 5,
  METRICS: 6,
  METRICS_HISTORY:7,
  METRICS_HISTORY_TRAIN:8,
};

//convert target to string
const defaultNameBuilder = template("<%= query.name %>: <%= options.regressor %> model");

export function getDefaultName(model) {
  if (!model.query) {
    return "New Model";
  }
  return defaultNameBuilder(model);
}

class MLModel extends React.Component {
  static propTypes = {
    mode: PropTypes.oneOf(values(MODES)),
    modelId: PropTypes.string,
    onError: PropTypes.func,
  };

  static defaultProps = {
    mode: null,
    modelId: null,
    onError: () => { },
  };

  _isMounted = false;

  state = {
    model: null,
    queryResult: null,
    pendingRearmTrain: null,
    pendingRearmPredict: null,
    canEdit: false,
    mode: null,
    predictions: null,
    versions: null,
  };

  componentDidMount() {
    this._isMounted = true;
    const { mode, modelId } = this.props;
    this.setState({ mode });

    if (mode === MODES.NEW) {
      this.setState({
        model: {
          options: {
            op: ">",
            value: 1,
            muted: false,
            regressor: "Regression",
            regressor_options: {},
            train_size: 0.7,
            test_size: 0.3,
            random_state: 42,
            features: [],
            targets: [],
            categories: [],
            timestamp: null,
            rearm_train: "never",
            rearm_predict: "never",
            train_template: {
              custom_subject: "",
              custom_body: "",
            },
            predict_template: {
              custom_subject: "",
              custom_body: "",
            },
          },
          is_archived: false,
          tags: [],
          rearm: 0,
          version: 1,
          description: "This model is awesome!"
        },
        pendingRearmTrain: 'never',
        pendingRearmPredict: 'never',
        canEdit: true,

      });
    } else {
      ModelService.get({ id: modelId }) // Use modelId to fetch model details
        .then(model => {
          if (this._isMounted) {
            const canEdit = currentUser.canEdit(model);

            // force view mode if can't edit
            if (!canEdit) {
              this.setState({ mode: MODES.OVERVIEW });
              notification.warn(
                "You cannot edit this model",
                "You do not have sufficient permissions to edit this model, and have been redirected to the view-only page.",
                { duration: 0 }
              );
            }

            this.setState({
              model,
              canEdit,
              pendingRearmTrain: model.options.rearm_train || 'never',
              pendingRearmPredict: model.options.rearm_predict || 'never',
              is_favorite: model.is_favorite,
              tags: model.tags,
              rearm: model.rearm,
              version: model.version,
              description: model.description,
              options: model.options,

            });

            this.onQueryView(model.query);

            // Fetch predictions and versions if in OVERVIEW, PREDICTIONS, or VERSIONS mode
            if (mode === MODES.OVERVIEW || mode === MODES.PREDICTIONS || mode === MODES.VERSIONS) {
              this.fetchPredictions(modelId);
              this.fetchVersions(modelId);
            }
          }
        })
        .catch(error => {
          if (this._isMounted) {
            this.props.onError(error);
          }
        });
    }
  }

  componentWillUnmount() {
    this._isMounted = false;
  }

  save = () => {
    const { model, pendingRearmTrain, pendingRearmPredict } = this.state;
    model.name = trim(model.name) || getDefaultName(model);
    model.options.rearm_train = pendingRearmTrain || 'never';
    model.options.rearm_predict = pendingRearmPredict || 'never';

    return ModelService.save(model)
      .then(model => {
        notification.success("Saved.");
        this.setState({ model, mode: MODES.OVERVIEW });
        navigateTo(`ml_models/${model.id}/overview`, true);
      })
      .catch(() => {
        notification.error("Failed saving model.");
      });
  };

  onQuerySelected = (query) => {
    this.setState(({ model }) => ({
      model: Object.assign(model, { query }),

      queryResult: null,
    }));

    if (query) {
      // get cached result for column names and values
      new QueryService(query).getQueryResultPromise().then(queryResult => {
        if (this._isMounted) {
          this.setState({ queryResult });

          let { column } = this.state.model.options;
          const columns = queryResult.getColumnNames();

          // Reset model options for new query
          this.setModelOptions({
            features: [],
            targets: [],
            categories: [],
            timestamp: null,
          });

          // default to first column name if none chosen, or irrelevant in current query
          if (!column || !includes(columns, column)) {
            column = head(queryResult.getColumnNames());
          }
          this.setModelOptions({ column });
          this.setModelName(getDefaultName(this.state.model));
        }
      });
    }
  };


  onQueryView = (query) => {
    this.setState(({ model }) => ({
      model: Object.assign(model, { query }),
      queryResult: null,
    }));

    if (query) {
      // get cached result for column names and values
      new QueryService(query).getQueryResultPromise().then(queryResult => {
        if (this._isMounted) {
          this.setState({ queryResult });

          let { column } = this.state.model.options;
          const columns = queryResult.getColumnNames();

          // default to first column name if none chosen, or irrelevant in current query
          if (!column || !includes(columns, column)) {
            column = head(queryResult.getColumnNames());
          }
          this.setModelOptions({ column });
        }
      });
    }
  };

  onNameChange = name => {
    const { model } = this.state;
    this.setState({
      model: Object.assign(model, { name }),
    });
  };

  onRearmTrainChange = (value) => {
    this.setModelOptions({ rearm_train: value });
    this.setState({ pendingRearmTrain: value });
  };

  onRearmPredictChange = (value) => {
    this.setModelOptions({ rearm_predict: value });
    this.setState({ pendingRearmPredict: value });
  };

  onNotificationTrainTemplateChange = (obj) => {
    const { model } = this.state;
    this.setState({
      model: {
        ...model,
        options: {
          ...model.options,
          train_template: {
            ...model.options.train_template,
            ...obj
          }
        }
      }
    });
  };

  onNotificationPredictTemplateChange = (obj) => {
    const { model } = this.state;
    this.setState({
      model: {
        ...model,
        options: {
          ...model.options,
          predict_template: {
            ...model.options.predict_template,
            ...obj
          }
        }
      }
    });
  };

  setModelOptions = (obj) => {
    const { model } = this.state;
    const options = { ...model.options, ...obj };
    this.setState({
      model: Object.assign(model, { options }),
    });
  };

  setModelName = name => {
    const { model } = this.state;
    this.setState({
      model: Object.assign(model, { name }),
    });
  };


  setRegressorOptions = (obj) => {
    const { model } = this.state;
    const options = { ...model.options, regressor_options: { ...model.options.regressor_options, ...obj } };
    this.setState({
      model: Object.assign(model, { options }),
    });
  };


  delete = () => {
    const { model } = this.state;
    return ModelService.delete(model.id)
      .then(() => {
        notification.success("Model deleted successfully.");
        navigateTo("ml_models");
      })
      .catch(() => {
        notification.error("Failed deleting model.");
      });
  };

  archive = () => {
    const { model } = this.state;
    model.is_archived = true;
    return ModelService.save(model)
      .then(() => {
        this.setState({ model });
        notification.success("Model archived successfully.");
        navigateTo(`ml_models/archive`);
      })
      .catch(() => {
        notification.error("Failed archiving model.");
      });
  };

  unarchive = () => {
    const { model } = this.state;
    model.is_archived = false;
    return ModelService.save(model)
      .then(() => {
        this.setState({ model });
        notification.success("Model unarchived successfully.");
        navigateTo(`ml_models/${model.id}/edit`, true);
        this.setState({ mode: MODES.EDIT });
      })
      .catch(() => {
        notification.error("Failed unarchiving model.");
      });
  };

  mute = () => {
    const { model } = this.state;
    return ModelService.mute(model)
      .then(() => {
        this.setModelOptions({ muted: true });
        notification.warn("Notifications have been muted.");
      })
      .catch(() => {
        notification.error("Failed muting notifications.");
      });
  };

  unmute = () => {
    const { model } = this.state;
    return ModelService.unmute(model)
      .then(() => {
        this.setModelOptions({ muted: false });
        notification.success("Notifications have been restored.");
      })
      .catch(() => {
        notification.error("Failed restoring notifications.");
      });
  };

  edit = () => {
    const { id } = this.state.model;
    navigateTo(`ml_models/${id}/edit`, true);
    this.setState({ mode: MODES.EDIT });
  };

  cancel = () => {
    const { id } = this.state.model;
    navigateTo(`ml_models/${id}/overview`, true);
    this.setState({ mode: MODES.OVERVIEW });
  };

  favorite = () => {
    const { id } = this.state.model;
    return ModelService.favorite(id)
      .then(() => {
        notification.success("Model added to favorites.");
      })
      .catch(() => {
        notification.error("Failed adding model to favorites.");
      });
  };

  unfavorite = () => {
    const { id } = this.state.model;
    return ModelService.unfavorite(id)
      .then(() => {
        //this.unfavorite()
        notification.success("Model removed from favorites.");
      })
      .catch(() => {
        notification.error("Failed removing model from favorites.");
      });
  };


  setModelTags = obj => {
    if (!Array.isArray(obj)) {
      return;
    }

    this.setState(prevState => ({
      model: { ...prevState.model, tags: obj }
    }), this.save); // Ensure save is called after state update
  };

  onTrainSizeChange = (value) => {
    this.setModelOptions({ train_size: value, test_size: 1 - value });
  };

  onVersionChange = version => {
    const { model } = this.state;
    this.setState({
      model: Object.assign(model, { version }),
    });
  };

  onRegressorChange = regressor => {
    this.setModelOptions({ regressor });
    this.setRegressorOptions({});
  };

  onRegressorOptionsChange = (regressor_options) => {
    this.setRegressorOptions(regressor_options);
  };


  onDescriptionChange = description => {
    const { model } = this.state;
    this.setState({
      model: Object.assign(model, { description }),
    });
  };

  onFeatureChange = (features) => {
    this.setModelOptions({ features });
  };

  onTargetChange = (targets) => {
    this.setModelOptions({ targets });
  };

  onCategoryChange = (categories) => {
    this.setModelOptions({ categories });
  };

  onTimestampChange = (timestamp) => {
    this.setModelOptions({ timestamp });
  };


  trainModel = () => {
    const { model } = this.state;
    return ModelService.train(model.id)
      .then(() => {
        notification.success("Model training started.");
        this.setState({ mode: MODES.OVERVIEW }, () => {
          const currentPath = `/ml_models/${model.id}/overview`;
          if (window.location.pathname === currentPath) {
            // If on the same page, wait 3 seconds then refresh the page
            setTimeout(() => {
              window.location.reload();
            }, 1500);
          } else {
            // Otherwise, navigate to the overview page
            navigateTo(currentPath, true);
          }
        });
      })
      .catch(() => {
        notification.error("Failed to start model training.");
      });
  };

  stopTraining = () => {
    const { model } = this.state;
    return ModelService.stopTraining(model.id)
      .then(() => {
        notification.success("Model training stopped.");
      })
      .catch(() => {
        notification.error("Failed to stop model training.");
      });
  };

  predict = () => {
    const { model } = this.state;
    return ModelService.predict(model.id)
      .then(prediction => {
        const predictionId = prediction?.id;
        const predictionLink = `/predictions/${predictionId}`;
        notification.success(
          "Prediction successful.",
          <a href={predictionLink}>View predictions</a>,
          "."
        );
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      })
      .catch((e) => {
        notification.error("Failed to make prediction.");
        notification.error(e);
      });
  };

  stopPredicting = () => {
    const { model } = this.state;
    return ModelService.stopPredicting(model.id)
      .then(() => {
        notification.success("Model prediction stopped.");
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      })
      .catch(() => {
        notification.error("Failed to stop model prediction.");
      });
  };

  onRandomStateChange = (value) => {
    this.setModelOptions({ random_state: value });
  };


  revertToVersion = (versionNumber) => {
    const { model } = this.state;
    return ModelService.revertToVersion(model.id, versionNumber)
      .then(() => {
        return ModelService.get({ id: model.id });
      })
      .then(updatedModel => {
        this.setState({ model: updatedModel });
        notification.success(`Model reverted to version ${versionNumber} successfully. New version: ${updatedModel.version}`);
        
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      })
      .catch((error) => {
        notification.error("Failed reverting model to version " + versionNumber + ".");
      });
  };

  createFromVersion = (versionNumber) => {
    const { model } = this.state;
    return ModelService.createFromVersion(model.id, versionNumber)
      .then(newModel => {
        notification.success(`New model created from version ${versionNumber} successfully.`);
        // Navigate to the new model's overview page
        navigateTo(`ml_models/${newModel.id}/overview`, true);
      })
      .catch((error) => {
        notification.error("Failed creating new model from version " + versionNumber + ".");
      });
  };

  copyModel = () => {
    const { model } = this.state;
    return ModelService.copy(model.id)
      .then(newModel => {
        notification.success(`Model copied successfully.`);
      })
  }

  fetchPredictions(modelId) {
    ModelService.getPredictions(modelId)
      .then(predictions => {
        if (this._isMounted) {
          this.setState({ predictions });
        }
      })
      .catch(() => {
        notification.error("Failed to load model predictions.");
      });
  }

  fetchVersions(modelId) {
    ModelService.getVersions(modelId)
      .then(versions => {
        if (this._isMounted) {
          this.setState({ versions });
        }
      })
      .catch(() => {
        notification.error("Failed to load model versions.");
      });
  }

  onOptionsChange = (newOptions) => {
    this.setState(prevState => ({
      model: {
        ...prevState.model,
        options: newOptions
      }
    }));
  };

  render() {
    const { model, predictions, versions } = this.state;
    if (!model) {
      return <LoadingState className="m-t-30" />;
    }
    const muted = !!model.options.muted;
    const { queryResult, mode, canEdit, pendingRearmTrain, pendingRearmPredict } = this.state;

    const menuButton = (
      <MenuButton
        doDelete={this.delete}
        muted={muted}
        mute={this.mute}
        unmute={this.unmute}
        trainModel={this.trainModel}
        stopTraining={this.stopTraining}
        stopPredicting={this.stopPredicting}
        predict={this.predict}
        canEdit={canEdit}
        doArchive={this.archive}
        doUnarchive={this.unarchive}
        archived={model.is_archived}
        modelId={model.id}
        revertToVersion={this.revertToVersion}
        createFromVersion={this.createFromVersion}
        copyModel={this.copyModel}
        stateTrain={model.state_train}
        statePredict={model.state_predict}
      />
    );

    const enhancedModel = {
      ...model,
      favorite: this.favorite,
      unfavorite: this.unfavorite,
      is_favorite: model.is_favorite,
      tags: model.tags,
      query: model.query,
      rearm: model.rearm,
      version: model.version,
      description: model.description,
      options: model.options,

    };

    const commonProps = {
      model: enhancedModel,
      queryResult,
      pendingRearmTrain,
      pendingRearmPredict,
      menuButton,
      save: this.save,
      setModelTags: this.setModelTags,
      onQuerySelected: this.onQuerySelected,
      onQueryView: this.onQueryView,
      onRearmTrainChange: this.onRearmTrainChange,
      onRearmPredictChange: this.onRearmPredictChange,
      onNameChange: this.onNameChange,
      onTrainCriteriaChange: this.setModelOptions,
      onPredictCriteriaChange: this.setModelOptions,
      onNotificationTrainTemplateChange: this.onNotificationTrainTemplateChange,
      onNotificationPredictTemplateChange: this.onNotificationPredictTemplateChange,
      onDescriptionChange: this.onDescriptionChange,
      onVersionChange: this.onVersionChange,
      onRegressorChange: this.onRegressorChange,
      onRegressorOptionsChange: this.onRegressorOptionsChange,
      onTrainSizeChange: this.onTrainSizeChange,
      onRandomStateChange: this.onRandomStateChange,
      onFeatureChange: this.onFeatureChange,
      onTargetChange: this.onTargetChange,
      onCategoryChange: this.onCategoryChange,
      onTimestampChange: this.onTimestampChange,
      onChange: () => { },
      revertToVersion: this.revertToVersion,
      onOptionsChange: this.onOptionsChange,
      createFromVersion: this.createFromVersion,
      copyModel: this.copyModel,
    };

    return (
      <div className="model-page">
        <div className="container">
          {mode === MODES.NEW && <MLModelNew canEdit={canEdit} {...commonProps} />}
          {mode === MODES.VIEW && <MLModelView canEdit={canEdit} onEdit={this.edit} muted={muted} unmute={this.unmute} trainModel={this.trainModel} stopTraining={this.stopTraining} stopPredicting={this.stopPredicting} predict={this.predict} {...commonProps} />}
          {mode === MODES.EDIT && <MLModelEdit cancel={this.cancel} {...commonProps} />}
          {mode === MODES.PREDICTIONS && <MLModelPredictions modelId={model.id} predictions={predictions} />}
          {mode === MODES.VERSIONS && <MLModelVersions modelId={model.id} versions={versions} revertToVersion={this.revertToVersion} />}
          {mode === MODES.METRICS && <MLModelMetrics metrics={model.metrics || {}} />}
          {mode === MODES.METRICS_HISTORY && <MLModelMetricsHistory predictions={predictions} />}
          {mode === MODES.OVERVIEW && (
            <>
              <MLModelView canEdit={canEdit} onEdit={this.edit} muted={muted} unmute={this.unmute} trainModel={this.trainModel} stopTraining={this.stopTraining} stopPredicting={this.stopPredicting} predict={this.predict} {...commonProps} />
              <MLModelMetrics metrics={model.metrics || {}} />
              <MLModelMetricsHistory predictions={predictions} />
              <MLModelMetricsHistoryTrain versions={versions} />
              <MLModelPredictions modelId={model.id} predictions={predictions} />
              <MLModelVersions modelId={model.id} versions={versions} revertToVersion={this.revertToVersion} createFromVersion={this.createFromVersion} copyModel={this.copyModel} />
            </>
          )}
        </div>
      </div>
    );
  }
}

routes.register(
  "MLModels.New",
  routeWithUserSession({
    path: "/ml_models/new",
    title: "New Model",
    render: pageProps => <MLModel {...pageProps} mode={MODES.NEW} />,
  })
);
routes.register(
  "MLModels.View",
  routeWithUserSession({
    path: "/ml_models/:modelId",
    title: "Model",
    render: pageProps => <MLModel {...pageProps} mode={MODES.VIEW} />,
  })
);
routes.register(
  "MLModels.Edit",
  routeWithUserSession({
    path: "/ml_models/:modelId/edit",
    title: "Model",
    render: pageProps => <MLModel {...pageProps} mode={MODES.EDIT} />,
  })
);

routes.register(
  "MLModels.Stats",
  routeWithUserSession({
    path: "/ml_models/:modelId/stats",
    title: "Model Statistics",
    render: pageProps => <MLModel {...pageProps} mode={MODES.STATS} />,
  })
);
routes.register(
  "MLModels.Overview",
  routeWithUserSession({
    path: "/ml_models/:modelId/overview",
    title: "Model Overview",
    render: pageProps => <MLModel {...pageProps} mode={MODES.OVERVIEW} />,
  })
);
routes.register(
  "MLModels.Predictions",
  routeWithUserSession({
    path: "/ml_models/:modelId/predictions",
    title: "Model Predictions",
    render: pageProps => <MLModel {...pageProps} mode={MODES.PREDICTIONS} />,
  })
);
routes.register(
  "MLModels.Versions",
  routeWithUserSession({
    path: "/ml_models/:modelId/versions",
    title: "Model Versions",
    render: pageProps => <MLModel {...pageProps} mode={MODES.VERSIONS} />,
  })
);
routes.register(
  "MLModels.MetricsHistory",
  routeWithUserSession({
    path: "/ml_models/:modelId/metrics_history",
    title: "Model Metrics History",
    render: pageProps => <MLModel {...pageProps} mode={MODES.METRICS_HISTORY} />,
  })
);

routes.register(
  "MLModels.MetricsHistoryTrain",
  routeWithUserSession({
    path: "/ml_models/:modelId/metrics_history_train",
    title: "Model Metrics History",
    render: pageProps => <MLModel {...pageProps} mode={MODES.METRICS_HISTORY_TRAIN} />,
  })
);

routes.register(
  "MLModels.Metrics",
  routeWithUserSession({
    path: "/ml_models/:modelId/metrics",
    title: "Model Metrics",
    render: pageProps => <MLModel {...pageProps} mode={MODES.METRICS} />,
  })
);
