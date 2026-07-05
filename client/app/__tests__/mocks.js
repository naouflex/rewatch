import { TextEncoder, TextDecoder } from "util";
import MockDate from "mockdate";

// react-dom/server (React 18) expects these globals, but jsdom doesn't provide them
if (typeof global.TextEncoder === "undefined") {
  global.TextEncoder = TextEncoder;
  global.TextDecoder = TextDecoder;
}

const date = new Date("2000-01-01T02:00:00.000");

MockDate.set(date);
