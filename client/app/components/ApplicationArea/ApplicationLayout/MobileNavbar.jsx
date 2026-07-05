import { first } from "lodash";
import React from "react";
import PropTypes from "prop-types";
import Button from "antd/lib/button";
import MenuOutlinedIcon from "@ant-design/icons/MenuOutlined";
import Dropdown from "antd/lib/dropdown";
import Menu from "antd/lib/menu";
import Link from "@/components/Link";
import ThemeToggle from "@/components/ThemeToggle";
import { Auth, clientConfig, currentUser } from "@/services/auth";
import settingsMenu from "@/services/settingsMenu";
import logoUrl from "@/assets/images/icon_small.png";

import "./MobileNavbar.less";

export default function MobileNavbar({ getPopupContainer }) {
  const firstSettingsTab = first(settingsMenu.getAvailableItems());

  return (
    <div className="mobile-navbar">
      <div className="mobile-navbar-logo">
        <Link href="./">
          <img src={logoUrl} alt="Redash" />
        </Link>
      </div>
      <div>
        <Dropdown
          overlayStyle={{ minWidth: 200 }}
          trigger={["click"]}
          getPopupContainer={getPopupContainer} // so the overlay menu stays with the fixed header when page scrolls
          overlay={
            <Menu mode="vertical" selectable={false} className="mobile-navbar-menu">
              {currentUser.hasPermission("list_dashboards") && (
                <Menu.Item key="dashboards">
                  <Link href="dashboards">Dashboards</Link>
                </Menu.Item>
              )}
              {currentUser.hasPermission("view_query") && (
                <Menu.Item key="queries">
                  <Link href="queries">Queries</Link>
                </Menu.Item>
              )}
              {currentUser.hasPermission("list_query_snippets") && (
                <Menu.Item key="query-snippets">
                  <Link href="query_snippets">Query Snippets</Link>
                </Menu.Item>
              )}
              {currentUser.hasPermission("list_alerts") && (
                <Menu.Item key="alerts">
                  <Link href="alerts">Alerts</Link>
                </Menu.Item>
              )}
              {currentUser.hasPermission("list_alerts") && (
                <Menu.Item key="alert-events">
                  <Link href="alert_events">Alerts History</Link>
                </Menu.Item>
              )}
              {currentUser.hasPermission("list_destinations") && (
                <Menu.Item key="alert-destinations">
                  <Link href="destinations">Destinations</Link>
                </Menu.Item>
              )}
              {currentUser.hasPermission("list_indexers") && (
                <Menu.Item key="indexers">
                  <Link href="indexers">Indexers</Link>
                </Menu.Item>
              )}
              {currentUser.hasPermission("list_models") && (
                <Menu.Item key="ml-models">
                  <Link href="ml_models">Models</Link>
                </Menu.Item>
              )}
              {currentUser.hasPermission("list_models") && (
                <Menu.Item key="ml-models-versions">
                  <Link href="ml_models_versions">Versions</Link>
                </Menu.Item>
              )}
              {currentUser.hasPermission("list_models") && (
                <Menu.Item key="predictions">
                  <Link href="predictions">Predictions</Link>
                </Menu.Item>
              )}
              {clientConfig.assistantEnabled && (
                <Menu.Item key="assistant">
                  <Link href="assistant">Assistant</Link>
                </Menu.Item>
              )}
              <Menu.Item key="profile">
                <Link href="users/me">Edit Profile</Link>
              </Menu.Item>
              <Menu.Divider />
              {firstSettingsTab && (
                <Menu.Item key="settings">
                  <Link href={firstSettingsTab.path}>Settings</Link>
                </Menu.Item>
              )}
              {currentUser.hasPermission("super_admin") && (
                <Menu.Item key="status">
                  <Link href="admin/status">System Status</Link>
                </Menu.Item>
              )}
              {currentUser.hasPermission("super_admin") && <Menu.Divider />}
              <Menu.Item key="help">
                {/* eslint-disable-next-line react/jsx-no-target-blank */}
                <Link href="https://naoufel.io/help" target="_blank" rel="noopener">
                  Help
                </Link>
              </Menu.Item>
              <Menu.Item key="theme" className="mobile-navbar-theme-item">
                <ThemeToggle variant="menu-item" />
              </Menu.Item>
              <Menu.Item key="logout" onClick={() => Auth.logout()}>
                Log out
              </Menu.Item>
            </Menu>
          }>
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
