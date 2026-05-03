import {
  interpolateWarm,
  interpolateCool,
  interpolateBlues,
  interpolateGreens,
  interpolateGreys,
  interpolateOranges,
  interpolatePurples,
  interpolateReds,
  interpolateViridis,
  interpolateInferno,
  interpolateMagma,
  interpolatePlasma,
  interpolateCividis,
  interpolateTurbo,
} from "d3-scale-chromatic";

const interpolatorCache: { [key: string]: (t: number) => string } = {};

export function getColorInterpolator(interpolatorName: string) {
  if (interpolatorCache[interpolatorName]) {
    return interpolatorCache[interpolatorName];
  }

  let interpolator: (t: number) => string;

  // Squash the input range into [0.1, 1.0] so the lightest end of every scheme
  // stays readable on light backgrounds.
  switch (interpolatorName) {
    case "interpolateWarm":
      interpolator = (t: number) => interpolateWarm(0.1 + 0.9 * t);
      break;
    case "interpolateCool":
      interpolator = (t: number) => interpolateCool(0.1 + 0.9 * t);
      break;
    case "interpolateBlues":
      interpolator = (t: number) => interpolateBlues(0.1 + 0.9 * t);
      break;
    case "interpolateGreens":
      interpolator = (t: number) => interpolateGreens(0.1 + 0.9 * t);
      break;
    case "interpolateGreys":
      interpolator = (t: number) => interpolateGreys(0.1 + 0.9 * t);
      break;
    case "interpolateOranges":
      interpolator = (t: number) => interpolateOranges(0.1 + 0.9 * t);
      break;
    case "interpolatePurples":
      interpolator = (t: number) => interpolatePurples(0.1 + 0.9 * t);
      break;
    case "interpolateReds":
      interpolator = (t: number) => interpolateReds(0.1 + 0.9 * t);
      break;
    case "interpolateViridis":
      interpolator = (t: number) => interpolateViridis(0.1 + 0.9 * t);
      break;
    case "interpolateInferno":
      interpolator = (t: number) => interpolateInferno(0.1 + 0.9 * t);
      break;
    case "interpolateMagma":
      interpolator = (t: number) => interpolateMagma(0.1 + 0.9 * t);
      break;
    case "interpolatePlasma":
      interpolator = (t: number) => interpolatePlasma(0.1 + 0.9 * t);
      break;
    case "interpolateCividis":
      interpolator = (t: number) => interpolateCividis(0.1 + 0.9 * t);
      break;
    case "interpolateTurbo":
      interpolator = (t: number) => interpolateTurbo(0.1 + 0.9 * t);
      break;
    default:
      interpolator = (t: number) => interpolateWarm(0.1 + 0.9 * t);
  }

  interpolatorCache[interpolatorName] = interpolator;
  return interpolator;
}

export function formatNumber(value: number | undefined | null): string {
  if (value === undefined || value === null || isNaN(value)) {
    return "N/A";
  }
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 4,
  }).format(value);
}

// Convert a relative position (0..1) into absolute pixels for a given viewport.
// We persist positions as ratios so they survive viewport resizes.
export function relativeToAbsolutePosition(
  position: { x: number; y: number },
  width: number,
  height: number
): { x: number; y: number } {
  return {
    x: position.x * width,
    y: position.y * height,
  };
}
