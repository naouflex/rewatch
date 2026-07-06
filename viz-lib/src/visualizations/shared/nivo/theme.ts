import getThemePalette from "../echarts/getThemePalette";

export default function getNivoTheme() {
  const palette = getThemePalette();
  return {
    textColor: palette.text,
    fontSize: 12,
    fontFamily: palette.fontFamily,
    tooltip: {
      container: {
        background: palette.surface,
        color: palette.text,
        fontSize: 12,
        fontFamily: palette.fontFamily,
        borderRadius: 6,
        boxShadow: "0 2px 8px rgba(0,0,0,0.12)",
        border: `1px solid ${palette.border}`,
      },
    },
    labels: {
      text: {
        fill: palette.text,
        fontFamily: palette.fontFamily,
      },
    },
  };
}
