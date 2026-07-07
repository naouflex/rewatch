import React from "react";
import PropTypes from "prop-types";
import Button from "antd/lib/button";

export default function ModalFooter({
  dialog,
  variant,
  okText,
  cancelText,
  closeText,
  formId,
  onOk,
  onClose,
  showSubmit,
  extra,
}) {
  if (variant === "close") {
    return (
      <Button {...dialog.props.cancelButtonProps} onClick={onClose || dialog.dismiss}>
        {closeText}
      </Button>
    );
  }

  if (variant === "custom") {
    return null;
  }

  return (
    <div className="modal-shell__footer-inner">
      {extra && <div className="modal-shell__footer-extra">{extra}</div>}
      <div className="modal-shell__footer-actions">
        <Button {...dialog.props.cancelButtonProps} onClick={dialog.dismiss}>
          {cancelText}
        </Button>
        {showSubmit && (
          <Button
            {...dialog.props.okButtonProps}
            type="primary"
            htmlType={formId ? "submit" : "button"}
            form={formId || undefined}
            onClick={formId ? undefined : onOk || dialog.props.onOk}>
            {okText}
          </Button>
        )}
      </div>
    </div>
  );
}

ModalFooter.propTypes = {
  dialog: PropTypes.shape({
    props: PropTypes.object.isRequired,
    dismiss: PropTypes.func.isRequired,
  }).isRequired,
  variant: PropTypes.oneOf(["submit-cancel", "close", "custom"]).isRequired,
  okText: PropTypes.string,
  cancelText: PropTypes.string,
  closeText: PropTypes.string,
  formId: PropTypes.string,
  onOk: PropTypes.func,
  onClose: PropTypes.func,
  showSubmit: PropTypes.bool,
  extra: PropTypes.node,
};

ModalFooter.defaultProps = {
  okText: "Save",
  cancelText: "Cancel",
  closeText: "Close",
  formId: null,
  onOk: null,
  onClose: null,
  showSubmit: true,
  extra: null,
};
