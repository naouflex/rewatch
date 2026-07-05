const { TextEncoder, TextDecoder } = require("util");

if (typeof global.ResizeObserver === "undefined") {
  global.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

if (typeof global.MessageChannel === "undefined") {
  global.MessageChannel = class MessageChannel {
    constructor() {
      this.port1 = { postMessage: () => {}, close: () => {} };
      this.port2 = { postMessage: () => {}, close: () => {} };
    }
  };
}


// react-dom/server (React 18) expects these globals, but jsdom doesn't provide them
if (typeof global.TextEncoder === "undefined") {
  global.TextEncoder = TextEncoder;
  global.TextDecoder = TextDecoder;
}

const MockDate = require("mockdate");

const date = new Date("2000-01-01T02:00:00.000");

MockDate.set(date);

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});
