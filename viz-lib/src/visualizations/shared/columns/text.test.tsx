import React from "react";
import { render } from "@testing-library/react";

import { toggleInput } from "@/testHelpers";

import Column from "./text";

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

describe("Visualizations -> Table -> Columns -> Text", () => {
  describe("Editor", () => {
    test("Enables HTML content", done => {
      renderEditor(
        {
          name: "a",
          allowHTML: false,
          highlightLinks: false,
        },
        done
      );

      toggleInput("Table.ColumnEditor.Text.AllowHTML");
    });

    test("Enables highlight links option", done => {
      renderEditor(
        {
          name: "a",
          allowHTML: true,
          highlightLinks: false,
        },
        done
      );

      toggleInput("Table.ColumnEditor.Text.HighlightLinks");
    });
  });
});
