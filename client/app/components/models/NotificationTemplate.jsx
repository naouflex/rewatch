import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { head, isEmpty, isNull, isUndefined } from "lodash";
import Mustache from "mustache";

import HelpTrigger from "@/components/HelpTrigger";
import { MLModel as ModelType, Query as QueryType } from "@/components/proptypes";

import Input from "antd/lib/input";
import Select from "antd/lib/select";
import Modal from "antd/lib/modal";
import Switch from "antd/lib/switch";

import "./NotificationTemplate.less";

function normalizeCustomTemplateData(model, query, columnNames, resultValues, templateType) {
  const topValue = !isEmpty(resultValues) ? head(resultValues)[model.options[`column_${templateType}`]] : null;

  return {
    MODEL_STATUS: templateType === 'train' ? "TRAINED" : "PREDICTED",
    MODEL_CONDITION: model.options[`op_${templateType}`],
    MODEL_THRESHOLD: model.options[`value_${templateType}`],
    MODEL_NAME: model.name,
    MODEL_URL: `${window.location.origin}/ml_models/${model.id}`,
    QUERY_NAME: query.name,
    QUERY_URL: `${window.location.origin}/queries/${query.id}`,
    QUERY_RESULT_VALUE: isNull(topValue) || isUndefined(topValue) ? "UNKNOWN" : topValue,
    QUERY_RESULT_ROWS: resultValues,
    QUERY_RESULT_COLS: columnNames,
  };
}

function NotificationTemplate({ model, query, columnNames, resultValues, subject, setSubject, body, setBody, templateType, disabled }) {
  const [enabled, setEnabled] = useState(subject || body ? 1 : 0);
  const [showPreview, setShowPreview] = useState(false);
  const [localSubject, setLocalSubject] = useState(subject);
  const [localBody, setLocalBody] = useState(body);

  useEffect(() => {
    setLocalSubject(subject);
    setLocalBody(body);
  }, [subject, body]);

  const onEnabledChange = value => {
    if (disabled) return;
    if (value) {
      setEnabled(value);
      setShowPreview(false);
    } else {
      Modal.confirm({
        title: "Are you sure?",
        content: "Switching to default template will discard your custom template.",
        onOk: () => {
          setEnabled(0);
          setTimeout(() => {
            setShowPreview(false);
            setTimeout(() => {
              setLocalSubject("");
              setTimeout(() => {
                setLocalBody("");
                setTimeout(() => {
                  setSubject("");
                  setTimeout(() => {
                    setBody("");
                  }, 0);
                }, 0);
              }, 0);
            }, 0);
          }, 0);
        },
        maskClosable: true,
        autoFocusButton: null,
      });
    }
  };

  const handleSubjectChange = e => {
    if (disabled) return;
    const newSubject = e.target.value;
    setLocalSubject(newSubject);
    setSubject(newSubject);
    if (!enabled) {
      setEnabled(1);
    }
  };

  const handleBodyChange = e => {
    if (disabled) return;
    const newBody = e.target.value;
    setLocalBody(newBody);
    setBody(newBody);
    if (!enabled) {
      setEnabled(1);
    }
  };

  const renderData = normalizeCustomTemplateData(model, query, columnNames, resultValues, templateType);

  const render = tmpl => Mustache.render(tmpl || "", renderData);

  return (
    <div className="model-template">
      <Select
        value={enabled}
        onChange={onEnabledChange}
        optionLabelProp="label"
        dropdownMatchSelectWidth={false}
        style={{ width: "fit-content" }}
        disabled={disabled}>
        <Select.Option value={0} label="Use default template">
          Default template
        </Select.Option>
        <Select.Option value={1} label="Use custom template">
          Custom template
        </Select.Option>
      </Select>
      {enabled === 1 && (
        <div className="model-custom-template" data-test="ModelCustomTemplate">
          <div className="d-flex align-items-center">
            <h5 className="flex-fill">Subject / Body</h5>
            Preview{" "}
            <Switch size="small" className="model-template-preview" checked={showPreview} onChange={setShowPreview} disabled={disabled} />
          </div>
          <Input
            value={showPreview ? render(localSubject) : localSubject}
            aria-label="Subject"
            onChange={handleSubjectChange}
            disabled={showPreview || disabled}
            data-test="CustomSubject"
          />
          <Input.TextArea
            value={showPreview ? render(localBody) : localBody}
            aria-label="Body"
            autoSize={{ minRows: 9 }}
            onChange={handleBodyChange}
            disabled={showPreview || disabled}
            data-test="CustomBody"
          />
          <HelpTrigger type="MODEL_NOTIF_TEMPLATE_GUIDE" className="f-13">
            <i className="fa fa-question-circle" aria-hidden="true" /> Formatting guide{" "}
            <span className="sr-only">(help)</span>
          </HelpTrigger>
        </div>
      )}
    </div>
  );
}

NotificationTemplate.propTypes = {
  model: ModelType.isRequired,
  query: QueryType.isRequired,
  columnNames: PropTypes.arrayOf(PropTypes.string).isRequired,
  resultValues: PropTypes.arrayOf(PropTypes.any).isRequired,
  subject: PropTypes.string,
  body: PropTypes.string,
  setSubject: PropTypes.func.isRequired,
  setBody: PropTypes.func.isRequired,
  templateType: PropTypes.oneOf(['train', 'predict']).isRequired,
  disabled: PropTypes.bool,
};

NotificationTemplate.defaultProps = {
  subject: "",
  body: "",
  disabled: false,
};

export default NotificationTemplate;
