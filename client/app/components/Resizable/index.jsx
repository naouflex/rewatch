import React, { useRef, useMemo, useCallback, useState, useEffect } from "react";
import PropTypes from "prop-types";
import { Resizable as ReactResizable } from "react-resizable";
import KeyboardShortcuts from "@/services/KeyboardShortcuts";

import "./index.less";

export default function Resizable({ toggleShortcut, direction, sizeAttribute, children }) {
  const [size, setSize] = useState(0);
  const elementRef = useRef();
  const wasUsingTouchEventsRef = useRef(false);
  const wasResizedRef = useRef(false);

  const sizeProp = direction === "horizontal" ? "width" : "height";
  sizeAttribute = sizeAttribute || sizeProp;

  const getElementSize = useCallback(() => {
    if (!elementRef.current) {
      return 0;
    }
    return Math.floor(elementRef.current.getBoundingClientRect()[sizeProp]);
  }, [sizeProp]);

  const savedSize = useRef(null);
  const toggle = useCallback(() => {
    if (!elementRef.current) {
      return;
    }

    const element = elementRef.current;
    let targetSize;
    if (savedSize.current === null) {
      targetSize = "0px";
      savedSize.current = `${getElementSize()}px`;
    } else {
      targetSize = savedSize.current;
      savedSize.current = null;
    }

    element.style.transition = `${sizeAttribute} 200ms ease`;
    element.style[sizeAttribute] = targetSize;

    setSize(parseInt(targetSize, 10) || 0);
  }, [getElementSize, sizeAttribute]);

  const resizeHandle = useMemo(
    () => (
      // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions
      <span
        className={`react-resizable-handle react-resizable-handle-${direction}`}
        role="separator"
        onClick={() => {
          if (wasUsingTouchEventsRef.current || !wasResizedRef.current) {
            toggle();
          }
          wasUsingTouchEventsRef.current = false;
          wasResizedRef.current = false;
        }}
      />
    ),
    [direction, toggle]
  );

  useEffect(() => {
    if (toggleShortcut) {
      const shortcuts = {
        [toggleShortcut]: toggle,
      };

      KeyboardShortcuts.bind(shortcuts);
      return () => {
        KeyboardShortcuts.unbind(shortcuts);
      };
    }
  }, [toggleShortcut, toggle]);

  const resizeEventHandlers = useMemo(
    () => ({
      onResizeStart: () => {
        setSize(getElementSize());
      },
      onResize: (unused, data) => {
        if (elementRef.current) {
          elementRef.current.style[sizeAttribute] = `${data.size[sizeProp]}px`;
        }
        setSize(data.size[sizeProp]);
        wasResizedRef.current = true;
      },
      onResizeStop: () => {
        if (wasResizedRef.current) {
          savedSize.current = null;
        }
      },
    }),
    [sizeProp, getElementSize, sizeAttribute]
  );

  const draggableCoreOptions = useMemo(
    () => ({
      onMouseDown: e => {
        if (e.type === "touchstart") {
          wasUsingTouchEventsRef.current = true;
        }
        setSize(getElementSize());
      },
    }),
    [getElementSize]
  );

  if (!children) {
    return null;
  }

  children = React.createElement(children.type, { ...children.props, ref: elementRef });

  return (
    <ReactResizable
      className="resizable-component"
      axis={direction === "horizontal" ? "x" : "y"}
      resizeHandles={[direction === "horizontal" ? "e" : "s"]}
      handle={resizeHandle}
      width={direction === "horizontal" ? size : 0}
      height={direction === "vertical" ? size : 0}
      minConstraints={[0, 0]}
      {...resizeEventHandlers}
      draggableOpts={draggableCoreOptions}>
      {children}
    </ReactResizable>
  );
}

Resizable.propTypes = {
  direction: PropTypes.oneOf(["horizontal", "vertical"]),
  sizeAttribute: PropTypes.string,
  toggleShortcut: PropTypes.string,
  children: PropTypes.element,
};

Resizable.defaultProps = {
  direction: "horizontal",
  sizeAttribute: null,
  toggleShortcut: null,
  children: null,
};
