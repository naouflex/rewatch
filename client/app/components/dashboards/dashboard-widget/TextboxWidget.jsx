import React, { useState } from "react";
import PropTypes from "prop-types";
import { markdown } from "markdown";
import HtmlContent from "@rewatch/viz/lib/components/HtmlContent";
import TextboxDialog from "@/components/dashboards/TextboxDialog";
import Widget from "./Widget";

function TextboxWidget(props) {
  const { widget, canEdit } = props;
  const [text, setText] = useState(widget.text);
  const renderAsHtml = !!widget.options?.renderAsHtml;

  const editTextBox = () => {
    TextboxDialog.showModal({
      text: widget.text,
      renderAsHtml,
    }).onClose(({ text: newText, renderAsHtml: newRenderAsHtml }) => {
      widget.text = newText;
      widget.options = { ...widget.options, renderAsHtml: !!newRenderAsHtml };
      setText(newText);
      return widget.save();
    });
  };

  const TextboxMenuOptions = [{ key: "edit", label: "Edit", onClick: editTextBox }];

  if (!widget.width) {
    return null;
  }

  const content = renderAsHtml ? text || "" : markdown.toHTML(text || "");

  return (
    <Widget {...props} menuOptions={canEdit ? TextboxMenuOptions : null} className="widget-text">
      <HtmlContent className="body-row-auto scrollbox t-body p-15 markdown">{content}</HtmlContent>
    </Widget>
  );
}

TextboxWidget.propTypes = {
  widget: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
  canEdit: PropTypes.bool,
};

TextboxWidget.defaultProps = {
  canEdit: false,
};

export default TextboxWidget;
