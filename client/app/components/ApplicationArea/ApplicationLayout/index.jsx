import React, { useRef, useCallback } from "react";
import PropTypes from "prop-types";
import DynamicComponent from "@/components/DynamicComponent";
import AssistantBubble from "@/components/AssistantBubble";
import DesktopNavbar from "./DesktopNavbar";
import MobileNavbar from "./MobileNavbar";

import "./index.less";

export default function ApplicationLayout({ children }) {
  const navbarContainerRef = useRef();

  const getNavbarPopupContainer = useCallback(() => navbarContainerRef.current, []);

  return (
    <React.Fragment>
      <DynamicComponent name="ApplicationWrapper">
        <nav className="application-layout-top-menu" ref={navbarContainerRef}>
          <div className="application-layout-desktop-nav">
            <DynamicComponent name="ApplicationDesktopNavbar">
              <DesktopNavbar />
            </DynamicComponent>
          </div>
          <div className="application-layout-mobile-nav">
            <DynamicComponent name="ApplicationMobileNavbar" getPopupContainer={getNavbarPopupContainer}>
              <MobileNavbar getPopupContainer={getNavbarPopupContainer} />
            </DynamicComponent>
          </div>
        </nav>
        <div className="application-layout-content">{children}</div>
      </DynamicComponent>
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
