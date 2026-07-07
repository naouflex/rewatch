import { first } from "lodash";
import React, { useMemo, useState, useCallback } from "react";
import Button from "antd/lib/button";
import Drawer from "antd/lib/drawer";
import MenuOutlinedIcon from "@ant-design/icons/MenuOutlined";
import Menu from "antd/lib/menu";
import Link from "@/components/Link";
import HelpTrigger from "@/components/HelpTrigger";
import CreateDashboardDialog from "@/components/dashboards/CreateDashboardDialog";
import ThemeToggle from "@/components/ThemeToggle";
import { Auth, clientConfig, currentUser } from "@/services/auth";
import settingsMenu from "@/services/settingsMenu";
import { APPLICATION_TITLE } from "@/config/brand";
import logoUrl from "@/assets/images/icon_small.png";

import "./MobileNavbar.less";

const SUBMENU_KEYS = new Set(["dashboards", "queries", "alerts", "indexers", "models", "account"]);

function submenuItem(key, label, children) {
  return { key, label, children };
}

function linkItem(key, href, label, props = {}) {
  return {
    key,
    label: (
      <Link href={href} {...props}>
        {label}
      </Link>
    ),
  };
}

export default function MobileNavbar() {
  const firstSettingsTab = first(settingsMenu.getAvailableItems());
  const [menuOpen, setMenuOpen] = useState(false);

  const canCreateQuery = currentUser.hasPermission("create_query");
  const canCreateDashboard = currentUser.hasPermission("create_dashboard");
  const canCreateAlert = currentUser.hasPermission("list_alerts");
  const canCreateDestination = currentUser.hasPermission("create_destination");
  const canCreateIndexer = currentUser.hasPermission("create_indexer");
  const canCreateModel = currentUser.hasPermission("create_model");

  const menuItems = useMemo(() => {
    const items = [];

    if (currentUser.hasPermission("list_dashboards")) {
      if (canCreateDashboard) {
        items.push(
          submenuItem("dashboards", "Dashboards", [
            { key: "new-dashboard", label: "Create Dashboard", "data-test": "CreateDashboardMenuItem" },
            { type: "divider" },
            linkItem("dashboards-list", "dashboards", "Dashboards"),
          ])
        );
      } else {
        items.push(linkItem("dashboards", "dashboards", "Dashboards"));
      }
    }

    if (currentUser.hasPermission("view_query")) {
      items.push(
        submenuItem("queries", "Queries", [
          ...(canCreateQuery
            ? [
                linkItem("new-query", "queries/new", "Create Query", { "data-test": "CreateQueryMenuItem" }),
                { type: "divider" },
              ]
            : []),
          linkItem("queries-list", "queries", "Queries"),
          ...(currentUser.hasPermission("list_query_snippets")
            ? [linkItem("query-snippets", "query_snippets", "Query Snippets")]
            : []),
        ])
      );
    }

    if (currentUser.hasPermission("list_alerts")) {
      items.push(
        submenuItem("alerts", "Alerts", [
          ...(canCreateAlert
            ? [
                linkItem("new-alert", "alerts/new", "Create Alert", { "data-test": "CreateAlertMenuItem" }),
                { type: "divider" },
              ]
            : []),
          linkItem("alerts-list", "alerts", "Alerts"),
          linkItem("alerts-history", "alert_events", "Alerts History"),
          ...(currentUser.hasPermission("list_destinations")
            ? [linkItem("alert-destinations", "destinations", "Destinations")]
            : []),
          ...(canCreateDestination
            ? [
                linkItem("new-destination", "destinations/new", "Create Destination", {
                  "data-test": "CreateDestinationMenuItem",
                }),
              ]
            : []),
        ])
      );
    }

    if (currentUser.hasPermission("list_indexers")) {
      if (canCreateIndexer) {
        items.push(
          submenuItem("indexers", "Indexers", [
            linkItem("new-indexer", "indexers/new", "Create Indexer", { "data-test": "CreateIndexerMenuItem" }),
            { type: "divider" },
            linkItem("indexers-list", "indexers", "Indexers"),
          ])
        );
      } else {
        items.push(linkItem("indexers", "indexers", "Indexers"));
      }
    }

    if (currentUser.hasPermission("list_models")) {
      items.push(
        submenuItem("models", "Models", [
          ...(canCreateModel
            ? [
                linkItem("new-model", "ml_models/new", "Create Model", { "data-test": "CreateMLModelMenuItem" }),
                { type: "divider" },
              ]
            : []),
          linkItem("models-list", "ml_models", "Models"),
          linkItem("models-versions", "ml_models_versions", "Versions"),
          linkItem("predictions-list", "predictions", "Predictions"),
        ])
      );
    }

    if (clientConfig.assistantEnabled) {
      items.push(linkItem("assistant", "assistant", "Assistant"));
    }

    if (currentUser.hasPermission("list_community_posts")) {
      items.push(linkItem("community", "community", "Community"));
    }

    items.push(linkItem("api-docs", "api-docs", "API"));

    items.push({ type: "divider" });

    const accountChildren = [
      linkItem("profile", "users/me", "Profile"),
      {
        key: "help",
        className: "mobile-navbar-help-item",
        label: (
          <HelpTrigger showTooltip={false} type="HOME" tabIndex={0}>
            Help
          </HelpTrigger>
        ),
      },
      ...(firstSettingsTab
        ? [
            {
              key: "settings",
              label: (
                <Link href={firstSettingsTab.path} data-test="SettingsLink">
                  Settings
                </Link>
              ),
            },
          ]
        : []),
      ...(currentUser.hasPermission("super_admin")
        ? [linkItem("status", "admin/status", "System Status")]
        : []),
    ];

    items.push(submenuItem("account", "Account", accountChildren));

    items.push({
      key: "theme",
      className: "mobile-navbar-theme-item",
      label: <ThemeToggle variant="menu-item" />,
    });

    items.push({
      key: "logout",
      label: "Log out",
    });

    return items;
  }, [
    canCreateAlert,
    canCreateDashboard,
    canCreateDestination,
    canCreateIndexer,
    canCreateModel,
    canCreateQuery,
    firstSettingsTab,
  ]);

  const handleMenuClick = useCallback(({ key }) => {
    if (SUBMENU_KEYS.has(key)) {
      return;
    }

    if (key === "logout") {
      Auth.logout();
    }

    if (key === "new-dashboard") {
      CreateDashboardDialog.showModal();
    }

    if (key !== "theme") {
      setMenuOpen(false);
    }
  }, []);

  return (
    <div className="mobile-navbar">
      <div className="mobile-navbar-logo">
        <Link href="./" className="mobile-navbar-logo-link">
          <img src={logoUrl} alt="" />
          <span className="mobile-navbar-logo-title">{APPLICATION_TITLE}</span>
        </Link>
      </div>
      <Button
        className="mobile-navbar-toggle-button"
        aria-label="Open navigation menu"
        aria-expanded={menuOpen}
        onClick={() => setMenuOpen(true)}>
        <MenuOutlinedIcon />
      </Button>
      <Drawer
        title="Menu"
        placement="right"
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        width="min(100vw - 24px, 320px)"
        rootClassName="mobile-navbar-drawer"
        destroyOnHidden>
        <Menu mode="inline" selectable={false} items={menuItems} onClick={handleMenuClick} />
      </Drawer>
    </div>
  );
}
