import React from "react";
import PropTypes from "prop-types";

import Link from "@/components/Link";
import { MLModel as MLModelType } from "@/components/proptypes";

import Tooltip from "@/components/Tooltip";

import InfoCircleFilledIcon from "@ant-design/icons/InfoCircleFilled";
import QuestionCircleTwoToneIcon from "@ant-design/icons/QuestionCircleTwoTone";

import "./Model.less"; // Create a similar CSS file to style the component

export default function MLModelFormItem({ model }) {
  const modelHint = (
    <small>
      {model?.name ? (
        <>
          <InfoCircleFilledIcon className="ok-icon" /> This model is available in the model list view.{" "}
          <Tooltip title="Go to the model view to see the model details."></Tooltip>
        </>
      ) : (
        <>
          <InfoCircleFilledIcon className="warning-icon-danger" /> This model might have been deleted. Please get in touch wih an admin.{" "}
          <Tooltip title="Model not found."></Tooltip>
        </>
      )}
    </small>
  );

  return (
    <>
    {model?.name ? (
      <>
      <Tooltip title="Open model in a new tab.">
        <Link href={`ml_models/${model.id}/overview`} target="_blank" rel="noopener noreferrer" className="prediction-link">
          {model.name} <i className="fa fa-external-link" aria-hidden="true" />
          <span className="sr-only">(opens in a new tab)</span>
        </Link>
      </Tooltip>
      <div className="ant-form-item-explain">{model && modelHint}</div>
      </>
    ) : (
      <>
      <div className="ant-form-item-explain">
        <QuestionCircleTwoToneIcon className="warning-icon-danger" /> Not found.
      </div>
      </>)
      }
    </>
  );
}

MLModelFormItem.propTypes = {
  model: MLModelType,
  onChange: PropTypes.func,
  editMode: PropTypes.bool,
};

MLModelFormItem.defaultProps = {
  model: null,
  onChange: () => {},
  editMode: false,
};
