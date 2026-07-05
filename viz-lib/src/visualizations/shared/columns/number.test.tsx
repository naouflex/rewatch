import React from "react";
import { render } from "@testing-library/react";

import { changeInputValue } from "@/testHelpers";

import Column from "./number";

function renderEditor(column: any, done: any) {
  return render(
    <Column.Editor
      // @ts-expect-error ts-migrate(2322) FIXME: Type '{ visualizationName: string; column: any; on... Remove this comment to see the full error message
      visualizationName="Test"
      column={column}
      onChange={(changedColumn: any) => {
        expect(changedColumn).toMatchSnapshot();
        done();
      }}
    />
  );
}

describe("Visualizations -> Table -> Columns -> Number", () => {
  describe("Editor", () => {
    test("Changes format", done => {
      renderEditor(
        {
          name: "a",
          numberFormat: "0[.]0000",
        },
        done
      );

      changeInputValue("Table.ColumnEditor.Number.Format", "0.00%");
    });
  });
});
