import { toString } from "lodash";
import { markdown } from "markdown";
import React, { useState, useEffect, useCallback } from "react";
import PropTypes from "prop-types";
import { useDebouncedCallback } from "use-debounce";
import Input from "antd/lib/input";
import Tooltip from "@/components/Tooltip";
import Link from "@/components/Link";
import HtmlContent from "@rewatch/viz/lib/components/HtmlContent";
import { wrap as wrapDialog, DialogPropType } from "@/components/DialogWrapper";
import { ModalShell, ModalSection } from "@/components/ModalShell";
import { confirmDialog } from "@/components/ModalShell/confirmDialog";
import notification from "@/services/notification";

import "./TextboxDialog.less";

function TextboxDialog({ dialog, isNew, ...props }) {
  const [text, setText] = useState(toString(props.text));
  const [preview, setPreview] = useState(null);

  useEffect(() => {
    setText(props.text);
    setPreview(markdown.toHTML(props.text));
  }, [props.text]);

  const [updatePreview] = useDebouncedCallback(() => {
    setPreview(markdown.toHTML(text));
  }, 200);

  const handleInputChange = useCallback(
    event => {
      setText(event.target.value);
      updatePreview();
    },
    [updatePreview]
  );

  const saveWidget = useCallback(() => {
    dialog.close(text).catch(() => {
      notification.error(isNew ? "Widget could not be added" : "Widget could not be saved");
    });
  }, [dialog, isNew, text]);

  const confirmDialogDismiss = useCallback(() => {
    const originalText = props.text;
    if (text !== originalText) {
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
  }, [dialog, text, props.text]);

  return (
    <ModalShell
      dialog={dialog}
      title={isNew ? "Add Textbox" : "Edit Textbox"}
      description="Write markdown content to display on your dashboard."
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
          placeholder="This is where you write some text"
        />
        <small>
          Supports basic{" "}
          <Link
            target="_blank"
            rel="noopener noreferrer"
            href="https://www.markdownguide.org/cheat-sheet/#basic-syntax">
            <Tooltip title="Markdown guide opens in new window">Markdown</Tooltip>
          </Link>
          .
        </small>
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
};

TextboxDialog.defaultProps = {
  isNew: false,
  text: "",
};

export default wrapDialog(TextboxDialog);
