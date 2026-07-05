import React from "react";
import { render, fireEvent } from "@testing-library/react";

import { findAllByTestID, findByTestID, findInputByTestID, openSelect, clickByTestID } from "@/testHelpers";

import ColumnEditor from "./ColumnEditor";

function renderEditor(column: any, variant: "table" | "details", onChange: any = jest.fn()) {
  return render(<ColumnEditor column={column} variant={variant} onChange={onChange} />);
}

const mockColumn = {
  name: "user_id",
  title: "user_id",
  visible: true,
  alignContent: "left" as const,
  displayAs: "string",
  description: "",
  allowSearch: false,
};

describe("Shared ColumnEditor", () => {
  describe("Common functionality", () => {
    test.each(["table", "details"] as const)("Changes column title - %s variant", async variant => {
      return new Promise<void>(resolve => {
        const onChange = jest.fn(changes => {
          expect(changes).toEqual({
            ...mockColumn,
            title: "User ID",
          });
          resolve();
        });
        renderEditor(mockColumn, variant, onChange);

        const testPrefix = variant === "table" ? "Table" : "Details";
        fireEvent.change(findInputByTestID(`${testPrefix}.Column.user_id.Title`), {
          target: { value: "User ID" },
        });
      });
    });

    test.each(["table", "details"] as const)("Changes column alignment - %s variant", variant => {
      const onChange = jest.fn();
      renderEditor(
        {
          ...mockColumn,
          name: "amount",
          displayAs: "number",
        },
        variant,
        onChange
      );

      const testPrefix = variant === "table" ? "Table" : "Details";
      const alignment = findByTestID(`${testPrefix}.Column.amount.TextAlignment`);
      fireEvent.click(alignment.querySelector('input[value="right"]') as HTMLElement);

      expect(onChange).toHaveBeenCalledWith({
        ...mockColumn,
        name: "amount",
        displayAs: "number",
        alignContent: "right",
      });
    });

    test.each(["table", "details"] as const)("Changes column description - %s variant", async variant => {
      return new Promise<void>(resolve => {
        const onChange = jest.fn(changes => {
          expect(changes).toEqual({
            ...mockColumn,
            name: "status",
            title: "Status",
            description: "Current order status",
          });
          resolve();
        });
        renderEditor(
          {
            ...mockColumn,
            name: "status",
            title: "Status",
          },
          variant,
          onChange
        );

        const testPrefix = variant === "table" ? "Table" : "Details";
        fireEvent.change(findInputByTestID(`${testPrefix}.Column.status.Description`), {
          target: { value: "Current order status" },
        });
      });
    });

    test.each(["table", "details"] as const)("Changes display type - %s variant", variant => {
      const onChange = jest.fn();
      renderEditor(
        {
          ...mockColumn,
          name: "created_at",
          title: "Created At",
          displayAs: "datetime",
        },
        variant,
        onChange
      );

      const testPrefix = variant === "table" ? "Table" : "Details";
      openSelect(`${testPrefix}.Column.created_at.DisplayAs`);
      clickByTestID(`${testPrefix}.Column.created_at.DisplayAs.string`);

      expect(onChange).toHaveBeenCalledWith({
        ...mockColumn,
        name: "created_at",
        title: "Created At",
        displayAs: "string",
      });
    });
  });

  describe("Table variant specific", () => {
    test("Shows search checkbox", () => {
      renderEditor(mockColumn, "table");

      const searchCheckbox = findInputByTestID("Table.Column.user_id.UseForSearch");
      expect(searchCheckbox.matches("input[type='checkbox']")).toBe(true);
    });

    test("Changes search setting", () => {
      const onChange = jest.fn();
      renderEditor(
        {
          ...mockColumn,
          allowSearch: false,
        },
        "table",
        onChange
      );

      fireEvent.click(findInputByTestID("Table.Column.user_id.UseForSearch"));

      expect(onChange).toHaveBeenCalledWith({
        ...mockColumn,
        allowSearch: true,
      });
    });

    test("Uses correct CSS class", () => {
      const { container } = renderEditor(mockColumn, "table");
      expect(container.querySelectorAll(".table-visualization-editor-column")).toHaveLength(1);
    });
  });

  describe("Details variant specific", () => {
    test("Hides search checkbox", () => {
      const { container } = renderEditor(mockColumn, "details");

      expect(container.querySelectorAll('[data-test="Details.Column.user_id.UseForSearch"]')).toHaveLength(0);
    });

    test("Uses correct CSS class", () => {
      const { container } = renderEditor(mockColumn, "details");
      expect(container.querySelectorAll(".details-visualization-editor-column")).toHaveLength(1);
    });
  });

  describe("Props and defaults", () => {
    test("Uses default showSearch based on variant", () => {
      const { container: tableContainer } = renderEditor(mockColumn, "table");
      const { container: detailsContainer } = renderEditor(mockColumn, "details");

      expect(findInputByTestID("Table.Column.user_id.UseForSearch", tableContainer)).toBeTruthy();
      expect(detailsContainer.querySelectorAll('[data-test="Details.Column.user_id.UseForSearch"]')).toHaveLength(0);
    });

    test("Allows custom testPrefix", () => {
      const { rerender } = renderEditor(mockColumn, "table");
      rerender(<ColumnEditor column={mockColumn} variant="table" onChange={jest.fn()} testPrefix="Custom.Prefix" />);

      expect(findInputByTestID("Custom.Prefix.Title")).toBeTruthy();
    });

    test("Handles missing onChange gracefully", () => {
      renderEditor(mockColumn, "table", undefined);

      expect(() => {
        fireEvent.change(findInputByTestID("Table.Column.user_id.Title"), { target: { value: "New Title" } });
      }).not.toThrow();
    });
  });

  describe("Rendering", () => {
    test("Table variant renders with correct structure", () => {
      const { container } = renderEditor(
        {
          ...mockColumn,
          allowSearch: true,
          description: "Sample description",
        },
        "table"
      );

      // Verify key elements are present
      expect(container.querySelectorAll(".table-visualization-editor-column")).toHaveLength(1);
      expect(findInputByTestID("Table.Column.user_id.Title", container)).toBeTruthy();
      expect(
        findByTestID("Table.Column.user_id.TextAlignment", container).querySelectorAll("input[type='radio']")
      ).toHaveLength(3);
      expect(findInputByTestID("Table.Column.user_id.UseForSearch", container).matches("input[type='checkbox']")).toBe(
        true
      );
      expect(findInputByTestID("Table.Column.user_id.Description", container)).toBeTruthy();
      expect(findAllByTestID("Table.Column.user_id.DisplayAs", container).length).toBeGreaterThan(0);
    });

    test("Details variant renders with correct structure", () => {
      const { container } = renderEditor(
        {
          ...mockColumn,
          description: "Sample description",
        },
        "details"
      );

      // Verify key elements are present
      expect(container.querySelectorAll(".details-visualization-editor-column")).toHaveLength(1);
      expect(findInputByTestID("Details.Column.user_id.Title", container)).toBeTruthy();
      expect(
        findByTestID("Details.Column.user_id.TextAlignment", container).querySelectorAll("input[type='radio']")
      ).toHaveLength(3);
      expect(container.querySelectorAll('[data-test="Details.Column.user_id.UseForSearch"]')).toHaveLength(0); // Should not exist
      expect(findInputByTestID("Details.Column.user_id.Description", container)).toBeTruthy();
      expect(findAllByTestID("Details.Column.user_id.DisplayAs", container).length).toBeGreaterThan(0);
    });
  });
});
