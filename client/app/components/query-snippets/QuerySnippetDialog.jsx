import { isNil, get, map, compact, trim } from "lodash";
import React, { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import DynamicForm from "@/components/dynamic-form/DynamicForm";
import { wrap as wrapDialog, DialogPropType } from "@/components/DialogWrapper";
import { ModalShell } from "@/components/ModalShell";
import { useUniqueId } from "@/lib/hooks/useUniqueId";

function QuerySnippetDialog({ querySnippet, dialog, readOnly, getAvailableTags }) {
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
      const querySnippetId = get(querySnippet, "id");

      if (isNil(values.description)) {
        values.description = "";
      }

      values.tags = compact(map(values.tags || [], trim));

      dialog
        .close(querySnippetId ? { id: querySnippetId, ...values } : values)
        .then(() => successCallback("Saved."))
        .catch(() => errorCallback("Failed saving snippet."));
    },
    [dialog, querySnippet]
  );

  const isEditing = !!get(querySnippet, "id");

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

  const querySnippetsFormId = useUniqueId("querySnippetForm");

  return (
    <ModalShell
      dialog={dialog}
      title={isEditing ? querySnippet.trigger : "Create Query Snippet"}
      description={
        readOnly
          ? "View snippet details and SQL template."
          : "Define a trigger keyword and reusable SQL snippet for the query editor."
      }
      size="lg"
      okText={isEditing ? "Save" : "Create"}
      cancelText={readOnly ? "Close" : "Cancel"}
      footer={readOnly ? "close" : "submit-cancel"}
      formId={readOnly ? null : querySnippetsFormId}
      wrapProps={{ "data-test": "QuerySnippetDialog" }}>
      <DynamicForm
        id={querySnippetsFormId}
        fields={formFields}
        onSubmit={handleSubmit}
        hideSubmitButton
        feedbackIcons
      />
    </ModalShell>
  );
}

QuerySnippetDialog.propTypes = {
  dialog: DialogPropType.isRequired,
  querySnippet: PropTypes.object,
  readOnly: PropTypes.bool,
  getAvailableTags: PropTypes.func,
};

QuerySnippetDialog.defaultProps = {
  querySnippet: null,
  readOnly: false,
  getAvailableTags: null,
};

export default wrapDialog(QuerySnippetDialog);
