import { toString } from "lodash";
import { markdown } from "markdown";
import React, { useState, useEffect, useCallback } from "react";
import PropTypes from "prop-types";
import { useDebouncedCallback } from "use-debounce";
import Checkbox from "antd/lib/checkbox";
import Input from "antd/lib/input";
import Tooltip from "@/components/Tooltip";
import Link from "@/components/Link";
import HtmlContent from "@rewatch/viz/lib/components/HtmlContent";
import { wrap as wrapDialog, DialogPropType } from "@/components/DialogWrapper";
import { ModalShell, ModalSection } from "@/components/ModalShell";
import { confirmDialog } from "@/components/ModalShell/confirmDialog";
import notification from "@/services/notification";

import "./TextboxDialog.less";

function renderPreview(text, renderAsHtml) {
  if (!text) {
    return null;
  }
  return renderAsHtml ? text : markdown.toHTML(text);
}

function TextboxDialog({ dialog, isNew, ...props }) {
  const [text, setText] = useState(toString(props.text));
  const [renderAsHtml, setRenderAsHtml] = useState(!!props.renderAsHtml);
  const [preview, setPreview] = useState(null);

  useEffect(() => {
    setText(props.text);
    setRenderAsHtml(!!props.renderAsHtml);
    setPreview(renderPreview(props.text, props.renderAsHtml));
  }, [props.text, props.renderAsHtml]);

  const [updatePreview] = useDebouncedCallback(() => {
    setPreview(renderPreview(text, renderAsHtml));
  }, 200);

  const handleInputChange = useCallback(
    event => {
      setText(event.target.value);
      updatePreview();
    },
    [updatePreview]
  );

  const handleRenderModeChange = useCallback(
    event => {
      setRenderAsHtml(event.target.checked);
      updatePreview();
    },
    [updatePreview]
  );

  const saveWidget = useCallback(() => {
    dialog.close({ text, renderAsHtml }).catch(err => {
      const detail = err?.response?.data?.message || err?.message;
      notification.error(
        isNew ? "Widget could not be added" : "Widget could not be saved",
        detail || undefined
      );
    });
  }, [dialog, isNew, text, renderAsHtml]);

  const confirmDialogDismiss = useCallback(() => {
    const originalText = props.text;
    const originalRenderAsHtml = !!props.renderAsHtml;
    if (text !== originalText || renderAsHtml !== originalRenderAsHtml) {
      confirmDialog({
        title: "Quit editing?",
        description: "Changes you made so far will not be saved. Are you sure?",
        variant: "danger",
        okText: "Yes, quit",
        onConfirm: () => dialog.dismiss(),
      });
    } else {
      dialog.dismiss();
    }
  }, [dialog, text, renderAsHtml, props.text, props.renderAsHtml]);

  return (
    <ModalShell
      dialog={dialog}
      title={isNew ? "Add Textbox" : "Edit Textbox"}
      description="Write markdown or HTML content to display on your dashboard."
      size="md"
      onOk={saveWidget}
      onCancel={confirmDialogDismiss}
      okText={isNew ? "Add to Dashboard" : "Save"}
      wrapProps={{ "data-test": "TextboxDialog" }}>
      <ModalSection title="Content">
        <Input.TextArea
          className="resize-vertical"
          rows="5"
          value={text}
          aria-label="Textbox widget content"
          onChange={handleInputChange}
          autoFocus
          placeholder={renderAsHtml ? "<p>Your HTML here</p>" : "This is where you write some text"}
        />
        <div className="textbox-dialog__options">
          <Checkbox checked={renderAsHtml} onChange={handleRenderModeChange} data-test="TextboxRenderAsHtml">
            Render as HTML
          </Checkbox>
          <small>
            {renderAsHtml ? (
              <>HTML is sanitized before display. Scripts and unsafe tags are removed. Use for images:{" "}
                <code>{`<img src="https://…" alt="…">`}</code></>
            ) : (
              <>
                Supports basic{" "}
                <Link
                  target="_blank"
                  rel="noopener noreferrer"
                  href="https://www.markdownguide.org/cheat-sheet/#basic-syntax">
                  <Tooltip title="Markdown guide opens in new window">Markdown</Tooltip>
                </Link>
                .
              </>
            )}
          </small>
        </div>
      </ModalSection>
      {text && (
        <ModalSection title="Preview">
          <HtmlContent className="preview markdown">{preview}</HtmlContent>
        </ModalSection>
      )}
    </ModalShell>
  );
}

TextboxDialog.propTypes = {
  dialog: DialogPropType.isRequired,
  isNew: PropTypes.bool,
  text: PropTypes.string,
  renderAsHtml: PropTypes.bool,
};

TextboxDialog.defaultProps = {
  isNew: false,
  text: "",
  renderAsHtml: false,
};

export default wrapDialog(TextboxDialog);
