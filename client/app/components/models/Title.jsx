import React from "react";
import PropTypes from "prop-types";
import Input from "antd/lib/input";
import { getDefaultName } from "../../pages/ml-model/MLModel";
import map from "lodash";
import { MLModel as MLModelType } from "@/components/proptypes";
import FavoritesControl from "@/components/FavoritesControl";
import { MLModelTagsControl } from "@/components/tags-control/TagsControl";
import getTags from "@/services/getTags";

import { useTheme } from "@/components/ThemeProvider";

import "./Title.less";

function getMLModelTags() {
  return getTags("api/ml_models/tags").then(tags => map(tags, t => t.name)) || [];
}

export default function Title({ 
  model, 
  editMode, 
  name, 
  children, 
  tagsExtra,
  onChange,  
  canEdit,
  setModelTags,
}) {
  const defaultName = getDefaultName(model);
  const { isDarkMode } = useTheme();

  return (
    <div className={`model-header ${isDarkMode ? 'dark-mode' : ''}`}>
      <div className={`title-with-tags ${isDarkMode ? 'dark-mode' : ''}`}>
        <div className={`page-title ${isDarkMode ? 'dark-mode' : ''}`}>
          <div className={`d-flex align-items-center ${isDarkMode ? 'dark-mode' : ''}`}>
            {model.id && <FavoritesControl item={model} />}
            <h3>
              {editMode ? (
                <Input
                  className="f-inherit"
                  placeholder={model.query ? defaultName : "Model name"}
                  value={name}
                  aria-label="Model title"
                  onChange={e => onChange(e.target.value)}
                />
              ) : (
                name || defaultName
              )}
            </h3>
          </div>
        </div>
        <div className={`model-tags ${isDarkMode ? 'dark-mode' : ''}`}>
          <MLModelTagsControl
            tags={model.tags}
            isArchived={model.is_archived}
            canEdit={canEdit}
            getAvailableTags={getMLModelTags}
            onEdit={setModelTags}
            tagsExtra={tagsExtra}
          />
        </div>
      </div>
      <div className={`header-actions ${isDarkMode ? 'dark-mode' : ''}`}>
        {children}
      </div>
    </div>
  );
}

Title.propTypes = {
  model: MLModelType.isRequired,
  editMode: PropTypes.bool,
  name: PropTypes.string,
  children: PropTypes.node,
  tagsExtra: PropTypes.node,
  onChange: PropTypes.func,
  canEdit: PropTypes.bool,
  setModelTags: PropTypes.func,
};

Title.defaultProps = {
  editMode: false,
  name: null,
  children: null,
  tagsExtra: null,
  onChange: () => {},
  canEdit: false,
  setModelTags: () => {},
};
