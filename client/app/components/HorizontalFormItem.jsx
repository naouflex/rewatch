import React from "react";
import PropTypes from "prop-types";
import cx from "classnames";
import Form from "antd/lib/form";

// Shared horizontal layout for AntD Form.Item used by alert / indexer /
// MLModel form pages. The MLModel components were ported from inverse-watch
// where a single shared component lived at `@/components/HorizontalFormItem`;
// alert and indexer pages keep their local copies for backwards compat.
export default function HorizontalFormItem({ children, label, className, ...props }) {
  const labelCol = { span: 4 };
  const wrapperCol = { span: 16 };
  if (!label) {
    wrapperCol.offset = 4;
  }

  className = cx("ml-model-form-item", className);

  return (
    <Form.Item labelCol={labelCol} wrapperCol={wrapperCol} label={label} className={className} {...props}>
      {children}
    </Form.Item>
  );
}

HorizontalFormItem.propTypes = {
  children: PropTypes.node,
  label: PropTypes.string,
  className: PropTypes.string,
};

HorizontalFormItem.defaultProps = {
  children: null,
  label: null,
  className: null,
};
