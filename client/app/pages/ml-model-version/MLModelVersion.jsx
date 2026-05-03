// File: model.jsx

import React from "react";
import PropTypes from "prop-types";
import { head, includes, template, values } from "lodash";

import LoadingState from "@/components/items-list/components/LoadingState";
import routeWithUserSession from "@/components/ApplicationArea/routeWithUserSession";
import navigateTo from "@/components/ApplicationArea/navigateTo";

import { currentUser } from "@/services/auth";
import notification from "@/services/notification";
import MLModelVersionService from "@/services/ml-models-versions.js";

import { Query as QueryService } from "@/services/query";
import routes from "@/services/routes";

import MenuButton from "../../components/models/MenuButton";
import MLModelVersionView from "../../components/models/MLModelView";


const MODES = {
  VIEW: 0,
};

const defaultNameBuilder = template("<%= query.name %>: <%= options.column %> <%= options.op %> <%= options.value %>");

export function getDefaultName(model) {
  if (!model.query) {
    return "New Model";
  }
  return defaultNameBuilder(model);
}

// Move showRevertModal outside of the component and make it a regular function
function showRevertModal(version, setSelectedVersion, setIsRevertModalVisible) {
  setSelectedVersion(version);
  setIsRevertModalVisible(true);
}

class MLModelVersion extends React.Component {
  static propTypes = {
    mode: PropTypes.oneOf(values(MODES)),
    modelVersionId: PropTypes.string,
    onError: PropTypes.func,
  };

  static defaultProps = {
    mode: null,
    modelVersionId: null,
    onError: () => {},
  };

  _isMounted = false;

  state = {
    model: null,
    queryResult: null,
    pendingRearm: null,
    canEdit: false,
    mode: null,
  };

  componentDidMount() {
    this._isMounted = true;
    const { mode, modelVersionId } = this.props; 
    this.setState({ mode });

    MLModelVersionService.get({ id: modelVersionId }) // Use modelVersionId to fetch model details
      .then(model => {
        if (this._isMounted) {
          const canEdit = currentUser.canEdit(model);

          this.setState({ 
            model, 
            canEdit, 
            pendingRearm: model.rearm, 
            is_favorite: model.is_favorite , 
            tags: model.tags, 
            rearm: model.rearm, 
            version: model.version, 
            description: model.description ,
            options: model.options,
          });

          this.onQueryView(model.query);

        }
      })
      .catch(error => {
        if (this._isMounted) {
          this.props.onError(error);
        }
      });
    
  }

  componentWillUnmount() {
    this._isMounted = false;
  }
  
  
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

  setModelOptions = (obj) => {
    const { model} = this.state;
    const options = { ...model.options, ...obj };
    this.setState({
      model:  Object.assign(model, { options }),
    });
  };

  setRegressorOptions = (obj) => {
    const { model} = this.state;
    const options = { ...model.options, regressor_options: { ...model.options.regressor_options, ...obj } };
    this.setState({
      model:  Object.assign(model, { options }),
    });
  };


  delete = () => {
    const { model} = this.state;
    return MLModelVersionService.delete(model.id)
      .then(() => {
        notification.success("Model Version deleted successfully.");
        navigateTo("ml_models_versions");
      })
      .catch(() => {
        notification.error("Failed deleting model.");
      });
  };

  archive = () => {
    const { model} = this.state;
    model.is_archived = true;
    return MLModelVersionService.save(model)
      .then(() => {
        this.setState({ model});
        notification.success("Model Version archived successfully.");
        navigateTo(`ml_models_versions/archive`);
      })
      .catch(() => {
        notification.error("Failed archiving model.");
      });
  };

  unarchive = () => {
    const { model} = this.state;
    model.is_archived = false;
    return MLModelVersionService.save(model)
      .then(() => {
        this.setState({ model});
        notification.success("Model Version unarchived successfully.");
        navigateTo(`ml_models_versions/${model.id}/edit`, true);
        this.setState({ mode: MODES.EDIT});
      })
      .catch(() => {
        notification.error("Failed unarchiving model.");
      });
  };


  cancel = () => {
    const { id } = this.state.model;
    navigateTo(`ml_models_versions/${id}/VIEW`, true);
    this.setState({ mode: MODES.VIEW});
  };

  favorite = () => {
    const { id } = this.state.model;
    return MLModelVersionService.favorite(id)
      .then(() => {
        notification.success("Model Version added to favorites.");
      })
      .catch(() => {
        notification.error("Failed adding version to favorites.");
      });
  };

  unfavorite = () => {
    const { id } = this.state.model;
    return MLModelVersionService.unfavorite(id)
      .then(() => {
        //this.unfavorite()
        notification.success("Model Version removed from favorites.");
      })
      .catch(() => {
        notification.error("Failed removing version from favorites.");
      });
  };


  setModelTags = obj => {
    if (!Array.isArray(obj)) {
        console.error("Expected an array for tags, but received:", obj);
        return;
    }

    this.setState(prevState => ({
        model:  { ...prevState.model, tags: obj }
    }), this.save); // Ensure save is called after state update
};


  render() {
    const { model } = this.state;
    if (!model) {
      return <LoadingState className="m-t-30" />;
    }

    const { queryResult, mode, pendingRearm } = this.state;

    const menuButton = (
      <MenuButton 
        doDelete={this.delete} 
        doArchive={this.archive} 
        doUnarchive={this.unarchive} 
        archived={model.is_archived} 
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
      showRevertModal: (version) => showRevertModal(version, this.setSelectedVersion, this.setIsRevertModalVisible),
    };

    const commonProps = {
      model:  enhancedModel,
      queryResult,
      pendingRearm,
      menuButton,
      save: this.save,
      setModelTags: this.setModelTags,
      onQueryView: this.onQueryView,
      onCriteriaChange: this.setModelOptions,
      onNotificationTemplateChange: this.setModelOptions,
      onChange: () => {},
    };

    return (
      <div className="models-versions-page">
        <div className="container">
          {mode === MODES.VIEW && (
            <MLModelVersionView {...commonProps} />
          )}
        </div>
      </div>
    );
  }
}

routes.register(
  "MLModelsVersions.View",
  routeWithUserSession({
    path: "/ml_models_versions/:modelVersionId",
    title: "Model",
    render: pageProps => <MLModelVersion {...pageProps} mode={MODES.VIEW} />,
  })
);
