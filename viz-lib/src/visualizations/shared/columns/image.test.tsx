import React from "react";
import { render } from "@testing-library/react";

import { changeInputValue } from "@/testHelpers";

import Column from "./image";

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

describe("Visualizations -> Table -> Columns -> Image", () => {
  describe("Editor", () => {
    test("Changes URL template", done => {
      renderEditor(
        {
          name: "a",
          imageUrlTemplate: "{{ @ }}",
        },
        done
      );

      changeInputValue("Table.ColumnEditor.Image.UrlTemplate", "http://{{ @ }}.jpeg");
    });

    test("Changes width", done => {
      renderEditor(
        {
          name: "a",
          imageWidth: null,
        },
        done
      );

      changeInputValue("Table.ColumnEditor.Image.Width", "400");
    });

    test("Changes height", done => {
      renderEditor(
        {
          name: "a",
          imageHeight: null,
        },
        done
      );

      changeInputValue("Table.ColumnEditor.Image.Height", "300");
    });

    test("Changes title template", done => {
      renderEditor(
        {
          name: "a",
          imageUrlTemplate: "{{ @ }}",
        },
        done
      );

      changeInputValue("Table.ColumnEditor.Image.TitleTemplate", "Image {{ @ }}");
    });
  });
});
