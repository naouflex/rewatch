import { first } from "lodash";
import React, { useMemo, useState, useCallback } from "react";
import Button from "antd/lib/button";
import Drawer from "antd/lib/drawer";
import MenuOutlinedIcon from "@ant-design/icons/MenuOutlined";
import Menu from "antd/lib/menu";
import Link from "@/components/Link";
import HelpTrigger from "@/components/HelpTrigger";
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

  const menuItems = useMemo(() => {
    const items = [];

    if (currentUser.hasPermission("list_dashboards")) {
      items.push(linkItem("dashboards", "dashboards", "Dashboards"));
    }

    if (currentUser.hasPermission("view_query")) {
      items.push(
        submenuItem("queries", "Queries", [
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
          linkItem("alerts-list", "alerts", "Alerts"),
          linkItem("alerts-history", "alert_events", "Alerts History"),
          ...(currentUser.hasPermission("list_destinations")
            ? [linkItem("alert-destinations", "destinations", "Destinations")]
            : []),
        ])
      );
    }

    if (currentUser.hasPermission("list_indexers")) {
      items.push(linkItem("indexers", "indexers", "Indexers"));
    }

    if (currentUser.hasPermission("list_models")) {
      items.push(
        submenuItem("models", "Models", [
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
  }, [firstSettingsTab]);

  const handleMenuClick = useCallback(({ key }) => {
    if (SUBMENU_KEYS.has(key)) {
      return;
    }

    if (key === "logout") {
      Auth.logout();
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
