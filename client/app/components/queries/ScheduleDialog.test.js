import React from "react";
import { render, fireEvent, screen, act } from "@testing-library/react";
import moment from "moment";
import { durationHumanize } from "@/lib/utils";
import ScheduleDialog, { TimeEditor } from "./ScheduleDialog";
import RefreshScheduleDefault from "../proptypes";

const defaultProps = {
  schedule: RefreshScheduleDefault,
  refreshOptions: [
    60,
    300,
    600, // 1, 5 ,10 mins
    3600,
    36000,
    82800, // 1, 10, 23 hours
    86400,
    172800,
    518400, // 1, 2, 6 days
    604800,
    1209600, // 1, 2, 4 weeks
  ],
  dialog: {
    props: {
      open: true,
      onOk: () => {},
      onCancel: () => {},
      afterClose: () => {},
    },
    close: () => {},
    dismiss: () => {},
  },
};

function renderDialog(schedule = {}, { onConfirm, onCancel, ...props } = {}) {
  onConfirm = onConfirm || (() => {});
  onCancel = onCancel || (() => {});

  props = {
    ...defaultProps,
    ...props,
    schedule: {
      ...RefreshScheduleDefault,
      ...schedule,
    },
    dialog: {
      props: {
        open: true,
        onOk: onConfirm,
        onCancel,
        afterClose: () => {},
      },
      close: onConfirm,
      dismiss: onCancel,
    },
  };

  const ref = React.createRef();
  render(<ScheduleDialog.Component ref={ref} {...props} />);
  return [ref, props];
}

describe("ScheduleDialog", () => {
  describe("Sets correct schedule settings", () => {
    test('Sets to "Never"', () => {
      renderDialog();
      expect(screen.getByTestId("interval")).toMatchSnapshot();
    });

    test('Sets to "5 Minutes"', () => {
      renderDialog({ interval: 300 });
      expect(screen.getByTestId("interval")).toMatchSnapshot();
    });

    test('Sets to "2 Hours"', () => {
      renderDialog({ interval: 7200 });
      expect(screen.getByTestId("interval")).toMatchSnapshot();
    });

    describe('Sets to "1 Day 22:15"', () => {
      const schedule = {
        interval: 86400,
        time: "22:15",
      };

      test("Sets to correct interval", () => {
        renderDialog(schedule);
        expect(screen.getByTestId("interval")).toMatchSnapshot();
      });

      test("Sets to correct time", () => {
        renderDialog(schedule);
        expect(screen.getByTestId("time")).toMatchSnapshot();
      });
    });

    describe("TimeEditor", () => {
      const defaultValue = moment().hour(5).minute(25); // 05:25

      test("UTC set correctly on init", () => {
        render(<TimeEditor defaultValue={defaultValue} onChange={() => {}} />);
        const utc = screen.getByTestId("utc");

        // expect utc to be 2h below initial time
        expect(utc.textContent).toBe("(03:25 UTC)");
      });

      test("UTC time should not render", () => {
        const utcValue = moment.utc(defaultValue);
        render(<TimeEditor defaultValue={utcValue} onChange={() => {}} />);

        // expect utc to not render
        expect(screen.queryByTestId("utc")).toBeNull();
      });
    });

    describe('Sets to "2 Weeks 22:15 Tuesday"', () => {
      const schedule = {
        interval: 1209600,
        time: "22:15",
        day_of_week: "Monday",
      };

      test("Sets to correct interval", () => {
        renderDialog(schedule);
        expect(screen.getByTestId("interval")).toMatchSnapshot();
      });

      test("Sets to correct time", () => {
        renderDialog(schedule);
        expect(screen.getByTestId("time")).toMatchSnapshot();
      });

      test("Sets to correct weekday", () => {
        renderDialog(schedule);
        expect(screen.getByTestId("weekday")).toMatchSnapshot();
      });
    });

    describe("Until feature", () => {
      test("Until not set", () => {
        renderDialog({ interval: 300 });
        expect(screen.getByTestId("ends")).toMatchSnapshot();
      });

      test("Until is set", () => {
        renderDialog({ interval: 300, until: "2030-01-01" });
        expect(screen.getByTestId("ends")).toMatchSnapshot();
      });
    });

    describe("Supports 30 days interval with no time value", () => {
      test("Time is none", () => {
        renderDialog({ interval: 30 * 24 * 3600 });
        expect(screen.queryByTestId("time")).toMatchSnapshot();
      });
    });
  });

  describe("Adheres to user permissions", () => {
    test("Shows correct interval options", () => {
      const refreshOptions = [60, 300, 3600, 7200]; // 1 min, 5 min, 1 hour, 2 hours
      const [ref] = renderDialog(null, { refreshOptions });

      // Verify the dialog component instance's computed intervals
      const intervals = ref.current.intervals;

      // Flatten all interval options to [label, seconds] pairs, prepend "Never"
      const allOptions = ["Never"];
      Object.keys(intervals)
        .filter(key => intervals[key].length > 0)
        .forEach(key => {
          intervals[key].forEach(([, secs]) => {
            allOptions.push(durationHumanize(secs));
          });
        });

      const expected = ["Never", "1 minute", "5 minutes", "1 hour", "2 hours"];

      expect(allOptions).toEqual(expected);
    });
  });

  describe("Modal Confirm/Cancel feature", () => {
    const confirmCb = jest.fn().mockName("confirmCb");
    const closeCb = jest.fn().mockName("closeCb");
    const initProps = { onConfirm: confirmCb, onCancel: closeCb };

    beforeEach(() => {
      jest.clearAllMocks();
    });

    function clickModalButton(selector) {
      const footer = document.querySelector(".ant-modal-footer");
      fireEvent.click(footer.querySelector(selector));
    }

    test("Query saved on confirm if state changed", () => {
      // init
      const [ref, props] = renderDialog(null, initProps);

      // change state
      const change = { time: "22:15" };
      const newSchedule = Object.assign({}, props.schedule, change);
      act(() => {
        ref.current.setState({ newSchedule });
      });

      // click confirm button
      clickModalButton(".ant-btn-primary");

      // expect calls
      expect(confirmCb).toHaveBeenCalled();
      expect(closeCb).toHaveBeenCalled();
    });

    test("Query not saved on confirm if state unchanged", () => {
      // init
      renderDialog(null, initProps);

      // click confirm button
      clickModalButton(".ant-btn-primary");

      // expect calls
      expect(confirmCb).not.toHaveBeenCalled();
      expect(closeCb).toHaveBeenCalled();
    });

    test("Cancel closes modal and query unsaved", () => {
      // init
      const [ref, props] = renderDialog(null, initProps);

      // change state
      const change = { time: "22:15" };
      const newSchedule = Object.assign({}, props.schedule, change);
      act(() => {
        ref.current.setState({ newSchedule });
      });

      // click cancel button
      clickModalButton("button:not(.ant-btn-primary)");

      // expect calls
      expect(confirmCb).not.toHaveBeenCalled();
      expect(closeCb).toHaveBeenCalled();
    });
  });
});
