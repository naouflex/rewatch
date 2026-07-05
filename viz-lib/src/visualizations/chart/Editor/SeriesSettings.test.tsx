import React from "react";
import { render } from "@testing-library/react";

import { changeInputValue, clickByTestID, openSelect, toggleInput } from "@/testHelpers";

import getOptions from "../getOptions";
import SeriesSettings from "./SeriesSettings";

function renderSettings(options: any, done: any) {
  options = getOptions(options);
  return render(
    <SeriesSettings
      visualizationName="Test"
      data={{ columns: [{ name: "a", type: "string" }], rows: [{ a: "test" }] }}
      options={options}
      onOptionsChange={(changedOptions: any) => {
        expect(changedOptions).toMatchSnapshot();
        done();
      }}
    />
  );
}

describe("Visualizations -> Chart -> Editor -> Series Settings", () => {
  test("Changes series type", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        columnMapping: { a: "y" },
        seriesOptions: {
          a: { type: "column", label: "a", yAxis: 0 },
        },
      },
      done
    );

    openSelect("Chart.Series.a.Type");
    clickByTestID("Chart.ChartType.area");
  });

  test("Changes series label", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        columnMapping: { a: "y" },
        seriesOptions: {
          a: { type: "column", label: "a", yAxis: 0 },
        },
      },
      done
    );

    changeInputValue("Chart.Series.a.Label", "test");
  });

  test("Changes series axis", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        columnMapping: { a: "y" },
        seriesOptions: {
          a: { type: "column", name: "a", yAxis: 0 },
        },
      },
      done
    );

    toggleInput("Chart.Series.a.UseRightAxis");
  });
});
