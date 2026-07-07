import React from "react";
import PropTypes from "prop-types";
import DynamicComponent from "@/components/DynamicComponent";
import AssistantBubble from "@/components/AssistantBubble";
import CreateBubble from "@/components/CreateBubble";
import DesktopNavbar from "./DesktopNavbar";
import MobileNavbar from "./MobileNavbar";

import "./index.less";

export default function ApplicationLayout({ children }) {
  return (
    <React.Fragment>
      <DynamicComponent name="ApplicationWrapper">
        <nav className="application-layout-top-menu">
          <div className="application-layout-desktop-nav">
            <DynamicComponent name="ApplicationDesktopNavbar">
              <DesktopNavbar />
            </DynamicComponent>
          </div>
          <div className="application-layout-mobile-nav">
            <DynamicComponent name="ApplicationMobileNavbar">
              <MobileNavbar />
            </DynamicComponent>
          </div>
        </nav>
        <div className="application-layout-content">{children}</div>
      </DynamicComponent>
      <CreateBubble />
      <AssistantBubble />
    </React.Fragment>
  );
}

ApplicationLayout.propTypes = {
  children: PropTypes.node,
};

ApplicationLayout.defaultProps = {
  children: null,
};
