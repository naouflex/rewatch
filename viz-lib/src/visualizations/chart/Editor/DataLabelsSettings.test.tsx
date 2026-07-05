import React from "react";
import { render } from "@testing-library/react";

import { changeInputValue, toggleInput } from "@/testHelpers";

import getOptions from "../getOptions";
import DataLabelsSettings from "./DataLabelsSettings";

function renderSettings(options: any, done: any) {
  options = getOptions(options);
  return render(
    <DataLabelsSettings
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

describe("Visualizations -> Chart -> Editor -> Data Labels Settings", () => {
  test("Sets Show Data Labels option", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        showDataLabels: false,
      },
      done
    );

    toggleInput("Chart.DataLabels.ShowDataLabels");
  });

  test("Changes number format", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        numberFormat: "0[.]0000",
      },
      done
    );

    changeInputValue("Chart.DataLabels.NumberFormat", "0.00");
  });

  test("Changes percent values format", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        percentFormat: "0[.]00%",
      },
      done
    );

    changeInputValue("Chart.DataLabels.PercentFormat", "0.0%");
  });

  test("Changes date/time format", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        dateTimeFormat: "YYYY-MM-DD HH:mm:ss",
      },
      done
    );

    changeInputValue("Chart.DataLabels.DateTimeFormat", "YYYY MMM DD");
  });

  test("Changes data labels format", done => {
    renderSettings(
      {
        globalSeriesType: "column",
        textFormat: null,
      },
      done
    );

    changeInputValue("Chart.DataLabels.TextFormat", "{{ @@x }} :: {{ @@y }} / {{ @@yPercent }}");
  });
});
