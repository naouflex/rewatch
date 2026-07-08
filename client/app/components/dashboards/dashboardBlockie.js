const CHART_PALETTES = [
  ["#ff7230", "#2563eb", "#0891b2"],
  ["#7c3aed", "#059669", "#ff7230"],
  ["#d97706", "#dc2626", "#0ea5b7"],
  ["#2563eb", "#ff7230", "#7c3aed"],
];

function hashSeed(seed) {
  const str = String(seed);
  let hash = 2166136261;
  for (let i = 0; i < str.length; i += 1) {
    hash ^= str.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0 || 1;
}

function createRng(seed) {
  let state = hashSeed(seed);
  return () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 0xffffffff;
  };
}

export function readBlockieThemeColors() {
  if (typeof document === "undefined") {
    return {
      bg: "#f5f2ec",
      surface: "#ffffff",
      grid: "#ece8e1",
      brand: "#ff7230",
      muted: "#7a7068",
    };
  }

  const styles = getComputedStyle(document.documentElement);
  const read = name => styles.getPropertyValue(name).trim();

  return {
    bg: read("--rd-color-bg-subtle") || "#f5f2ec",
    surface: read("--rd-color-surface") || "#ffffff",
    grid: read("--rd-color-divider") || "#ece8e1",
    brand: read("--rd-color-brand") || "#ff7230",
    muted: read("--rd-color-text-muted") || "#7a7068",
  };
}

export function buildDashboardBlockie(dashboardId, seedExtra = "") {
  const rng = createRng(`dashboard-blockie:${dashboardId}:${seedExtra}`);
  const palette = CHART_PALETTES[Math.floor(rng() * CHART_PALETTES.length)];
  const accent = palette[Math.floor(rng() * palette.length)];
  const secondary = palette[Math.floor(rng() * palette.length)];
  const variant = Math.floor(rng() * 3);
  const barCount = 5 + Math.floor(rng() * 4);
  const bars = Array.from({ length: barCount }, () => 0.2 + rng() * 0.75);
  const linePoints = Array.from({ length: 8 }, (_, index) => ({
    x: index / 7,
    y: 0.15 + rng() * 0.7,
  }));

  return {
    variant,
    bars,
    linePoints,
    accent,
    secondary,
    showDots: rng() > 0.45,
  };
}

export function blockieViewBox(size) {
  return size === "home" ? { width: 72, height: 42 } : { width: 88, height: 51 };
}
