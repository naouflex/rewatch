import { includes, words, capitalize, clone, isNull } from "lodash";
import React, { useState, useEffect, useMemo } from "react";
import PropTypes from "prop-types";
import Checkbox from "antd/lib/checkbox";
import Form from "antd/lib/form";
import Select from "antd/lib/select";
import Input from "antd/lib/input";
import { wrap as wrapDialog, DialogPropType } from "@/components/DialogWrapper";
import { ModalShell, ModalSection } from "@/components/ModalShell";
import QuerySelector from "@/components/QuerySelector";
import { Query } from "@/services/query";
import { useUniqueId } from "@/lib/hooks/useUniqueId";
import { getModalFormProps } from "@/styles/formStyle";
import "./EditParameterSettingsDialog.less";

const { Option, OptGroup } = Select;

function getDefaultTitle(text) {
  return capitalize(words(text).join(" "));
}

function isTypeDateRange(type) {
  return /-range/.test(type);
}

function joinExampleList(multiValuesOptions) {
  const { prefix, suffix } = multiValuesOptions;
  return ["value1", "value2", "value3"].map(value => `${prefix}${value}${suffix}`).join(",");
}

function usageSnippet(name, type) {
  if (!name) {
    return null;
  }
  if (isTypeDateRange(type)) {
    return `{{ ${name}.start }} … {{ ${name}.end }}`;
  }
  return `{{ ${name} }}`;
}

function NameInput({ name, type, onChange, existingNames, onValidityChange }) {
  useEffect(() => {
    if (!name || includes(existingNames, name)) {
      onValidityChange(false);
    } else {
      onValidityChange(true);
    }
  }, [name, existingNames, onValidityChange]);

  let helpText = "Choose a keyword for this parameter (letters, numbers, underscores).";
  let validateStatus = "";

  if (!name) {
    validateStatus = "error";
  } else if (includes(existingNames, name)) {
    helpText = "A parameter with this keyword already exists.";
    validateStatus = "error";
  } else if (isTypeDateRange(type)) {
    helpText = `Appears in query as {{ ${name}.start }} and {{ ${name}.end }}.`;
  }

  return (
    <Form.Item required label="Keyword" help={helpText} validateStatus={validateStatus || undefined}>
      <Input value={name} onChange={e => onChange(e.target.value)} autoFocus data-test="ParameterKeywordInput" />
    </Form.Item>
  );
}

NameInput.propTypes = {
  name: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  existingNames: PropTypes.arrayOf(PropTypes.string).isRequired,
  onValidityChange: PropTypes.func.isRequired,
  type: PropTypes.string.isRequired,
};

