import React from "react";
import PropTypes from "prop-types";
import { get, isEmpty } from "lodash";
import Modal from "antd/lib/modal";
import Button from "antd/lib/button";
import TimeAgo from "@/components/TimeAgo";
import { destinationLabel, statusTag } from "@/pages/alert-events/alertEventUtils";

import "@/components/ModalShell/modal-shell.less";

export function NotificationContentBody({ event }) {
  if (!event) {
    return null;
  }

  return (
    <>
      <p className="text-muted m-b-10">
        <TimeAgo date={event.created_at} /> · {destinationLabel(event)} · {statusTag(event.status)}
      </p>
      {!isEmpty(get(event, "additional_properties.error")) && (
        <pre className="text-danger modal-shell__code-block m-b-10">{event.additional_properties.error}</pre>
      )}
      <div className="modal-shell__notification-content">{event.content || "(no content recorded)"}</div>
    </>
  );
}

NotificationContentBody.propTypes = {
  event: PropTypes.object,
};

NotificationContentBody.defaultProps = {
  event: null,
};

export default function NotificationContentModal({ open, event, onClose }) {
  return (
    <Modal
      open={open}
      onCancel={onClose}
      title="Notification"
      width={720}
      className="modal-shell"
      rootClassName="modal-shell-root modal-shell-root--lg"
      footer={
        <Button onClick={onClose} type="default">
          Close
        </Button>
      }>
      <div className="modal-shell__body">
        <NotificationContentBody event={event} />
      </div>
    </Modal>
  );
}

NotificationContentModal.propTypes = {
  open: PropTypes.bool.isRequired,
  event: PropTypes.object,
  onClose: PropTypes.func.isRequired,
};

NotificationContentModal.defaultProps = {
  event: null,
};
