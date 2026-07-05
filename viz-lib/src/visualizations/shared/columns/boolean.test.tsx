import React from "react";
import { render } from "@testing-library/react";

import { changeInputValue } from "@/testHelpers";

import Column from "./boolean";

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

describe("Visualizations -> Table -> Columns -> Boolean", () => {
  describe("Editor", () => {
    test("Changes value for FALSE", done => {
      renderEditor(
        {
          name: "a",
          booleanValues: ["false", "true"],
        },
        done
      );

      changeInputValue("Table.ColumnEditor.Boolean.False", "no");
    });

    test("Changes value for TRUE", done => {
      renderEditor(
        {
          name: "a",
          booleanValues: ["false", "true"],
        },
        done
      );

      changeInputValue("Table.ColumnEditor.Boolean.True", "yes");
    });
  });
});
