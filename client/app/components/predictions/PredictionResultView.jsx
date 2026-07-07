import React from "react";
import PropTypes from "prop-types";

import TimeAgo from "@/components/TimeAgo";
import { PredictionResult as PredictionType } from "@/components/proptypes";

import Form from "antd/lib/form";
import * as Grid from "antd/lib/grid";

import Title from "../../components/predictions/Title";
import PredictionFormItem from "../../components/predictions/Model";
import QueryFormItem from "../../components/predictions/Query";

import HorizontalFormItem from "@/components/HorizontalFormItem";
import DynamicComponent from "@/components/DynamicComponent";
import JsonViewInteractive from "@/components/json-view-interactive/JsonViewInteractive";
import { useTheme } from "@/components/ThemeProvider";
import "./PredictionResultView.less";

export default function PredictionView({ prediction, canEdit, menuButton, onChange, setPredictionTags, name }) {
  const { isDarkMode } = useTheme();

  const { query, model, content, created_at, additional_properties } = prediction;


  let parsedContent;
  try {
    parsedContent = typeof content === "string" ? JSON.parse(content) : content;
  } catch (e) {
    parsedContent = content;
  }

  let parsedAdditionalProperties;
  try {
    parsedAdditionalProperties = typeof additional_properties === "string" ? JSON.parse(additional_properties) : additional_properties;
  } catch (e) {
    parsedAdditionalProperties = additional_properties;
  }



  return (
    <>
      <div className="create-page-form__header">
        <Title
          name={name}
          prediction={prediction}
          editMode={false}
          tagsExtra={null}
          onChange={onChange}
          canEdit={canEdit}
          setPredictionTags={setPredictionTags}
        >
          <DynamicComponent name="PredictionView.HeaderExtra" prediction={prediction} />
          {menuButton}
        </Title>
      </div>
      <div className="create-page-form__body">
        <Grid.Row type="flex" gutter={16}>
          <Grid.Col xs={24} md={16} className="d-flex">
            <Form className="flex-fill">
              <HorizontalFormItem label="Created At">
                {Date(created_at).toLocaleString()} (<TimeAgo date={created_at} />)
              </HorizontalFormItem>
              <HorizontalFormItem label="Query">
                <QueryFormItem query={query} editMode={false} />
              </HorizontalFormItem>
              <HorizontalFormItem label="Model">
                <PredictionFormItem model={model} />
              </HorizontalFormItem>
              <HorizontalFormItem label="Content">
                {typeof parsedContent === "object" ? (
                  <JsonViewInteractive value={parsedContent} darkMode={isDarkMode} />
                ) : (
                  <pre>{String(parsedContent)}</pre>
                )}
              </HorizontalFormItem>
              <HorizontalFormItem label="Additional Properties">
                {typeof parsedAdditionalProperties === "object" ? (
                  <JsonViewInteractive value={parsedAdditionalProperties} darkMode={isDarkMode} />
                ) : (
                  <pre>{String(parsedAdditionalProperties)}</pre>
                )}
              </HorizontalFormItem>
            </Form>
          </Grid.Col>
        </Grid.Row>
      </div>
    </>
  );
}

PredictionView.propTypes = {
  prediction: PredictionType.isRequired,
  canEdit: PropTypes.bool.isRequired,
  menuButton: PropTypes.node.isRequired,
  favorite: PropTypes.func.isRequired,
  unfavorite: PropTypes.func.isRequired,
  archive: PropTypes.func.isRequired,
  unarchive: PropTypes.func.isRequired,
  onChange: PropTypes.func.isRequired,
  setPredictionTags: PropTypes.func.isRequired,
};

PredictionView.defaultProps = {
  queryResult: null,
  content:null,
};
