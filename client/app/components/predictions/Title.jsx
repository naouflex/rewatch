import React from "react";
import PropTypes from "prop-types";
import { getDefaultName } from "../../pages/prediction/PredictionResult";
import map from "lodash";
import { PredictionResult as PredictionType } from "@/components/proptypes";
import FavoritesControl from "@/components/FavoritesControl";
import { PredictionsTagsControl } from "@/components/tags-control/TagsControl";
import getTags from "@/services/getTags";

import "./Title.less";

function getPredictionTags() {
  return getTags("api/predictions/tags").then(tags => map(tags, t => t.name)) || [];
}

export default function Title({ 
  prediction, 
  name, 
  children, 
  tagsExtra,
  onChange,  
  canEdit,
  setPredictionTags,
}) {
  const defaultName = getDefaultName(prediction);


  return (
    <div className="predictions-header">
      <div className="title-with-tags">
        <div className="page-title">
          <div className="d-flex align-items-center">
            {prediction.id && <FavoritesControl item={prediction} />}
            <h3>
              {name || defaultName}
            </h3>
          </div>
        </div>
        <div className="predictions-tags">
          <PredictionsTagsControl
            tags={prediction.tags}
            isArchived={prediction.is_archived}
            canEdit={canEdit}
            getAvailableTags={getPredictionTags}
            onEdit={setPredictionTags}
            tagsExtra={tagsExtra}
          />
        </div>
      </div>
      <div className="header-actions">{children}</div>
    </div>
  );
}

Title.propTypes = {
  prediction: PredictionType.isRequired,
  name: PropTypes.string,
  children: PropTypes.node,
  onChange: PropTypes.func,
  editMode: PropTypes.bool,
  tagsExtra: PropTypes.node,
};

Title.defaultProps = {
  name: null,
  children: null,
  editMode: false,
  tagsExtra: null,
  onChange: () => {},
};
