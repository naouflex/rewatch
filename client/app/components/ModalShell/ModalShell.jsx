import React from "react";
import PropTypes from "prop-types";
import cx from "classnames";
import Modal from "antd/lib/modal";
import { DialogPropType } from "@/components/DialogWrapper";
import ModalFooter from "./ModalFooter";

import "./modal-shell.less";

const SIZE_WIDTH = {
  sm: 480,
  md: 560,
  lg: 720,
  xl: 960,
};

function renderTitle(title, description) {
  if (!description) {
    return title;
  }

  return (
    <div className="modal-shell__title-block">
      <div className="modal-shell__title">{title}</div>
      <div className="modal-shell__description">{description}</div>
    </div>
  );
}

export default function ModalShell({
  dialog,
  title,
  description,
  size,
  width,
  footer,
  footerExtra,
  customFooter,
  okText,
  cancelText,
  closeText,
  formId,
  onOk,
  onClose,
  showSubmit,
  children,
  className,
  bodyClassName,
  ...modalProps
}) {
  const resolvedWidth = width ?? SIZE_WIDTH[size] ?? SIZE_WIDTH.md;
  const footerVariant = footer === null ? "custom" : footer;

  const { footer: _ignoredFooter, okButtonProps, cancelButtonProps, ...restModalProps } = modalProps;

  const mergedOkButtonProps = { ...dialog.props.okButtonProps, ...okButtonProps };
  const mergedCancelButtonProps = { ...dialog.props.cancelButtonProps, ...cancelButtonProps };

  const dialogWithButtonProps = {
    ...dialog,
    props: {
      ...dialog.props,
      okButtonProps: mergedOkButtonProps,
      cancelButtonProps: mergedCancelButtonProps,
    },
  };

  const resolvedFooter =
    footer === "custom" ? (
      customFooter
    ) : footer === null ? null : (
      <ModalFooter
        dialog={dialogWithButtonProps}
        variant={footerVariant}
        okText={okText}
        cancelText={cancelText}
        closeText={closeText}
        formId={formId}
        onOk={onOk}
        onClose={onClose}
        showSubmit={showSubmit}
        extra={footerExtra}
      />
    );

  return (
    <Modal
      {...dialog.props}
      {...restModalProps}
      okButtonProps={mergedOkButtonProps}
      cancelButtonProps={mergedCancelButtonProps}
      className={cx("modal-shell", className)}
      rootClassName={cx("modal-shell-root", `modal-shell-root--${size}`, restModalProps.rootClassName)}
      title={renderTitle(title, description)}
      width={resolvedWidth}
      footer={resolvedFooter}
      onOk={onOk || dialog.props.onOk}
      onCancel={restModalProps.onCancel || dialog.props.onCancel}>
      <div className={cx("modal-shell__body", bodyClassName)}>{children}</div>
    </Modal>
  );
}

ModalShell.propTypes = {
  dialog: DialogPropType.isRequired,
  title: PropTypes.node.isRequired,
  description: PropTypes.node,
  size: PropTypes.oneOf(["sm", "md", "lg", "xl"]),
  width: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  footer: PropTypes.oneOf(["submit-cancel", "close", "custom", null]),
  footerExtra: PropTypes.node,
  customFooter: PropTypes.node,
  okText: PropTypes.string,
  cancelText: PropTypes.string,
  closeText: PropTypes.string,
  formId: PropTypes.string,
  onOk: PropTypes.func,
  onClose: PropTypes.func,
  showSubmit: PropTypes.bool,
  children: PropTypes.node,
  className: PropTypes.string,
  bodyClassName: PropTypes.string,
};

ModalShell.defaultProps = {
  description: null,
  size: "md",
  width: null,
  footer: "submit-cancel",
  footerExtra: null,
  customFooter: null,
  okText: "Save",
  cancelText: "Cancel",
  closeText: "Close",
  formId: null,
  onOk: null,
  onClose: null,
  showSubmit: true,
  children: null,
  className: null,
  bodyClassName: null,
};
