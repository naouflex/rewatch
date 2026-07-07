import Modal from "antd/lib/modal";

/**
 * Consistent confirm / warning dialogs with shared styling.
 *
 * @param {object} options
 * @param {string} options.title
 * @param {string} [options.description] - body text (alias: content)
 * @param {string} [options.content]
 * @param {"default"|"danger"|"warning"} [options.variant]
 * @param {string} [options.okText]
 * @param {string} [options.cancelText]
 * @param {() => void|Promise<void>} [options.onConfirm]
 * @param {() => void} [options.onCancel]
 */
export function confirmDialog({
  title,
  description,
  content,
  variant = "default",
  okText,
  cancelText = "Cancel",
  onConfirm,
  onCancel,
}) {
  const body = description ?? content ?? "";
  const isDanger = variant === "danger";
  const isWarning = variant === "warning";

  const modalFn = isWarning ? Modal.warning : Modal.confirm;

  return modalFn({
    title,
    content: body,
    okText: okText || (isDanger ? "Delete" : "OK"),
    cancelText,
    okButtonProps: isDanger ? { danger: true } : undefined,
    className: "modal-shell-confirm",
    centered: true,
    onOk: onConfirm,
    onCancel,
  });
}

export default confirmDialog;
