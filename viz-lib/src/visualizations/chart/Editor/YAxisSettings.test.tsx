import React from "react";
import { render } from "@testing-library/react";

import { changeInputValue, clickByTestID, elementExists, openSelect } from "@/testHelpers";

import getOptions from "../getOptions";
import YAxisSettings from "./YAxisSettings";

function renderSettings(options: any, done?: any) {
  options = getOptions(options);
  return render(
    <YAxisSettings
      visualizationName="Test"
      data={{ columns: [], rows: [] }}
      options={options}
      onOptionsChange={(changedOptions: any) => {
        expect(changedOptions).toMatchSnapshot();
        done();
      }}
    />
  );
}

describe("Visualizations -> Chart -> Editor -> Y-Axis Settings", () => {
  test("Changes axis type", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        yAxis: [{ type: "linear" }, { type: "linear", opposite: true }],
      },
      done
    );

    openSelect("Chart.LeftYAxis.Type");
    clickByTestID("Chart.LeftYAxis.Type.Category");
  });

  test("Changes axis name", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        yAxis: [{ type: "linear" }, { type: "linear", opposite: true }],
      },
      done
    );

    changeInputValue("Chart.LeftYAxis.Name", "test");
  });

  test("Changes axis tick format", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        yAxis: [],
      },
      done
    );

    changeInputValue("Chart.LeftYAxis.TickFormat", "s");
  });

  test("Changes axis min value", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        yAxis: [{ type: "linear" }, { type: "linear", opposite: true }],
      },
      done
    );

    changeInputValue("Chart.LeftYAxis.RangeMin", "50");
  });

  test("Changes axis max value", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        yAxis: [{ type: "linear" }, { type: "linear", opposite: true }],
      },
      done
    );

    changeInputValue("Chart.LeftYAxis.RangeMax", "200");
  });

  describe("for non-heatmap", () => {
    test("Right Y Axis should be available", () => {
      renderSettings({
        globalSeriesType: "column",
        yAxis: [{ type: "linear" }, { type: "linear", opposite: true }],
      });

      expect(elementExists("Chart.RightYAxis.Type")).toBeTruthy();
    });
  });

  describe("for heatmap", () => {
    test("Right Y Axis should not be available", () => {
      renderSettings({
        globalSeriesType: "heatmap",
        yAxis: [{ type: "linear" }, { type: "linear", opposite: true }],
      });

      expect(elementExists("Chart.RightYAxis.Type")).toBeFalsy();
    });

    test("Sets Sort X Values option", done => {
      renderSettings(
        {
          globalSeriesType: "heatmap",
          sortY: false,
        },
        done
      );

      clickByTestID("Chart.LeftYAxis.Sort");
    });

    test("Sets Reverse Y Values option", done => {
      renderSettings(
        {
          globalSeriesType: "heatmap",
          reverseY: false,
        },
        done
      );

      clickByTestID("Chart.LeftYAxis.Reverse");
    });
  });
});