function EditParameterSettingsDialog(props) {
  const [param, setParam] = useState(clone(props.parameter));
  const [isNameValid, setIsNameValid] = useState(true);
  const [initialQuery, setInitialQuery] = useState();
  const [userInput, setUserInput] = useState(param.regex || "");
  const [isValidRegex, setIsValidRegex] = useState(true);

  const isNew = !props.parameter.name;

  useEffect(() => {
    const queryId = props.parameter.queryId;
    if (queryId) {
      Query.get({ id: queryId }).then(setInitialQuery);
    }
  }, [props.parameter.queryId]);

  const usage = useMemo(() => usageSnippet(param.name, param.type), [param.name, param.type]);

  function isFulfilled() {
    if (!isNameValid) {
      return false;
    }
    if (param.title === "") {
      return false;
    }
    if (param.type === "query" && !param.queryId) {
      return false;
    }
    if (param.type === "text-pattern" && !isValidRegex) {
      return false;
    }
    return true;
  }

  function onConfirm() {
    const payload = { ...param };
    if (!payload.title) {
      payload.title = getDefaultTitle(payload.name);
    }
    props.dialog.close(payload);
  }

  const paramFormId = useUniqueId("paramForm");

  const handleRegexChange = e => {
    setUserInput(e.target.value);
    try {
      new RegExp(e.target.value);
      setParam({ ...param, regex: e.target.value });
      setIsValidRegex(true);
    } catch (error) {
      setIsValidRegex(false);
    }
  };

  const showOptionsSection =
    param.type === "text-pattern" ||
    param.type === "enum" ||
    param.type === "query" ||
    ((param.type === "enum" || param.type === "query") && param.multiValuesOptions);

  return (
    <ModalShell
      dialog={props.dialog}
      title={isNew ? "Add Parameter" : "Parameter Settings"}
      description={
        isNew
          ? "Define a query filter users can change before running the query."
          : "Update how this parameter appears and behaves."
      }
      size="md"
      okText={isNew ? "Add Parameter" : "Save"}
      formId={paramFormId}
      okButtonProps={{ disabled: !isFulfilled() }}
      wrapProps={{ "data-test": "EditParameterSettingsDialog" }}>
      <Form {...getModalFormProps()} onFinish={onConfirm} id={paramFormId}>
        <ModalSection title="Display">
          {isNew ? (
            <NameInput
              name={param.name}
              onChange={name => setParam({ ...param, name })}
              onValidityChange={setIsNameValid}
              existingNames={props.existingParams}
              type={param.type}
            />
          ) : (
            <Form.Item label="Keyword">
              <Input value={param.name} disabled data-test="ParameterKeywordReadOnly" />
            </Form.Item>
          )}
          <Form.Item required label="Title" help="Label shown above the parameter input.">
            <Input
              value={isNull(param.title) ? getDefaultTitle(param.name) : param.title}
              onChange={e => setParam({ ...param, title: e.target.value })}
              data-test="ParameterTitleInput"
            />
          </Form.Item>
          {usage && (
            <Form.Item label="Usage in query">
              <code className="parameter-settings-dialog__usage">{usage}</code>
            </Form.Item>
          )}
        </ModalSection>

        <ModalSection title="Type">
          <Form.Item label="Value type" help="Controls the input shown when running the query.">
            <Select value={param.type} onChange={type => setParam({ ...param, type })} data-test="ParameterTypeSelect">
              <OptGroup label="Text & numbers">
                <Option value="text" data-test="TextParameterTypeOption">
                  Text
                </Option>
                <Option value="text-pattern">Text pattern (regex)</Option>
                <Option value="number" data-test="NumberParameterTypeOption">
                  Number
                </Option>
                <Option value="enum">Dropdown list</Option>
                <Option value="query">Query-based dropdown</Option>
              </OptGroup>
              <OptGroup label="Date & time">
                <Option value="date" data-test="DateParameterTypeOption">
                  Date
                </Option>
                <Option value="datetime-local" data-test="DateTimeParameterTypeOption">
                  Date and time
                </Option>
                <Option value="datetime-with-seconds">Date and time (with seconds)</Option>
                <Option value="date-range" data-test="DateRangeParameterTypeOption">
                  Date range
                </Option>
                <Option value="datetime-range">Date and time range</Option>
                <Option value="datetime-range-with-seconds">Date and time range (with seconds)</Option>
              </OptGroup>
            </Select>
          </Form.Item>
        </ModalSection>

        {showOptionsSection && (
          <ModalSection title="Options">
            {param.type === "text-pattern" && (
              <Form.Item
                label="Validation pattern"
                help={!isValidRegex ? "Enter a valid regular expression." : "Value must match this pattern."}
                validateStatus={!isValidRegex ? "error" : undefined}>
                <Input
                  value={userInput}
                  onChange={handleRegexChange}
                  className={!isValidRegex ? "input-error" : ""}
                  data-test="RegexPatternInput"
                />
              </Form.Item>
            )}
            {param.type === "enum" && (
              <Form.Item label="Dropdown values" help="One option per line.">
                <Input.TextArea
                  rows={4}
                  value={param.enumOptions}
                  onChange={e => setParam({ ...param, enumOptions: e.target.value })}
                />
              </Form.Item>
            )}
            {param.type === "query" && (
              <Form.Item label="Source query" help="First column values populate the dropdown.">
                <QuerySelector
                  selectedQuery={initialQuery}
                  onChange={q => setParam({ ...param, queryId: q && q.id })}
                  type="select"
                />
              </Form.Item>
            )}
            {(param.type === "enum" || param.type === "query") && (
              <Form.Item className="m-b-0">
                <Checkbox
                  checked={!!param.multiValuesOptions}
                  onChange={e =>
                    setParam({
                      ...param,
                      multiValuesOptions: e.target.checked
                        ? {
                            prefix: "",
                            suffix: "",
                            separator: ",",
                          }
                        : null,
                    })
                  }
                  data-test="AllowMultipleValuesCheckbox">
                  Allow multiple values
                </Checkbox>
              </Form.Item>
            )}
            {(param.type === "enum" || param.type === "query") && param.multiValuesOptions && (
              <Form.Item
                label="Quotation"
                help={
                  <>
                    Inserted in query as: <code>{joinExampleList(param.multiValuesOptions)}</code>
                  </>
                }>
                <Select
                  value={param.multiValuesOptions.prefix}
                  onChange={quoteOption =>
                    setParam({
                      ...param,
                      multiValuesOptions: {
                        ...param.multiValuesOptions,
                        prefix: quoteOption,
                        suffix: quoteOption,
                      },
                    })
                  }
                  data-test="QuotationSelect">
                  <Option value="">None</Option>
                  <Option value="'">Single quotes</Option>
                  <Option value={'"'} data-test="DoubleQuotationMarkOption">
                    Double quotes
                  </Option>
                </Select>
              </Form.Item>
            )}
          </ModalSection>
        )}
      </Form>
    </ModalShell>
  );
}

EditParameterSettingsDialog.propTypes = {
  parameter: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
  dialog: DialogPropType.isRequired,
  existingParams: PropTypes.arrayOf(PropTypes.string),
};

EditParameterSettingsDialog.defaultProps = {
  existingParams: [],
};

export default wrapDialog(EditParameterSettingsDialog);
