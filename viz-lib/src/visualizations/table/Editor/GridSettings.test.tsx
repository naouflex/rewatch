import React from "react";
import { render } from "@testing-library/react";

import { clickByTestID, openSelect } from "@/testHelpers";

import getOptions from "../getOptions";
import GridSettings from "./GridSettings";

function renderSettings(options: any, done: any) {
  const data = { columns: [], rows: [] };
  options = getOptions(options, data);
  return render(
    <GridSettings
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

describe("Visualizations -> Table -> Editor -> Grid Settings", () => {
  test("Changes items per page", done => {
    renderSettings(
      {
        itemsPerPage: 25,
      },
      done
    );

    openSelect("Table.ItemsPerPage");
    clickByTestID("Table.ItemsPerPage.100");
  });
});
