import React, { useMemo, useReducer, useEffect } from "react";
import { first, includes } from "lodash";
import Menu from "antd/lib/menu";
import Link from "@/components/Link";
import PlainButton from "@/components/PlainButton";
import HelpTrigger from "@/components/HelpTrigger";
import CreateDashboardDialog from "@/components/dashboards/CreateDashboardDialog";
import { useCurrentRoute } from "@/components/ApplicationArea/Router";
import { Auth, clientConfig, currentUser, subscribeToCurrentUser } from "@/services/auth";
import settingsMenu from "@/services/settingsMenu";
import { APPLICATION_TITLE, getApiDocsUrl } from "@/config/brand";
import logoUrl from "@/assets/images/icon_small.png";

import ThemeToggle from "@/components/ThemeToggle";
import VersionInfo from "./VersionInfo";

import "./DesktopNavbar.less";

function NavbarSection({ items, className, ...props }) {
  return (
    <Menu
      selectable={false}
      mode="horizontal"
      className={`desktop-navbar-menu ${className || ""}`}
      items={items}
      {...props}
    />
  );
}

function useNavbarActiveState() {
  const currentRoute = useCurrentRoute();

  return useMemo(
    () => ({
      dashboards: includes(
        [
          "Dashboards.List",
          "Dashboards.Favorites",
          "Dashboards.My",
          "Dashboards.ViewOrEdit",
          "Dashboards.LegacyViewOrEdit",
        ],
        currentRoute.id
      ),
      queries: includes(
        [
          "Queries.List",
          "Queries.Favorites",
          "Queries.Archived",
          "Queries.My",
          "Queries.View",
          "Queries.New",
          "Queries.Edit",
          "QuerySnippets.List",
          "QuerySnippets.My",
          "QuerySnippets.Favorites",
          "QuerySnippets.Archived",
          "QuerySnippets.NewOrEdit",
        ],
        currentRoute.id
      ),
      dataSources: includes(["DataSources.List"], currentRoute.id),
      assistant: currentRoute.id === "Assistant",
      alerts: includes(
        [
          "Alerts.List",
          "Alerts.New",
          "Alerts.View",
          "Alerts.Edit",
          "AlertEvents.List",
          "AlertDestinations.List",
          "AlertDestinations.My",
          "AlertDestinations.Favorites",
          "AlertDestinations.Archived",
          "AlertDestinations.New",
          "AlertDestinations.Edit",
        ],
        currentRoute.id
      ),
      indexers: includes(
        [
          "Indexers.List",
          "Indexers.My",
          "Indexers.Favorites",
          "Indexers.Archived",
          "Indexers.New",
          "Indexers.View",
          "Indexers.Edit",
        ],
        currentRoute.id
      ),
      models: includes(
        [
          "MLModels.List",
          "MLModels.My",
          "MLModels.Favorites",
          "MLModels.Archive",
          "MLModels.New",
          "MLModels.View",
          "MLModels.Edit",
          "MLModels.Stats",
          "MLModels.Overview",
          "MLModels.Predictions",
          "MLModels.Versions",
          "MLModels.Metrics",
          "MLModels.MetricsHistory",
          "MLModels.MetricsHistoryTrain",
          "MLModelsVersions.List",
          "MLModelsVersions.My",
          "MLModelsVersions.Favorites",
          "MLModelsVersions.Archive",
          "MLModelsVersions.View",
          "PredictionResults.List",
          "PredictionResults.My",
          "PredictionResults.Favorites",
          "PredictionResults.Archive",
          "PredictionResult.View",
        ],
        currentRoute.id
      ),
    }),
    [currentRoute.id]
  );
}

