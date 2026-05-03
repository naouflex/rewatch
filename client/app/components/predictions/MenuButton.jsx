import React, { useState, useCallback } from "react";
import PropTypes from "prop-types";
import cx from "classnames";

import Modal from "antd/lib/modal";
import Dropdown from "antd/lib/dropdown";
import Menu from "antd/lib/menu";
import Button from "antd/lib/button";

import LoadingOutlinedIcon from "@ant-design/icons/LoadingOutlined";
import EllipsisOutlinedIcon from "@ant-design/icons/EllipsisOutlined";
import PlainButton from "@/components/PlainButton";
import "./MenuButton.less";

export default function MenuButton({ doDelete, doArchive, doUnarchive, archived }) {
  const [loading, setLoading] = useState(false);

  const execute = useCallback(action => {
    setLoading(true);
    action().finally(() => {
      setLoading(false);
    });
  }, []);

  const confirmDelete = useCallback(() => {
    Modal.confirm({
      title: "Delete Predicition",
      content: "Are you sure you want to delete this predicition?",
      okText: "Delete",
      okType: "danger",
      onOk: () => execute(doDelete),
      maskClosable: true,
      autoFocusButton: null,
    });
  }, [doDelete, execute]);

  const confirmArchive = useCallback(() => {
    Modal.confirm({
      title: "Archive Predicition",
      content: "Are you sure you want to archive this predicition?",
      okText: "Archive",
      okType: "danger",
      onOk: () => execute(doArchive),
      maskClosable: true,
      autoFocusButton: null,
    });
  }, [doArchive, execute]);

  const confirmUnarchive = useCallback(() => {
    Modal.confirm({
      title: "Unarchive Predicition",
      content: "Are you sure you want to unarchive this predicition?",
      okText: "Unarchive",
      okType: "danger",
      onOk: () => execute(doUnarchive),
      maskClosable: true,
      autoFocusButton: null,
    });
  }, [doUnarchive, execute]);

  return (
    <Dropdown
      className={cx("m-l-5", { disabled: true })}
      trigger="click" 
      placement="bottomRight"
      overlay={
        <Menu>
          <Menu.Item>
            <PlainButton onClick={confirmDelete}>Delete</PlainButton>
          </Menu.Item>
          <Menu.Item>
            {archived ? (
              <PlainButton onClick={confirmUnarchive}>Unarchive</PlainButton>
            ) : (
              <PlainButton onClick={confirmArchive}>Archive</PlainButton>
            )}
          </Menu.Item>
        </Menu>
      }>
      <Button aria-label="More actions">
        {loading ? <LoadingOutlinedIcon /> : <EllipsisOutlinedIcon rotate={90} aria-hidden="true" />}
      </Button>
    </Dropdown>
  );
}

MenuButton.propTypes = {
  doDelete: PropTypes.func.isRequired,
  doArchive: PropTypes.func.isRequired,
  doUnarchive: PropTypes.func.isRequired,
  archived: PropTypes.bool.isRequired,
};
