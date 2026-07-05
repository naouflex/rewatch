import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { toLower, isNumber } from "lodash";

import InputNumber from "antd/lib/input-number";
import Select from "antd/lib/select";

import "./Rearm.less";

const DURATIONS = [
  ["Second", 1],
  ["Minute", 60],
  ["Hour", 3600],
  ["Day", 86400],
  ["Week", 604800],
];

function RearmByDuration({ value, onChange, editMode }) {
  const [durationIdx, setDurationIdx] = useState();
  const [count, setCount] = useState();

  useEffect(() => {
    for (let i = DURATIONS.length - 1; i >= 0; i -= 1) {
      const [, durValue] = DURATIONS[i];
      if (value % durValue === 0) {
        setDurationIdx(i);
        setCount(value / durValue);
        break;
      }
    }
  }, [value]);

  if (!isNumber(count) || !isNumber(durationIdx)) {
    return null;
  }

  const onChangeCount = newCount => {
    setCount(newCount);
    onChange(newCount * DURATIONS[durationIdx][1]);
  };

  const onChangeIdx = newIdx => {
    setDurationIdx(newIdx);
    onChange(count * DURATIONS[newIdx][1]);
  };

  const plural = count !== 1 ? "s" : "";

  if (editMode) {
    return (
      <>
        <InputNumber value={count} onChange={onChangeCount} min={1} precision={0} />
        <Select value={durationIdx} onChange={onChangeIdx}>
          {DURATIONS.map(([name], idx) => (
            <Select.Option value={idx} key={name}>
              {name}
              {plural}
            </Select.Option>
          ))}
        </Select>
      </>
    );
  }

  const [name] = DURATIONS[durationIdx];
  return count + " " + toLower(name) + plural;
}

RearmByDuration.propTypes = {
  onChange: PropTypes.func,
  value: PropTypes.number.isRequired,
  editMode: PropTypes.bool.isRequired,
};

RearmByDuration.defaultProps = {
  onChange: () => {},
};

function computeSelected(value, sendForEachRow) {
  if (sendForEachRow) {
    return 2;
  }
  if (value < 2) {
    return value;
  }
  return 3;
}

function RearmEditor({ value, onChange, sendForEachRow, onSendForEachRowChange }) {
  const [selected, setSelected] = useState(computeSelected(value, sendForEachRow));

  useEffect(() => {
    setSelected(computeSelected(value, sendForEachRow));
  }, [value, sendForEachRow]);

  const _onChange = newSelected => {
    setSelected(newSelected);
    switch (newSelected) {
      case 0:
        onChange(0);
        onSendForEachRowChange(false);
        break;
      case 1:
        onChange(1);
        onSendForEachRowChange(false);
        break;
      case 2:
        // "for each row in the result" runs at every evaluation
        onChange(1);
        onSendForEachRowChange(true);
        break;
      default:
        onChange(value && value >= 3600 ? value : 3600);
        onSendForEachRowChange(false);
        break;
    }
  };

  return (
    <div className="alert-rearm">
      <Select
        optionLabelProp="label"
        value={selected}
        popupMatchSelectWidth={false}
        onChange={_onChange}>
        <Select.Option value={0} label="Just once">
          Just once <em>until back to normal</em>
        </Select.Option>
        <Select.Option value={1} label="Each time alert is evaluated">
          Each time alert is evaluated <em>until back to normal</em>
        </Select.Option>
        <Select.Option value={2} label="Each time alert is evaluated for each row in the result">
          Each time alert is evaluated <em>for each row in the result</em>
        </Select.Option>
        <Select.Option value={3} label="At most every">
          At most every ... <em>when alert is evaluated</em>
        </Select.Option>
      </Select>
      {selected === 3 && value && <RearmByDuration value={value} onChange={onChange} editMode />}
    </div>
  );
}

RearmEditor.propTypes = {
  onChange: PropTypes.func.isRequired,
  value: PropTypes.number.isRequired,
  sendForEachRow: PropTypes.bool,
  onSendForEachRowChange: PropTypes.func,
};

RearmEditor.defaultProps = {
  sendForEachRow: false,
  onSendForEachRowChange: () => {},
};

function RearmViewer({ value, sendForEachRow }) {
  let phrase = "";
  if (sendForEachRow) {
    phrase = "each time alert is evaluated, for each row in the result";
  } else {
    switch (value) {
      case 0:
        phrase = "just once, until back to normal";
        break;
      case 1:
        phrase = "each time alert is evaluated, until back to normal";
        break;
      default:
        phrase = (
          <>
            at most every <RearmByDuration value={value} editMode={false} />, when alert is evaluated
          </>
        );
    }
  }

  return <span>Notifications are sent {phrase}.</span>;
}

RearmViewer.propTypes = {
  value: PropTypes.number.isRequired,
  sendForEachRow: PropTypes.bool,
};

RearmViewer.defaultProps = {
  sendForEachRow: false,
};

export default function Rearm({ editMode, ...props }) {
  return editMode ? <RearmEditor {...props} /> : <RearmViewer {...props} />;
}

Rearm.propTypes = {
  onChange: PropTypes.func,
  value: PropTypes.number.isRequired,
  editMode: PropTypes.bool,
  sendForEachRow: PropTypes.bool,
  onSendForEachRowChange: PropTypes.func,
};

Rearm.defaultProps = {
  onChange: null,
  editMode: false,
  sendForEachRow: false,
  onSendForEachRowChange: () => {},
};
