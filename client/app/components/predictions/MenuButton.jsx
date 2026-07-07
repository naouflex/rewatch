import React, { useState, useCallback, useMemo } from "react";
import PropTypes from "prop-types";
import cx from "classnames";

import Dropdown from "antd/lib/dropdown";
import Button from "antd/lib/button";

import LoadingOutlinedIcon from "@ant-design/icons/LoadingOutlined";
import EllipsisOutlinedIcon from "@ant-design/icons/EllipsisOutlined";
import PlainButton from "@/components/PlainButton";
import { confirmDialog } from "@/components/ModalShell/confirmDialog";
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
    confirmDialog({
      title: "Delete Predicition",
      description: "Are you sure you want to delete this predicition?",
      okText: "Delete",
      variant: "danger",
      onConfirm: () => execute(doDelete),
    });
  }, [doDelete, execute]);

  const confirmArchive = useCallback(() => {
    confirmDialog({
      title: "Archive Predicition",
      description: "Are you sure you want to archive this predicition?",
      okText: "Archive",
      variant: "danger",
      onConfirm: () => execute(doArchive),
    });
  }, [doArchive, execute]);

  const confirmUnarchive = useCallback(() => {
    confirmDialog({
      title: "Unarchive Predicition",
      description: "Are you sure you want to unarchive this predicition?",
      okText: "Unarchive",
      variant: "danger",
      onConfirm: () => execute(doUnarchive),
    });
  }, [doUnarchive, execute]);

  const menuItems = useMemo(
    () => [
      {
        key: "delete",
        label: <PlainButton onClick={confirmDelete}>Delete</PlainButton>,
      },
      {
        key: "archive",
        label: archived ? (
          <PlainButton onClick={confirmUnarchive}>Unarchive</PlainButton>
        ) : (
          <PlainButton onClick={confirmArchive}>Archive</PlainButton>
        ),
      },
    ],
    [archived, confirmArchive, confirmDelete, confirmUnarchive]
  );

  return (
    <Dropdown
      className={cx("m-l-5", { disabled: true })}
      trigger="click" 
      placement="bottomRight"
      menu={{ items: menuItems }}>
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
