import React from "react";
import { render } from "@testing-library/react";

import { clickByTestID, elementExists, openSelect, toggleInput } from "@/testHelpers";

import getOptions from "../getOptions";
import GeneralSettings from "./GeneralSettings";

function renderSettings(options: any, done?: any) {
  options = getOptions(options);
  return render(
    <GeneralSettings
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

describe("Visualizations -> Chart -> Editor -> General Settings", () => {
  test("Changes global series type", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        showDataLabels: false,
        seriesOptions: {
          a: { type: "column" },
          b: { type: "line" },
        },
      },
      done
    );

    openSelect("Chart.GlobalSeriesType");
    clickByTestID("Chart.ChartType.pie");
  });

  test("Pie: changes direction", done => {
    renderSettings(
      {
        globalSeriesType: "pie",
        direction: { type: "counterclockwise" },
      },
      done
    );

    openSelect("Chart.PieDirection");
    clickByTestID("Chart.PieDirection.Clockwise");
  });

  test("Toggles legend", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        legend: { enabled: true },
      },
      done
    );

    openSelect("Chart.LegendPlacement");
    clickByTestID("Chart.LegendPlacement.HideLegend");
  });

  test("Box: toggles show points", done => {
    renderSettings(
      {
        globalSeriesType: "box",
        showpoints: false,
      },
      done
    );

    toggleInput("Chart.ShowPoints");
  });

  test("Enables stacking", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        series: {},
      },
      done
    );

    openSelect("Chart.Stacking");
    clickByTestID("Chart.Stacking.Stack");
  });

  test("Toggles normalize values to percentage", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        series: {},
      },
      done
    );

    toggleInput("Chart.NormalizeValues");
  });

  test("Keep missing/null values", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        missingValuesAsZero: true,
      },
      done
    );

    openSelect("Chart.MissingValues");
    clickByTestID("Chart.MissingValues.Keep");
  });

  describe("Column mappings should be available", () => {
    test("for bubble", () => {
      renderSettings({
        globalSeriesType: "column",
        seriesOptions: {
          a: { type: "column" },
          b: { type: "bubble" },
          c: { type: "heatmap" },
        },
      });

      expect(elementExists("Chart.ColumnMapping.x")).toBeTruthy();
      expect(elementExists("Chart.ColumnMapping.y")).toBeTruthy();
      expect(elementExists("Chart.ColumnMapping.size")).toBeTruthy();
    });

    test("for heatmap", () => {
      renderSettings({
        globalSeriesType: "heatmap",
        seriesOptions: {
          a: { type: "column" },
          b: { type: "bubble" },
          c: { type: "heatmap" },
        },
      });

      expect(elementExists("Chart.ColumnMapping.x")).toBeTruthy();
      expect(elementExists("Chart.ColumnMapping.y")).toBeTruthy();
      expect(elementExists("Chart.ColumnMapping.zVal")).toBeTruthy();
    });

    test("for all types except of bubble, heatmap and custom", () => {
      renderSettings({
        globalSeriesType: "column",
        seriesOptions: {
          a: { type: "column" },
          b: { type: "bubble" },
          c: { type: "heatmap" },
        },
      });

      expect(elementExists("Chart.ColumnMapping.x")).toBeTruthy();
      expect(elementExists("Chart.ColumnMapping.y")).toBeTruthy();
      expect(elementExists("Chart.ColumnMapping.series")).toBeTruthy();
      expect(elementExists("Chart.ColumnMapping.yError")).toBeTruthy();
    });
  });

  test("Toggles horizontal bar chart", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        series: {},
      },
      done
    );

    toggleInput("Chart.SwappedAxes");
  });

  test("Toggles Enable click events", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        series: {},
      },
      done
    );

    toggleInput("Chart.EnableClickEvents");
  });
});
