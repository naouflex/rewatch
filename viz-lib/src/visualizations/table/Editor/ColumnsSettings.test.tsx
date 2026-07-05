import React from "react";
import { render, fireEvent } from "@testing-library/react";

import { changeInputValue, clickByTestID, findByTestID, findInputByTestID, openSelect, toggleInput } from "@/testHelpers";

import getOptions from "../getOptions";
import ColumnsSettings from "./ColumnsSettings";

function renderSettings(options: any, done: any) {
  const data = {
    columns: [{ name: "a", type: "string" }],
    rows: [{ a: "test" }],
  };
  options = getOptions(options, data);
  return render(
    <ColumnsSettings
      visualizationName="Test"
      data={data}
      options={options}
      onOptionsChange={(changedOptions: any) => {
        expect(changedOptions).toMatchSnapshot();
        done();
      }}
    />
  );
}

describe("Visualizations -> Table -> Editor -> Columns Settings", () => {
  test("Toggles column visibility", done => {
    renderSettings({}, done);

    clickByTestID("Table.Column.a.Visibility");
  });

  test("Changes column title", done => {
    renderSettings({}, done);
    clickByTestID("Table.Column.a.Name"); // expand settings

    changeInputValue("Table.Column.a.Title", "test");
  });

  test("Changes column alignment", done => {
    renderSettings({}, done);
    clickByTestID("Table.Column.a.Name"); // expand settings

    const alignment = findByTestID("Table.Column.a.TextAlignment");
    fireEvent.click(findInputByTestID("TextAlignmentSelect.Right", alignment));
  });

  test("Enables search by column data", done => {
    renderSettings({}, done);
    clickByTestID("Table.Column.a.Name"); // expand settings

    toggleInput("Table.Column.a.UseForSearch");
  });

  test("Changes column display type", done => {
    renderSettings({}, done);
    clickByTestID("Table.Column.a.Name"); // expand settings

    openSelect("Table.Column.a.DisplayAs");
    clickByTestID("Table.Column.a.DisplayAs.number");
  });
});
