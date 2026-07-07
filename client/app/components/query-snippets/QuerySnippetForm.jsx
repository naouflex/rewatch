import { isNil, get, map, compact, trim } from "lodash";
import React, { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";

import Button from "antd/lib/button";
import DynamicForm from "@/components/dynamic-form/DynamicForm";
import Link from "@/components/Link";
import { useUniqueId } from "@/lib/hooks/useUniqueId";

import "@/components/items-list/create-page-layout.less";

export default function QuerySnippetForm({ querySnippet, readOnly, getAvailableTags, onSubmit, saving }) {
  const [availableTags, setAvailableTags] = useState([]);
  const [tagsLoading, setTagsLoading] = useState(!!getAvailableTags);

  useEffect(() => {
    if (!getAvailableTags) {
      setTagsLoading(false);
      return undefined;
    }

    let cancelled = false;
    getAvailableTags()
      .then(tags => {
        if (!cancelled) {
          setAvailableTags(tags);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setTagsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [getAvailableTags]);

  const handleSubmit = useCallback(
    (values, successCallback, errorCallback) => {
      if (isNil(values.description)) {
        values.description = "";
      }

      values.tags = compact(map(values.tags || [], trim));

      onSubmit(values)
        .then(() => successCallback("Saved."))
        .catch(() => errorCallback("Failed saving snippet."));
    },
    [onSubmit]
  );

  const isEditing = !!get(querySnippet, "id");
  const formId = useUniqueId("querySnippetForm");

  const formFields = [
    { name: "trigger", title: "Trigger", type: "text", required: true, autoFocus: !isEditing },
    { name: "description", title: "Description", type: "text" },
    {
      name: "tags",
      title: "Tags",
      type: "select",
      mode: "tags",
      options: map(availableTags, tag => ({ value: tag, name: tag })),
      loading: tagsLoading,
      initialValue: get(querySnippet, "tags", []),
      placeholder: "Add tags...",
      props: readOnly ? { disabled: true } : undefined,
    },
    { name: "snippet", title: "Snippet", type: "ace", required: true },
  ].map(field => ({
    ...field,
    readOnly,
    initialValue:
      field.name === "tags" ? get(querySnippet, "tags", []) : get(querySnippet, field.name, field.initialValue ?? ""),
  }));

  return (
    <div data-test="QuerySnippetForm">
      <DynamicForm
        id={formId}
        fields={formFields}
        onSubmit={handleSubmit}
        hideSubmitButton
        feedbackIcons
      />
      {!readOnly && (
        <div className="create-page-form__footer">
          <Button type="primary" htmlType="submit" form={formId} loading={saving} data-test="SaveQuerySnippetButton">
            {isEditing ? "Save" : "Create"}
          </Button>
          <Link.Button href="query_snippets" disabled={saving}>
            Cancel
          </Link.Button>
        </div>
      )}
    </div>
  );
}

QuerySnippetForm.propTypes = {
  querySnippet: PropTypes.object,
  readOnly: PropTypes.bool,
  getAvailableTags: PropTypes.func,
  onSubmit: PropTypes.func.isRequired,
  saving: PropTypes.bool,
};

QuerySnippetForm.defaultProps = {
  querySnippet: null,
  readOnly: false,
  getAvailableTags: null,
  saving: false,
};
