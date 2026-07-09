const SELECTOR_PHRASES = {
  first: "the first value of",
  min: "the minimum value of",
  max: "the maximum value of",
};

const OP_PHRASES = {
  ">": "is greater than",
  ">=": "is greater than or equal to",
  "<": "is less than",
  "<=": "is less than or equal to",
  "==": "equals",
  "!=": "does not equal",
};

export function getSelectorPhrase(selector) {
  return SELECTOR_PHRASES[selector] || selector;
}

export function getOperatorPhrase(op) {
  return OP_PHRASES[op] || op;
}

export function buildCriteriaSentence(alertOptions) {
  const { selector, column, op, value } = alertOptions;
  return `Trigger when ${getSelectorPhrase(selector)} ${column} ${getOperatorPhrase(op)} ${value}`;
}
