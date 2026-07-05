import { first } from "lodash";
import React, { useMemo } from "react";
import PropTypes from "prop-types";
import Button from "antd/lib/button";
import MenuOutlinedIcon from "@ant-design/icons/MenuOutlined";
import Dropdown from "antd/lib/dropdown";
import Link from "@/components/Link";
import ThemeToggle from "@/components/ThemeToggle";
import { Auth, clientConfig, currentUser } from "@/services/auth";
import settingsMenu from "@/services/settingsMenu";
import { APPLICATION_TITLE, getApiDocsUrl } from "@/config/brand";
import logoUrl from "@/assets/images/icon_small.png";

import "./MobileNavbar.less";

export default function MobileNavbar({ getPopupContainer }) {
  const firstSettingsTab = first(settingsMenu.getAvailableItems());

  const menuItems = useMemo(() => {
    const items = [];

    if (currentUser.hasPermission("list_dashboards")) {
      items.push({
        key: "dashboards",
        label: <Link href="dashboards">Dashboards</Link>,
      });
    }
    if (currentUser.hasPermission("view_query")) {
      items.push({
        key: "queries",
        label: <Link href="queries">Queries</Link>,
      });
    }
    if (currentUser.hasPermission("list_query_snippets")) {
      items.push({
        key: "query-snippets",
        label: <Link href="query_snippets">Query Snippets</Link>,
      });
    }
    if (currentUser.hasPermission("list_alerts")) {
      items.push({
        key: "alerts",
        label: <Link href="alerts">Alerts</Link>,
      });
    }
    if (currentUser.hasPermission("list_alerts")) {
      items.push({
        key: "alert-events",
        label: <Link href="alert_events">Alerts History</Link>,
      });
    }
    if (currentUser.hasPermission("list_destinations")) {
      items.push({
        key: "alert-destinations",
        label: <Link href="destinations">Destinations</Link>,
      });
    }
    if (currentUser.hasPermission("list_indexers")) {
      items.push({
        key: "indexers",
        label: <Link href="indexers">Indexers</Link>,
      });
    }
    if (currentUser.hasPermission("list_models")) {
      items.push({
        key: "ml-models",
        label: <Link href="ml_models">Models</Link>,
      });
    }
    if (currentUser.hasPermission("list_models")) {
      items.push({
        key: "ml-models-versions",
        label: <Link href="ml_models_versions">Versions</Link>,
      });
    }
    if (currentUser.hasPermission("list_models")) {
      items.push({
        key: "predictions",
        label: <Link href="predictions">Predictions</Link>,
      });
    }
    if (clientConfig.assistantEnabled) {
      items.push({
        key: "assistant",
        label: <Link href="assistant">Assistant</Link>,
      });
    }

    items.push({
      key: "profile",
      label: <Link href="users/me">Edit Profile</Link>,
    });
    items.push({ type: "divider" });

    if (firstSettingsTab) {
      items.push({
        key: "settings",
        label: <Link href={firstSettingsTab.path}>Settings</Link>,
      });
    }
    if (currentUser.hasPermission("super_admin")) {
      items.push({
        key: "status",
        label: <Link href="admin/status">System Status</Link>,
      });
    }
    if (currentUser.hasPermission("super_admin")) {
      items.push({ type: "divider" });
    }

    items.push({
      key: "api-docs",
      label: (
        /* eslint-disable-next-line react/jsx-no-target-blank */
        <a href={getApiDocsUrl(clientConfig.basePath)} target="_blank" rel="noopener noreferrer">
          API Docs
        </a>
      ),
    });
    items.push({
      key: "help",
      label: (
        /* eslint-disable-next-line react/jsx-no-target-blank */
        <Link href="https://naoufel.io/help" target="_blank" rel="noopener">
          Help
        </Link>
      ),
    });
    items.push({
      key: "theme",
      className: "mobile-navbar-theme-item",
      label: <ThemeToggle variant="menu-item" />,
    });
    items.push({
      key: "logout",
      label: "Log out",
      onClick: () => Auth.logout(),
    });

    return items;
  }, [firstSettingsTab]);

  return (
    <div className="mobile-navbar">
      <div className="mobile-navbar-logo">
        <Link href="./" className="mobile-navbar-logo-link">
          <img src={logoUrl} alt="" />
          <span className="mobile-navbar-logo-title">{APPLICATION_TITLE}</span>
        </Link>
      </div>
      <div>
        <Dropdown
          overlayStyle={{ minWidth: 200 }}
          trigger={["click"]}
          getPopupContainer={getPopupContainer} // so the overlay menu stays with the fixed header when page scrolls
          menu={{
            items: menuItems,
            selectable: false,
            className: "mobile-navbar-menu",
          }}>
          <Button className="mobile-navbar-toggle-button">
            <MenuOutlinedIcon />
          </Button>
        </Dropdown>
      </div>
    </div>
  );
}

MobileNavbar.propTypes = {
  getPopupContainer: PropTypes.func,
};

MobileNavbar.defaultProps = {
  getPopupContainer: null,
};
