import React from "react";
import { render } from "@testing-library/react";

import { changeInputValue, toggleInput } from "@/testHelpers";

import Column from "./link";

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

describe("Visualizations -> Table -> Columns -> Link", () => {
  describe("Editor", () => {
    test("Changes URL template", done => {
      renderEditor(
        {
          name: "a",
          linkUrlTemplate: "{{ @ }}",
        },
        done
      );

      changeInputValue("Table.ColumnEditor.Link.UrlTemplate", "http://{{ @ }}/index.html");
    });

    test("Changes text template", done => {
      renderEditor(
        {
          name: "a",
          linkTextTemplate: "{{ @ }}",
        },
        done
      );

      changeInputValue("Table.ColumnEditor.Link.TextTemplate", "Text of {{ @ }}");
    });

    test("Changes title template", done => {
      renderEditor(
        {
          name: "a",
          linkTitleTemplate: "{{ @ }}",
        },
        done
      );

      changeInputValue("Table.ColumnEditor.Link.TitleTemplate", "Title of {{ @ }}");
    });

    test("Makes link open in new tab ", done => {
      renderEditor(
        {
          name: "a",
          linkOpenInNewTab: false,
        },
        done
      );

      toggleInput("Table.ColumnEditor.Link.OpenInNewTab");
    });
  });
});
