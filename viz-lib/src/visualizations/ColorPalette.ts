import { values } from "lodash";

// Modern, harmonious qualitative palette (inspired by the Open Color system).
// Tuned to read cleanly on warm light surfaces and to coordinate with the
// app's orange brand without the harsh neon feel of the legacy defaults.
export const BaseColors = {
  Indigo: "#4C6EF5",
  Orange: "#FF7230",
  Teal: "#12B886",
  Pink: "#F06595",
  Violet: "#7950F2",
  Amber: "#F59F00",
  Cyan: "#15AABF",
  Lime: "#82C91E",
  "Light Blue": "#748FFC",
  Red: "#FA5252",
  Grape: "#CC5DE8",
  Mint: "#20C997",
  "Dark Blue": "#1864AB",
  Gray: "#868E96",
};

// Additional colors for the user to choose from
export const AdditionalColors = {
  "Deep Orange": "#E8590C",
  Forest: "#2F9E44",
  Sky: "#4DABF7",
  Plum: "#9C36B5",
  Rose: "#E64980",
  Slate: "#495057",
  Black: "#212529",
};

const Viridis = {
  1: '#440154',
  2: '#48186a',
  3: '#472d7b',
  4: '#424086',
  5: '#3b528b',
  6: '#33638d',
  7: '#2c728e',
  8: '#26828e',
  9: '#21918c',
  10: '#1fa088',
  11: '#28ae80',
  12: '#3fbc73',
  13: '#5ec962',
  14: '#84d44b',
  15: '#addc30',
  16: '#d8e219',
  17: '#fde725',
};

const Tableau = {
  1 : "#4e79a7",
  2 : "#f28e2c",
  3 : "#e15759",
  4 : "#76b7b2",
  5 : "#59a14f",
  6 : "#edc949",
  7 : "#af7aa1",
  8 : "#ff9da7",
  9 : "#9c755f",
  10 : "#bab0ab",
}

const D3Category10 = {
  1 : "#1f77b4",
  2 : "#ff7f0e",
  3 : "#2ca02c",
  4 : "#d62728",
  5 : "#9467bd",
  6 : "#8c564b",
  7 : "#e377c2",
  8 : "#7f7f7f",
  9 : "#bcbd22",
  10 : "#17becf",
}

let ColorPalette = {
  ...BaseColors,
  ...AdditionalColors,
};

export const ColorPaletteArray = values(ColorPalette);

export default ColorPalette;

export const DEFAULT_COLOR_SCHEME = "Rewatch";

export const AllColorPalettes = {
  Rewatch: ColorPalette,
  Viridis: Viridis,
  "Tableau 10": Tableau,
  "D3 Category 10": D3Category10,
};

export const AllColorPaletteArrays = {
  Rewatch: ColorPaletteArray,
  Viridis: values(Viridis),
  "Tableau 10": values(Tableau),
  "D3 Category 10": values(D3Category10),
};

export const ColorPaletteTypes = {
  Rewatch: "discrete",
  Viridis: "continuous",
  "Tableau 10": "discrete",
  "D3 Category 10": "discrete",
};

const COLOR_SCHEME_ALIASES: Record<string, string> = {
  Redash: "Rewatch",
};

export function resolveColorScheme(name: string) {
  return COLOR_SCHEME_ALIASES[name] || name;
}
