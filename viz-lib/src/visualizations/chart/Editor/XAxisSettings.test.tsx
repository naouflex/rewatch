import React from "react";
import { render } from "@testing-library/react";

import { changeInputValue, clickByTestID, openSelect } from "@/testHelpers";

import getOptions from "../getOptions";
import XAxisSettings from "./XAxisSettings";

function renderSettings(options: any, done: any) {
  options = getOptions(options);
  return render(
    <XAxisSettings
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

describe("Visualizations -> Chart -> Editor -> X-Axis Settings", () => {
  test("Changes axis type", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        xAxis: { type: "-", labels: { enabled: true } },
      },
      done
    );

    openSelect("Chart.XAxis.Type");
    clickByTestID("Chart.XAxis.Type.Linear");
  });

  test("Changes axis name", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        xAxis: { type: "-", labels: { enabled: true } },
      },
      done
    );

    changeInputValue("Chart.XAxis.Name", "test");
  });

  test("Changes axis tick format", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        xAxis: {},
      },
      done
    );

    changeInputValue("Chart.XAxis.TickFormat", "%B");
  });

  test("Sets Show Labels option", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        xAxis: { type: "-", labels: { enabled: false } },
      },
      done
    );

    clickByTestID("Chart.XAxis.ShowLabels");
  });

  test("Sets Sort X Values option", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        sortX: false,
      },
      done
    );

    clickByTestID("Chart.XAxis.Sort");
  });

  test("Sets Reverse X Values option", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        reverseX: false,
      },
      done
    );

    clickByTestID("Chart.XAxis.Reverse");
  });
});
