import { startsWith, get, some } from "lodash";
import React from "react";
import PropTypes from "prop-types";
import cx from "classnames";
import Tooltip from "@/components/Tooltip";
import Drawer from "antd/lib/drawer";
import Link from "@/components/Link";
import PlainButton from "@/components/PlainButton";
import CloseOutlinedIcon from "@ant-design/icons/CloseOutlined";
import BigMessage from "@/components/BigMessage";
import DynamicComponent, { registerComponent } from "@/components/DynamicComponent";
import { getResolvedTheme, subscribeToTheme } from "@/services/theme";

import "./HelpTrigger.less";

// Help is now served by the in-cluster landing site (see ./landing/) instead
// of naoufel.io. The base URL can be overridden at build time with the
// REWATCH_HELP_BASE_URL env var (wired through webpack.EnvironmentPlugin).
// `?embed=1` tells the landing site to drop its top-level chrome so the
// drawer feels native; `?theme=light|dark` keeps it in lockstep with the
// theme the user picked in the main app.
const DEFAULT_HELP_BASE_URL = "https://naoufel.io";
const HELP_BASE_URL =
  (typeof process !== "undefined" && process.env && process.env.REWATCH_HELP_BASE_URL) ||
  DEFAULT_HELP_BASE_URL;
const DOMAIN = HELP_BASE_URL.replace(/\/+$/, "");
const HELP_PATH = "/help";
const IFRAME_TIMEOUT = 20000;
const IFRAME_URL_UPDATE_MESSAGE = "iframe_url";
const SET_THEME_MESSAGE = "set_theme";

function buildHelpUrl(path) {
  // Preserve any existing #hash on the configured help path while appending
  // the embed + theme query flags so the landing site renders chrome-less
  // and matches the host's theme.
  const [pathWithoutHash, hash = ""] = path.split("#");
  const fullHash = hash ? `#${hash}` : "";
  const theme = getResolvedTheme();
  const search = `?embed=1&theme=${encodeURIComponent(theme)}`;
  return `${DOMAIN}${HELP_PATH}${pathWithoutHash}${search}${fullHash}`;
}

// Each entry is `[relativePath, title]`. We deliberately do NOT pre-build
// the full URL here — `buildHelpUrl` is called lazily inside `getUrl` so
// the URL always reflects the *current* theme (the user can toggle theme
// after this module has loaded).
export const TYPES = {
  HOME: ["", "Help"],
  VALUE_SOURCE_OPTIONS: ["/user-guide/querying/query-parameters#Value-Source-Options", "Guide: Value Source Options"],
  SHARE_DASHBOARD: ["/user-guide/dashboards/sharing-dashboards", "Guide: Sharing and Embedding Dashboards"],
  AUTHENTICATION_OPTIONS: ["/user-guide/users/authentication-options", "Guide: Authentication Options"],
  DS_ATHENA: ["/data-sources/amazon-athena-setup", "Guide: Help Setting up Amazon Athena"],
  DS_BIGQUERY: ["/data-sources/bigquery-setup", "Guide: Help Setting up BigQuery"],
  DS_URL: ["/data-sources/querying-urls", "Guide: Help Setting up URL"],
  DS_MONGODB: ["/data-sources/mongodb-setup", "Guide: Help Setting up MongoDB"],
  DS_GOOGLE_SPREADSHEETS: [
    "/data-sources/querying-a-google-spreadsheet",
    "Guide: Help Setting up Google Spreadsheets",
  ],
  DS_GOOGLE_ANALYTICS: ["/data-sources/google-analytics-setup", "Guide: Help Setting up Google Analytics"],
  DS_AXIBASETSD: ["/data-sources/axibase-time-series-database", "Guide: Help Setting up Axibase Time Series"],
  DS_RESULTS: ["/user-guide/querying/query-results-data-source", "Guide: Help Setting up Query Results"],
  ALERT_SETUP: ["/user-guide/alerts/setting-up-an-alert", "Guide: Setting Up a New Alert"],
  MAIL_CONFIG: ["/open-source/setup/#Mail-Configuration", "Guide: Mail Configuration"],
  ALERT_NOTIF_TEMPLATE_GUIDE: ["/user-guide/alerts/custom-alert-notifications", "Guide: Custom Alerts Notifications"],
  FAVORITES: ["/user-guide/querying/favorites-tagging/#Favorites", "Guide: Favorites"],
  MANAGE_PERMISSIONS: [
    "/user-guide/querying/writing-queries#Managing-Query-Permissions",
    "Guide: Managing Query Permissions",
  ],
  NUMBER_FORMAT_SPECS: ["/user-guide/visualizations/formatting-numbers", "Formatting Numbers"],
  GETTING_STARTED: ["/user-guide/getting-started", "Guide: Getting Started"],
  DASHBOARDS: ["/user-guide/dashboards", "Guide: Dashboards"],
  QUERIES: ["/user-guide/querying", "Guide: Queries"],
  ALERTS: ["/user-guide/alerts", "Guide: Alerts"],
};

