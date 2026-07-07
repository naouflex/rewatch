import React, { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import { Moment } from "@/components/proptypes";
import TimeAgo from "@/components/TimeAgo";
import { formatDate } from "@/lib/utils";

const NARROW_COLUMN_WIDTH = 148;

export default function AlertHistoryWhen({ date }) {
  const ref = useRef(null);
  const [narrow, setNarrow] = useState(false);

  useEffect(() => {
    const root = ref.current;
    if (!root) {
      return undefined;
    }

    const cell = root.closest("td, th");
    if (!cell) {
      return undefined;
    }

    const update = () => {
      setNarrow(cell.getBoundingClientRect().width < NARROW_COLUMN_WIDTH);
    };

    update();
    const observer = new ResizeObserver(update);
    observer.observe(cell);
    return () => observer.disconnect();
  }, []);

  return (
    <span ref={ref} className={`alert-history-when${narrow ? " alert-history-when--narrow" : ""}`}>
      <span className="alert-history-when__relative">
        <TimeAgo date={date} />
      </span>
      {narrow && <span className="alert-history-when__date">{formatDate(date)}</span>}
    </span>
  );
}

AlertHistoryWhen.propTypes = {
  date: PropTypes.oneOfType([PropTypes.string, PropTypes.number, PropTypes.instanceOf(Date), Moment]),
};
