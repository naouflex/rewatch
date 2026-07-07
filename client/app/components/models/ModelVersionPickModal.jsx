import React from "react";
import PropTypes from "prop-types";
import Modal from "antd/lib/modal";
import Select from "antd/lib/select";
import Form from "antd/lib/form";

import "@/components/ModalShell/modal-shell.less";

function renderModalTitle(title, description) {
  if (!description) {
    return title;
  }

  return (
    <div className="modal-shell__title-block">
      <div className="modal-shell__title">{title}</div>
      {description && <div className="modal-shell__description">{description}</div>}
    </div>
  );
}

export default function ModelVersionPickModal({
  open,
  title,
  description,
  okText,
  cancelText,
  versions,
  value,
  onChange,
  onOk,
  onCancel,
  children,
  okButtonProps,
}) {
  return (
    <Modal
      open={open}
      title={renderModalTitle(title, description)}
      onOk={onOk}
      onCancel={onCancel}
      okText={okText}
      cancelText={cancelText}
      okButtonProps={okButtonProps}
      className="modal-shell"
      rootClassName="modal-shell-root modal-shell-root--md"
      destroyOnClose>
      <div className="modal-shell__body">
        {children ||
          (versions && (
            <Form layout="vertical" className="modal-shell-form">
              <Form.Item label="Version">
                <Select
                  className="w-100"
                  placeholder="Select a version"
                  onChange={onChange}
                  value={value}
                  size="large">
                  {versions.map(version => (
                    <Select.Option key={`${version.id || version.version}`} value={version.version}>
                      {version.name} v{version.version}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Form>
          ))}
      </div>
    </Modal>
  );
}

ModelVersionPickModal.propTypes = {
  open: PropTypes.bool.isRequired,
  title: PropTypes.string.isRequired,
  description: PropTypes.string,
  okText: PropTypes.string,
  cancelText: PropTypes.string,
  versions: PropTypes.array,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  onChange: PropTypes.func,
  onOk: PropTypes.func,
  onCancel: PropTypes.func.isRequired,
  children: PropTypes.node,
  okButtonProps: PropTypes.object,
};

ModelVersionPickModal.defaultProps = {
  description: null,
  okText: "Confirm",
  cancelText: "Cancel",
  versions: null,
  value: undefined,
  onChange: () => {},
  onOk: () => {},
  children: null,
  okButtonProps: undefined,
};