export default function DesktopNavbar() {
  const firstSettingsTab = first(settingsMenu.getAvailableItems());

  const [, forceUpdate] = useReducer(x => x + 1, 0);
  useEffect(() => subscribeToCurrentUser(forceUpdate), []);

  const activeState = useNavbarActiveState();

  const canCreateQuery = currentUser.hasPermission("create_query");
  const canCreateDashboard = currentUser.hasPermission("create_dashboard");
  const canCreateAlert = currentUser.hasPermission("list_alerts");
  const canCreateDestination = currentUser.hasPermission("create_destination");
  const canCreateIndexer = currentUser.hasPermission("create_indexer");
  const canCreateModel = currentUser.hasPermission("create_model");
  const canListModels = currentUser.hasPermission("list_models");

  const mainNavItems = useMemo(() => {
    const items = [];

    if (currentUser.hasPermission("list_dashboards")) {
      items.push({
        key: "dashboards",
        className: activeState.dashboards ? "navbar-active-item" : null,
        label: (
          <Link href="dashboards">
            <span className="desktop-navbar-label">Dashboards</span>
          </Link>
        ),
      });
    }

    if (currentUser.hasPermission("view_query")) {
      items.push({
        key: "queries",
        popupClassName: "desktop-navbar-submenu",
        className: activeState.queries ? "navbar-active-item" : null,
        label: (
          <Link href="queries" className="navbar-submenu-title">
            <span className="desktop-navbar-label">Queries</span>
          </Link>
        ),
        children: [
          {
            key: "queries-list",
            label: <Link href="queries">Queries</Link>,
          },
          ...(currentUser.hasPermission("list_query_snippets")
            ? [
                {
                  key: "query-snippets",
                  label: <Link href="query_snippets">Query Snippets</Link>,
                },
              ]
            : []),
        ],
      });
    }

    if (currentUser.hasPermission("list_alerts")) {
      items.push({
        key: "alerts",
        popupClassName: "desktop-navbar-submenu",
        className: activeState.alerts ? "navbar-active-item" : null,
        label: (
          <Link href="alerts" className="navbar-submenu-title">
            <span className="desktop-navbar-label">Alerts</span>
          </Link>
        ),
        children: [
          {
            key: "alerts-list",
            label: <Link href="alerts">Alerts</Link>,
          },
          {
            key: "alerts-history",
            label: <Link href="alert_events">Alerts History</Link>,
          },
          ...(currentUser.hasPermission("list_destinations")
            ? [
                {
                  key: "alert-destinations",
                  label: <Link href="destinations">Destinations</Link>,
                },
              ]
            : []),
        ],
      });
    }

    if (currentUser.hasPermission("list_indexers")) {
      items.push({
        key: "indexers",
        className: activeState.indexers ? "navbar-active-item" : null,
        label: (
          <Link href="indexers">
            <span className="desktop-navbar-label">Indexers</span>
          </Link>
        ),
      });
    }

    if (canListModels) {
      items.push({
        key: "models",
        popupClassName: "desktop-navbar-submenu",
        className: activeState.models ? "navbar-active-item" : null,
        label: (
          <Link href="ml_models" className="navbar-submenu-title">
            <span className="desktop-navbar-label">Models</span>
          </Link>
        ),
        children: [
          {
            key: "models-list",
            label: <Link href="ml_models">Models</Link>,
          },
          {
            key: "models-versions",
            label: <Link href="ml_models_versions">Versions</Link>,
          },
          {
            key: "predictions-list",
            label: <Link href="predictions">Predictions</Link>,
          },
        ],
      });
    }

    if (clientConfig.assistantEnabled) {
      items.push({
        key: "assistant",
        className: activeState.assistant ? "navbar-active-item" : null,
        label: (
          <Link href="assistant">
            <span className="desktop-navbar-label">Assistant</span>
          </Link>
        ),
      });
    }

    return items;
  }, [activeState, canListModels]);

  const utilityNavItems = useMemo(() => {
    const items = [];

    if (canCreateQuery || canCreateDashboard || canCreateAlert || canCreateDestination || canCreateIndexer || canCreateModel) {
      items.push({
        key: "create",
        popupClassName: "desktop-navbar-submenu",
        className: "desktop-navbar-create-item",
        "data-test": "CreateButton",
        tabIndex: 0,
        label: <span className="desktop-navbar-label">Create</span>,
        children: [
          ...(canCreateQuery
            ? [
                {
                  key: "new-query",
                  label: (
                    <Link href="queries/new" data-test="CreateQueryMenuItem">
                      New Query
                    </Link>
                  ),
                },
              ]
            : []),
          ...(canCreateDashboard
            ? [
                {
                  key: "new-dashboard",
                  label: (
                    <PlainButton data-test="CreateDashboardMenuItem" onClick={() => CreateDashboardDialog.showModal()}>
                      New Dashboard
                    </PlainButton>
                  ),
                },
              ]
            : []),
          ...(canCreateAlert
            ? [
                {
                  key: "new-alert",
                  label: (
                    <Link data-test="CreateAlertMenuItem" href="alerts/new">
                      New Alert
                    </Link>
                  ),
                },
              ]
            : []),
          ...(canCreateDestination
            ? [
                {
                  key: "new-destination",
                  label: (
                    <Link data-test="CreateDestinationMenuItem" href="destinations/new">
                      New Alert Destination
                    </Link>
                  ),
                },
              ]
            : []),
          ...(canCreateIndexer
            ? [
                {
                  key: "new-indexer",
                  label: (
                    <Link data-test="CreateIndexerMenuItem" href="indexers/new">
                      New Indexer
                    </Link>
                  ),
                },
              ]
            : []),
          ...(canCreateModel
            ? [
                {
                  key: "new-model",
                  label: (
                    <Link data-test="CreateMLModelMenuItem" href="ml_models/new">
                      New Model
                    </Link>
                  ),
                },
              ]
            : []),
        ],
      });
    }

    items.push({
      key: "api-docs",
      label: (
        /* eslint-disable-next-line react/jsx-no-target-blank */
        <a href={getApiDocsUrl(clientConfig.basePath)} target="_blank" rel="noopener noreferrer">
          <span className="desktop-navbar-label">API Docs</span>
        </a>
      ),
    });

    items.push({
      key: "help",
      label: (
        <HelpTrigger showTooltip={false} type="HOME" tabIndex={0}>
          <span className="desktop-navbar-label">Help</span>
        </HelpTrigger>
      ),
    });

    if (firstSettingsTab) {
      items.push({
        key: "settings",
        className: activeState.dataSources ? "navbar-active-item" : null,
        label: (
          <Link href={firstSettingsTab.path} data-test="SettingsLink">
            <span className="desktop-navbar-label">Settings</span>
          </Link>
        ),
      });
    }

    items.push({
      key: "theme",
      className: "desktop-navbar-theme-item",
      "data-test": "ThemeToggle",
      label: <ThemeToggle />,
    });

    items.push({
      key: "profile",
      popupClassName: "desktop-navbar-submenu",
      className: "desktop-navbar-profile-menu",
      tabIndex: 0,
      label: (
        <span data-test="ProfileDropdown" className="desktop-navbar-profile-menu-title">
          <img className="profile__image_thumb" src={currentUser.profile_image_url} alt={currentUser.name} />
        </span>
      ),
      children: [
        {
          key: "profile",
          label: <Link href="users/me">Profile</Link>,
        },
        ...(currentUser.hasPermission("super_admin")
          ? [
              {
                key: "status",
                label: <Link href="admin/status">System Status</Link>,
              },
            ]
          : []),
        { type: "divider" },
        {
          key: "logout",
          label: (
            <PlainButton data-test="LogOutButton" onClick={() => Auth.logout()}>
              Log out
            </PlainButton>
          ),
        },
        { type: "divider" },
        {
          key: "version",
          role: "presentation",
          disabled: true,
          className: "version-info",
          label: <VersionInfo />,
        },
      ],
    });

    return items;
  }, [
    activeState.dataSources,
    canCreateAlert,
    canCreateDashboard,
    canCreateDestination,
    canCreateIndexer,
    canCreateModel,
    canCreateQuery,
    firstSettingsTab,
  ]);

  return (
    <nav className="desktop-navbar">
      <div className="desktop-navbar-logo">
        <Link href="./" className="desktop-navbar-logo-link">
          <img src={logoUrl} alt="" />
          <span className="desktop-navbar-logo-title">{APPLICATION_TITLE}</span>
        </Link>
      </div>

      <NavbarSection className="desktop-navbar-main" items={mainNavItems} />

      <div className="desktop-navbar-spacer" />

      <NavbarSection className="desktop-navbar-utilities" items={utilityNavItems} />
    </nav>
  );
}
