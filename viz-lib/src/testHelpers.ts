import { fireEvent } from "@testing-library/react";

// Antd renders dropdowns, popovers and modals in portals attached to
// `document.body`, so queries run against the whole document by default.

export function findAllByTestID(testId: string, scope: ParentNode = document): HTMLElement[] {
  return Array.from(scope.querySelectorAll<HTMLElement>(`[data-test="${testId}"]`));
}

export function findByTestID(testId: string, scope: ParentNode = document): HTMLElement {
  const matches = findAllByTestID(testId, scope);
  if (matches.length === 0) {
    throw new Error(`Element with data-test="${testId}" not found`);
  }
  return matches[matches.length - 1];
}

export function elementExists(testId: string, scope: ParentNode = document): boolean {
  return findAllByTestID(testId, scope).length > 0;
}

// Returns the native input/textarea for a test id — the attribute may sit on
// the input itself or on a wrapper element around it.
export function findInputByTestID(testId: string, scope: ParentNode = document): HTMLElement {
  const el = findByTestID(testId, scope);
  if (el.matches("input, textarea")) {
    return el;
  }
  const input = el.querySelector<HTMLElement>("input, textarea");
  if (!input) {
    throw new Error(`No input found within element with data-test="${testId}"`);
  }
  return input;
}

export function changeInputValue(testId: string, value: string, scope: ParentNode = document) {
  fireEvent.change(findInputByTestID(testId, scope), { target: { value } });
}

// Toggles antd Checkbox/Switch/Radio controls: clicking the native input
// flips `checked` and fires the change event, which is what rc-checkbox &co
// listen for (fireEvent.change alone does not toggle checkboxes in jsdom).
export function toggleInput(testId: string, scope: ParentNode = document) {
  fireEvent.click(findInputByTestID(testId, scope));
}

// Opens an antd Select dropdown (rc-select listens for mousedown on the
// `.ant-select-selector` element).
export function openSelect(testId: string, scope: ParentNode = document) {
  const el = findByTestID(testId, scope);
  const selector = el.matches(".ant-select-selector")
    ? el
    : el.querySelector(".ant-select-selector") || el.closest(".ant-select")?.querySelector(".ant-select-selector") || el;
  fireEvent.mouseDown(selector);
}

export function clickByTestID(testId: string, scope: ParentNode = document) {
  fireEvent.click(findByTestID(testId, scope));
}
