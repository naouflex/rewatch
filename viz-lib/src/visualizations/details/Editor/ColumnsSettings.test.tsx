import React from "react";
import { render, fireEvent } from "@testing-library/react";

import { changeInputValue, clickByTestID, findByTestID, findInputByTestID, openSelect } from "@/testHelpers";

import getOptions from "../getOptions";
import ColumnsSettings from "./ColumnsSettings";

function renderSettings(options: any, done: any) {
  const data = {
    columns: [
      { name: "id", type: "integer" },
      { name: "name", type: "string" },
      { name: "created_at", type: "datetime" },
    ],
    rows: [{ id: 1, name: "test", created_at: "2023-01-01T00:00:00Z" }],
  };
  options = getOptions(options, data);
  return render(
    <ColumnsSettings
      visualizationName="Details"
      data={data}
      options={options}
      onOptionsChange={(changedOptions: any) => {
        expect(changedOptions).toMatchSnapshot();
        done();
      }}
    />
  );
}

describe("Visualizations -> Details -> Editor -> Columns Settings", () => {
  test("Toggles column visibility", done => {
    renderSettings({}, done);

    clickByTestID("Details.Column.id.Visibility");
  });

  test("Changes column title", done => {
    renderSettings({}, done);
    clickByTestID("Details.Column.name.Name"); // expand settings

    changeInputValue("Details.Column.name.Title", "Full Name");
  });

  test("Changes column alignment", done => {
    renderSettings({}, done);
    clickByTestID("Details.Column.id.Name"); // expand settings

    const alignment = findByTestID("Details.Column.id.TextAlignment");
    fireEvent.click(findInputByTestID("TextAlignmentSelect.Center", alignment));
  });

  test("Changes column description", done => {
    renderSettings({}, done);
    clickByTestID("Details.Column.name.Name"); // expand settings

    changeInputValue("Details.Column.name.Description", "User full name");
  });

  test("Changes column display type", done => {
    renderSettings({}, done);
    clickByTestID("Details.Column.created_at.Name"); // expand settings

    openSelect("Details.Column.created_at.DisplayAs");
    clickByTestID("Details.Column.created_at.DisplayAs.string");
  });

  test("Hides multiple columns", done => {
    renderSettings({}, done);

    clickByTestID("Details.Column.id.Visibility");
  });
});