const HelpTriggerPropTypes = {
  type: PropTypes.string,
  href: PropTypes.string,
  title: PropTypes.node,
  className: PropTypes.string,
  showTooltip: PropTypes.bool,
  renderAsLink: PropTypes.bool,
  children: PropTypes.node,
};

const HelpTriggerDefaultProps = {
  type: null,
  href: null,
  title: null,
  className: null,
  showTooltip: true,
  renderAsLink: false,
  children: <i className="fa fa-question-circle" aria-hidden="true" />,
};

export function helpTriggerWithTypes(types, allowedDomains = [], drawerClassName = null) {
  return class HelpTrigger extends React.Component {
    static propTypes = {
      ...HelpTriggerPropTypes,
      type: PropTypes.oneOf(Object.keys(types)),
    };

    static defaultProps = HelpTriggerDefaultProps;

    iframeRef = React.createRef();

    iframeLoadingTimeout = null;

    state = {
      visible: false,
      loading: false,
      error: false,
      currentUrl: null,
    };

    componentDidMount() {
      window.addEventListener("message", this.onPostMessageReceived, false);
      // Push theme changes into the iframe so the help drawer's color scheme
      // tracks the host app's theme even if the user toggles after open.
      this.unsubscribeTheme = subscribeToTheme(({ resolved }) => {
        if (!this.state.visible) return;
        const iframeEl = this.iframeRef.current;
        if (!iframeEl || !iframeEl.contentWindow) return;
        try {
          iframeEl.contentWindow.postMessage(
            { type: SET_THEME_MESSAGE, theme: resolved },
            "*"
          );
        } catch (e) {
          // Cross-origin iframe — postMessage is allowed regardless, but
          // if posting fails for any reason just fall through; the next
          // openDrawer will reload the iframe with the right ?theme=.
        }
      });
    }

    componentWillUnmount() {
      window.removeEventListener("message", this.onPostMessageReceived);
      clearTimeout(this.iframeLoadingTimeout);
      if (this.unsubscribeTheme) {
        this.unsubscribeTheme();
      }
    }

    loadIframe = (url) => {
      clearTimeout(this.iframeLoadingTimeout);
      this.setState({ loading: true, error: false });

      this.iframeRef.current.src = url;
      this.iframeLoadingTimeout = setTimeout(() => {
        this.setState({ error: url, loading: false });
      }, IFRAME_TIMEOUT); // safety
    };

    onIframeLoaded = () => {
      this.setState({ loading: false });
      clearTimeout(this.iframeLoadingTimeout);
    };

    onPostMessageReceived = (event) => {
      if (!some(allowedDomains, (domain) => startsWith(event.origin, domain))) {
        return;
      }

      const { type, message: currentUrl } = event.data || {};
      if (type !== IFRAME_URL_UPDATE_MESSAGE) {
        return;
      }

      this.setState({ currentUrl });
    };

    getUrl = () => {
      const helpTriggerType = get(types, this.props.type);
      // `types[type][0]` is now a relative path (e.g. "/user-guide/...");
      // build the absolute URL on demand so the current theme + embed flag
      // are always part of the URL we point the iframe at.
      if (helpTriggerType) {
        return buildHelpUrl(helpTriggerType[0]);
      }
      return this.props.href;
    };

    openDrawer = (e) => {
      // keep "open in new tab" behavior
      if (!e.shiftKey && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        this.setState({ visible: true });
        // wait for drawer animation to complete so there's no animation jank
        setTimeout(() => this.loadIframe(this.getUrl()), 300);
      }
    };

    closeDrawer = (event) => {
      if (event) {
        event.preventDefault();
      }
      this.setState({ visible: false });
      this.setState({ visible: false, currentUrl: null });
    };

    render() {
      const targetUrl = this.getUrl();
      if (!targetUrl) {
        return null;
      }

      const tooltip = get(types, `${this.props.type}[1]`, this.props.title);
      const className = cx("help-trigger", this.props.className);
      const url = this.state.currentUrl;
      const isAllowedDomain = some(allowedDomains, (domain) => startsWith(url || targetUrl, domain));
      const shouldRenderAsLink = this.props.renderAsLink || !isAllowedDomain;

      return (
        <React.Fragment>
          <Tooltip
            title={
              this.props.showTooltip ? (
                <>
                  {tooltip}
                  {shouldRenderAsLink && (
                    <>
                      {" "}
                      <i className="fa fa-external-link" style={{ marginLeft: 5 }} aria-hidden="true" />
                      <span className="sr-only">(opens in a new tab)</span>
                    </>
                  )}
                </>
              ) : null
            }
          >
            <Link
              href={url || this.getUrl()}
              className={className}
              rel="noopener noreferrer"
              target="_blank"
              onClick={shouldRenderAsLink ? () => {} : this.openDrawer}
            >
              {this.props.children}
            </Link>
          </Tooltip>
          <Drawer
            placement="right"
            closable={false}
            onClose={this.closeDrawer}
            open={this.state.visible}
            className={cx("help-drawer", drawerClassName)}
            destroyOnClose
            width={400}
          >
            <div className="drawer-wrapper">
              <div className="drawer-menu">
                {url && (
                  <Tooltip title="Open page in a new window" placement="left">
                    {/* eslint-disable-next-line react/jsx-no-target-blank */}
                    <Link href={url} target="_blank">
                      <i className="fa fa-external-link" aria-hidden="true" />
                      <span className="sr-only">(opens in a new tab)</span>
                    </Link>
                  </Tooltip>
                )}
                <Tooltip title="Close" placement="bottom">
                  <PlainButton onClick={this.closeDrawer}>
                    <CloseOutlinedIcon />
                  </PlainButton>
                </Tooltip>
              </div>

              {/* iframe */}
              {!this.state.error && (
                <iframe
                  ref={this.iframeRef}
                  title="Usage Help"
                  src="about:blank"
                  className={cx({ ready: !this.state.loading })}
                  onLoad={this.onIframeLoaded}
                />
              )}

              {/* loading indicator */}
              {this.state.loading && (
                <BigMessage icon="fa-spinner fa-2x fa-pulse" message="Loading..." className="help-message" />
              )}

              {/* error message */}
              {this.state.error && (
                <BigMessage icon="fa-exclamation-circle" className="help-message">
                  Something went wrong.
                  <br />
                  {/* eslint-disable-next-line react/jsx-no-target-blank */}
                  <Link href={this.state.error} target="_blank" rel="noopener">
                    Click here
                  </Link>{" "}
                  to open the page in a new window.
                </BigMessage>
              )}
            </div>

            {/* extra content */}
            <DynamicComponent name="HelpDrawerExtraContent" onLeave={this.closeDrawer} openPageUrl={this.loadIframe} />
          </Drawer>
        </React.Fragment>
      );
    }
  };
}

registerComponent("HelpTrigger", helpTriggerWithTypes(TYPES, [DOMAIN]));

export default function HelpTrigger(props) {
  return <DynamicComponent {...props} name="HelpTrigger" />;
}

HelpTrigger.propTypes = HelpTriggerPropTypes;
HelpTrigger.defaultProps = HelpTriggerDefaultProps;
