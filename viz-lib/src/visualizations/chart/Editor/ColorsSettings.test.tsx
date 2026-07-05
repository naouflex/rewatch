import { after } from "lodash";
import React from "react";
import { render, fireEvent } from "@testing-library/react";

import { changeInputValue, clickByTestID, findByTestID, openSelect } from "@/testHelpers";

import getOptions from "../getOptions";
import ColorsSettings from "./ColorsSettings";

function clickColorPickerTrigger(testId: string) {
  const el = findByTestID(testId);
  const triggers = el.matches(".color-picker-trigger")
    ? [el]
    : Array.from(el.querySelectorAll(".color-picker-trigger"));
  fireEvent.click(triggers[triggers.length - 1]);
}

function renderSettings(options: any, done: any) {
  options = getOptions(options);
  return render(
    <ColorsSettings
      visualizationName="Test"
      data={{
        columns: [
          { name: "a", type: "string" },
          { name: "b", type: "number" },
        ],
        rows: [{ a: "v", b: 3.14 }],
      }}
      options={options}
      onOptionsChange={(changedOptions: any) => {
        expect(changedOptions).toMatchSnapshot();
        done();
      }}
    />
  );
}

describe("Visualizations -> Chart -> Editor -> Colors Settings", () => {
  describe("for pie", () => {
    test("Changes series color", done => {
      renderSettings(
        {
          globalSeriesType: "pie",
          columnMapping: { a: "x", b: "y" },
        },
        done
      );

      clickColorPickerTrigger("Chart.Series.v.Color");
      changeInputValue("ColorPicker", "red");
    });
  });

  describe("for heatmap", () => {
    test("Changes color scheme", done => {
      renderSettings(
        {
          globalSeriesType: "heatmap",
          columnMapping: { a: "x", b: "y" },
        },
        done
      );

      openSelect("Chart.Colors.Heatmap.ColorScheme");
      clickByTestID("Chart.Colors.Heatmap.ColorScheme.Blues");
    });

    test("Sets custom color scheme", done => {
      renderSettings(
        {
          globalSeriesType: "heatmap",
          columnMapping: { a: "x", b: "y" },
          colorScheme: "Custom...",
        },
        after(2, done)
      ); // we will perform 2 actions, so call `done` after all of them completed

      clickColorPickerTrigger("Chart.Colors.Heatmap.MinColor");
      changeInputValue("ColorPicker", "yellow");

      clickColorPickerTrigger("Chart.Colors.Heatmap.MaxColor");
      changeInputValue("ColorPicker", "red");
    });
  });

  describe("for all except of pie and heatmap", () => {
    test("Changes series color", done => {
      renderSettings(
        {
          globalSeriesType: "column",
          columnMapping: { a: "x", b: "y" },
        },
        done
      );

      clickColorPickerTrigger("Chart.Series.b.Color");
      changeInputValue("ColorPicker", "red");
    });
  });
});
