import { extend } from "lodash";
import React, { useCallback } from "react";
import { confirmDialog } from "@/components/ModalShell/confirmDialog";
import { Query } from "@/services/query";
import notification from "@/services/notification";
import useImmutableCallback from "@/lib/hooks/useImmutableCallback";

function confirmArchive() {
  return new Promise((resolve, reject) => {
    confirmDialog({
      title: "Archive Query",
      content: (
        <React.Fragment>
          <div className="m-b-5">Are you sure you want to archive this query?</div>
          <div>All alerts and dashboard widgets created with its visualizations will be deleted.</div>
        </React.Fragment>
      ),
      okText: "Archive",
      variant: "danger",
      onConfirm: () => resolve(),
      onCancel: () => reject(),
    });
  });
}

function doArchiveQuery(query) {
  return Query.delete({ id: query.id })
    .then(() => {
      return extend(query.clone(), { is_archived: true, schedule: null });
    })
    .catch(error => {
      notification.error("Query could not be archived.");
      return Promise.reject(error);
    });
}

export default function useArchiveQuery(query, onChange) {
  const handleChange = useImmutableCallback(onChange);

  return useCallback(() => {
    confirmArchive()
      .then(() => doArchiveQuery(query))
      .then(handleChange);
  }, [query, handleChange]);
}
