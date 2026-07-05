import React from "react";
import { render } from "@testing-library/react";

import { changeInputValue } from "@/testHelpers";

import Column from "./datetime";

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

describe("Visualizations -> Table -> Columns -> Date/Time", () => {
  describe("Editor", () => {
    test("Changes format", done => {
      renderEditor(
        {
          name: "a",
          dateTimeFormat: "YYYY-MM-DD HH:mm:ss",
        },
        done
      );

      changeInputValue("Table.ColumnEditor.DateTime.Format", "YYYY/MM/DD HH:ss");
    });
  });
});
