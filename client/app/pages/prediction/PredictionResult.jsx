// File: Alert.jsx

import React from "react";
import PropTypes from "prop-types";
import { trim, template, values } from "lodash";

import LoadingState from "@/components/items-list/components/LoadingState";
import routeWithUserSession from "@/components/ApplicationArea/routeWithUserSession";
import navigateTo from "@/components/ApplicationArea/navigateTo";

import { currentUser } from "@/services/auth";
import notification from "@/services/notification";

import  PredictionService  from "@/services/prediction";
import routes from "@/services/routes";

import MenuButton from "../../components/predictions/MenuButton";
import PredictionView from "../../components/predictions/PredictionResultView";

const MODES = {
  VIEW: 1,
};

const defaultNameBuilder = template("<%= model.name %>: <%= created_at %> [<%= id %>]");

export function getDefaultName(prediction) {
  if (!prediction.id) {
    return "Unknown Prediction";
  }
  return defaultNameBuilder(prediction);
}

class Prediction extends React.Component {
  static propTypes = {
    mode: PropTypes.oneOf(values(MODES)),
    predictionId: PropTypes.string,
    onError: PropTypes.func,
  };

  static defaultProps = {
    mode: null,
    predictionId: null,
    onError: () => {},
  };

  _isMounted = false;

  state = {
    prediction: null,
    mode: null,
  };

  componentDidMount() {
    this._isMounted = true;
    const { mode, predictionId } = this.props; 
    this.setState({ mode });
      PredictionService.get({ id: predictionId }) 
        .then(prediction => {
          if (this._isMounted) {
            const canEdit = currentUser.canEdit(prediction);
            this.setState({ prediction,canEdit, is_favorite: prediction.is_favorite , tags: prediction.tags});
          }
          //console.log(prediction)
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

  save = () => {
    const { prediction } = this.state;
    prediction.id = trim(prediction.id) || getDefaultName(prediction);

    return PredictionService.save(prediction)
      .then(prediction => {
        notification.success("Saved.");
        this.setState({ prediction, mode: MODES.VIEW });
        navigateTo(`predictions/${prediction.id}/view`, true);
      })
      .catch(() => {
        notification.error("Failed saving prediction.");
      });
  };

  setPredictionOptions = (obj) => {
    const { prediction } = this.state;
    const options = { ...prediction.options, ...obj };
    this.setState({
      prediction: Object.assign(prediction, { options }),
    });
  };


  delete = () => {
    const { prediction } = this.state;
    return PredictionService.delete(prediction.id)
      .then(() => {
        notification.success("Prediction deleted successfully.");
        navigateTo("predictions");
      })
      .catch(() => {
        notification.error("Failed deleting prediction.");
      });
  };

  archive = () => {
    const { prediction } = this.state;
    prediction.is_archived = true;
    return PredictionService.save(prediction)
      .then(() => {
        this.setState({ prediction });
        notification.success("Prediction archived successfully.");
        navigateTo(`predictions/archive`);
      })
      .catch(() => {
        notification.error("Failed archiving prediction.");
      });
  };

  unarchive = () => {
    const { prediction } = this.state;
    prediction.is_archived = false;
    return PredictionService.save(prediction)
      .then(() => {
        this.setState({ prediction });
        notification.success("Prediction unarchived successfully.");
        navigateTo(`predictions/${prediction.id}/view`, true);
        this.setState({ mode: MODES.VIEW});
      })
      .catch(() => {
        notification.error("Failed unarchiving prediction.");
      });
  };

  cancel = () => {
    const { id } = this.state.prediction;
    navigateTo(`predictions/${id}/view`, true);
    this.setState({ mode: MODES.VIEW});
  };

  favorite = () => {
    const { id } = this.state.prediction;
    return PredictionService.favorite(id)
      .then(() => {
        notification.success("Prediction added to favorites.");
      })
      .catch(() => {
        notification.error("Failed adding prediction to favorites.");
      });
  };

  unfavorite = () => {
    const { id } = this.state.prediction;
    return PredictionService.unfavorite(id)
      .then(() => {
        //this.unfavorite()
        notification.success("Prediction removed from favorites.");
      })
      .catch(() => {
        notification.error("Failed removing prediction from favorites.");
      });
  };

  setPredictionTags = obj => {
    if (!Array.isArray(obj)) {
        console.error("Expected an array for tags, but received:", obj);
        return;
    }

    this.setState(prevState => ({
        prediction: { ...prevState.prediction, tags: obj }
    }), this.save); // Ensure save is called after state update
};

  render() {
    const { prediction } = this.state;
    if (!prediction) {
      return <LoadingState className="m-t-30" />;
    }

    const { mode, canEdit } = this.state;

    const menuButton = (
      <MenuButton 
        doDelete={this.delete} 
        doArchive={this.archive} 
        canEdit={canEdit} 

        doUnarchive={this.unarchive} 
        archived={prediction.is_archived} 
        />
    );
    
    const enhancedPrediction = {
      ...prediction,
      favorite: this.favorite,
      unfavorite: this.unfavorite,
      content: prediction.content,
      is_favorite: prediction.is_favorite,
      tags: prediction.tags,
      query: prediction.query,
      model: prediction.model,
      destination: prediction.destination || null,
    };

    const commonProps = {
      prediction: enhancedPrediction,
      save: this.save,
      setPredictionTags: this.setPredictionTags,
      menuButton,
      onChange: () => {},
      name: getDefaultName(prediction),
    };

    return (
      <div className="predictions-page">
        <div className="container">
          {mode === MODES.VIEW && (
            <PredictionView canEdit={canEdit}   {...commonProps} />
          )}
        </div>
      </div>
    );
  }
}


routes.register(
  "PredictionResult.View",
  routeWithUserSession({
    path: "/predictions/:predictionId",
    title: "Prediction Result",
    render: pageProps => <Prediction {...pageProps} mode={MODES.VIEW} />,
  })
);