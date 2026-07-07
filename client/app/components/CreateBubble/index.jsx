import React, { useMemo, useState } from "react";
import PlusOutlined from "@ant-design/icons/PlusOutlined";
import Dropdown from "antd/lib/dropdown";

import Link from "@/components/Link";
import CreateDashboardDialog from "@/components/dashboards/CreateDashboardDialog";
import { currentUser } from "@/services/auth";
import { policy } from "@/services/policy";

import "./index.less";

function CreateMenuItem({ href, icon, label, testId }) {
  const content = (
    <>
      <span className="create-bubble-menu__item-icon" aria-hidden="true">
        <i className={icon} />
      </span>
      {label}
    </>
  );

  if (href) {
    return (
      <Link href={href} className="create-bubble-menu__item" data-test={testId}>
        {content}
      </Link>
    );
  }

  return (
    <span className="create-bubble-menu__item" data-test={testId}>
      {content}
    </span>
  );
}

CreateMenuItem.defaultProps = {
  href: null,
  testId: null,
};

export default function CreateBubble() {
  const [open, setOpen] = useState(false);

  const menuItems = useMemo(() => {
    const items = [];

    if (currentUser.hasPermission("create_query")) {
      items.push({
        key: "query",
        label: <CreateMenuItem href="queries/new" icon="fa fa-code" label="New query" testId="CreateQueryMenuItem" />,
      });
    }

    if (currentUser.hasPermission("create_dashboard")) {
      items.push({
        key: "dashboard",
        label: (
          <CreateMenuItem icon="zmdi zmdi-view-quilt" label="New dashboard" testId="CreateDashboardMenuItem" />
        ),
      });
    }

    if (currentUser.hasPermission("list_alerts")) {
      items.push({
        key: "alert",
        label: <CreateMenuItem href="alerts/new" icon="fa fa-bell" label="New alert" testId="CreateAlertMenuItem" />,
      });
    }

    if (currentUser.hasPermission("create_destination")) {
      items.push({
        key: "destination",
        label: (
          <CreateMenuItem
            href="destinations/new"
            icon="fa fa-paper-plane"
            label="New destination"
            testId="CreateDestinationMenuItem"
          />
        ),
      });
    }

    if (currentUser.hasPermission("create_indexer")) {
      items.push({
        key: "indexer",
        label: (
          <CreateMenuItem href="indexers/new" icon="fa fa-database" label="New indexer" testId="CreateIndexerMenuItem" />
        ),
      });
    }

    if (currentUser.hasPermission("create_model")) {
      items.push({
        key: "model",
        label: (
          <CreateMenuItem href="ml_models/new" icon="fa fa-flask" label="New model" testId="CreateMLModelMenuItem" />
        ),
      });
    }

    if (policy.isCreateQuerySnippetEnabled()) {
      items.push({
        key: "query-snippet",
        label: (
          <CreateMenuItem
            href="query_snippets/new"
            icon="fa fa-scissors"
            label="New query snippet"
            testId="CreateQuerySnippetMenuItem"
          />
        ),
      });
    }

    return items;
  }, []);

  if (!menuItems.length) {
    return null;
  }

  const handleMenuClick = ({ key }) => {
    if (key === "dashboard") {
      CreateDashboardDialog.showModal();
    }
    setOpen(false);
  };

  return (
    <div className="create-bubble-root">
      <Dropdown
        menu={{ items: menuItems, onClick: handleMenuClick }}
        trigger={["click"]}
        placement="topRight"
        open={open}
        onOpenChange={setOpen}
        overlayClassName="create-bubble-menu"
      >
        <button
          type="button"
          className={`create-bubble-toggle${open ? " open" : ""}`}
          aria-label="Create new item"
          aria-expanded={open}
        >
          <PlusOutlined />
        </button>
      </Dropdown>
    </div>
  );
}
