import React from "react";
import { render, fireEvent } from "@testing-library/react";
import moment from "moment";

import Renderer from "./Renderer";
import getOptions from "./getOptions";

function renderComponent(data: any, options: any = {}) {
  options = getOptions(options, data);
  return render(<Renderer data={data} options={options} />);
}

describe("Visualizations -> Details -> Renderer", () => {
  const sampleData = {
    columns: [
      { name: "id", type: "integer" },
      { name: "name", type: "string" },
      { name: "created_at", type: "datetime" },
      { name: "active", type: "boolean" },
    ],
    rows: [
      {
        id: 1,
        name: "John Doe",
        created_at: moment("2023-01-01T12:00:00Z"),
        active: true,
      },
      {
        id: 2,
        name: "Jane Smith",
        created_at: moment("2023-02-01T12:00:00Z"),
        active: false,
      },
    ],
  };

  test("Renders all columns when no options provided", () => {
    const { container } = renderComponent(sampleData);

    const text = container.textContent || "";
    expect(text).toContain("id");
    expect(text).toContain("name");
    expect(text).toContain("created_at");
    expect(text).toContain("active");
    expect(text).toContain("1"); // id value
    expect(text).toContain("John Doe"); // name value
  });

  test("Renders only visible columns", () => {
    const options = {
      columns: [
        { name: "id", visible: true, order: 0 },
        { name: "name", visible: false, order: 1 },
        { name: "created_at", visible: true, order: 2 },
        { name: "active", visible: false, order: 3 },
      ],
    };

    const { container } = renderComponent(sampleData, options);

    const text = container.textContent || "";
    // Should show id and created_at, but not name and active
    expect(text).toContain("id");
    expect(text).toContain("created_at");
    expect(text).not.toContain("name");
    expect(text).not.toContain("active");
  });

  test("Respects column order", () => {
    const options = {
      columns: [
        { name: "active", visible: true, order: 0 },
        { name: "name", visible: true, order: 1 },
        { name: "created_at", visible: true, order: 2 },
        { name: "id", visible: true, order: 3 },
      ],
    };

    const { container } = renderComponent(sampleData, options);

    // Get all description item labels in order
    const labels = Array.from(container.querySelectorAll(".ant-descriptions-item-label")).map(
      node => node.textContent
    );

    // Should appear in order: active (0), name (1), created_at (2), id (3)
    expect(labels).toEqual(["active", "name", "created_at", "id"]);
  });

  test("Uses custom column titles", () => {
    const options = {
      columns: [
        { name: "id", visible: true, title: "User ID", order: 0 },
        { name: "name", visible: true, title: "Full Name", order: 1 },
      ],
    };

    const { container } = renderComponent(sampleData, options);

    const text = container.textContent || "";
    expect(text).toContain("User ID");
    expect(text).toContain("Full Name");
  });

  test("Applies text alignment", () => {
    const options = {
      columns: [
        { name: "id", visible: true, alignContent: "center", order: 0 },
        { name: "name", visible: true, alignContent: "right", order: 1 },
      ],
    };

    const { container } = renderComponent(sampleData, options);

    // Check that alignment styles are applied
    const alignedDivs = container.querySelectorAll("div[style]");
    expect(alignedDivs.length).toBeGreaterThan(0);
  });

  test("Shows pagination for multiple rows", () => {
    const { container } = renderComponent(sampleData);

    // Check that pagination is present - look for pagination elements
    const paginationElements = container.querySelectorAll('[class*="paginator"]');
    expect(paginationElements.length).toBeGreaterThan(0);
  });

  test("Hides pagination for single row", () => {
    const singleRowData = {
      ...sampleData,
      rows: [sampleData.rows[0]],
    };

    const { container } = renderComponent(singleRowData);

    // Check that pagination is not present for single row
    const paginationElements = container.querySelectorAll('[class*="paginator"]');
    expect(paginationElements.length).toBe(0);
  });

  test("Handles empty data", () => {
    const emptyData = {
      columns: [],
      rows: [],
    };

    const { container } = renderComponent(emptyData);

    expect(container.firstChild).toBeNull();
  });

  test("Handles null data", () => {
    // Suppress PropTypes warning for this test
    const originalError = console.error;
    console.error = jest.fn();

    // Test the component directly with null data instead of using render helper
    const { container } = render(<Renderer data={null as any} options={{}} />);

    expect(container.firstChild).toBeNull();

    // Restore console.error
    console.error = originalError;
  });

  test("Navigates between rows with pagination", () => {
    const { container } = renderComponent(sampleData);

    // Check first row is displayed
    expect(container.textContent).toContain("John Doe");
    expect(container.textContent).not.toContain("Jane Smith");

    // Find and click next button
    const buttons = Array.from(container.querySelectorAll("button"));
    const nextButton = buttons.find(
      button => (button.textContent || "").includes("Next") || button.getAttribute("aria-label") === "Next Page"
    );
    if (nextButton) {
      fireEvent.click(nextButton);

      // Check second row is displayed after state update
      expect(container.textContent).toContain("Jane Smith");
    }
  });
});
