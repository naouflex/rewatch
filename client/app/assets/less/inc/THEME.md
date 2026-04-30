# Theming Redash

The Redash UI is themed through **CSS custom properties** (a.k.a. CSS
variables) defined in `inc/tokens.less`. Every color, radius, shadow,
spacing step, motion curve, and font scale used by buttons, tables,
cards, modals, sidebars, charts, etc. is read from these tokens at
runtime — so a single value change re-themes the whole product.

---

## File map

| File                      | Purpose                                                                 |
| ------------------------- | ----------------------------------------------------------------------- |
| `inc/tokens.less`         | **Source of truth** for all design tokens (light + dark variants).      |
| `inc/dark-theme.less`     | Targeted overrides for Bootstrap / Ant Design classes that hardcode dark text on white surfaces. Kept separate so it only loads when `[data-theme="dark"]` is active on `<html>`. |
| `inc/ant-variables.less`  | Mirror of a few Ant Design LESS variables (e.g. `@primary-color`, `@input-color-placeholder`) that must be set at compile time. |
| `inc/variables.less`      | Legacy Bootstrap LESS variables. Slowly being phased out; new code should reference `--rd-*` tokens instead. |
| `services/theme.ts`       | Runtime API: `getTheme()`, `setTheme('light' | 'dark' | 'system')`, `toggleTheme()`. |
| `components/ThemeToggle.jsx` | Antd Switch-based toggle used in the desktop & mobile navbars.          |

---

## Customizing the brand color

The current brand color is **`#FF7230`** (warm orange).

To rebrand the entire UI (buttons, links, focus rings, active sidebar
tab, soft tints, sidebar highlight, focus shadow), update **two
locations** with the same color:

1. `inc/tokens.less` — `--rd-brand-rgb` and `--rd-color-brand`
   ```less
   --rd-brand-rgb: 255, 114, 48;            /* #FF7230 in R, G, B */
   --rd-color-brand: rgb(var(--rd-brand-rgb));
   --rd-color-brand-hover:  #f05a12;
   --rd-color-brand-active: #d3490a;
   ```
2. `inc/ant-variables.less` — `@primary-color` and `@lightblue`
   ```less
   @lightblue: #ff7230;
   @primary-color: #ff7230;
   ```

Soft tints (`--rd-color-brand-soft`, `--rd-color-brand-soft-hover`),
the focus ring shadow (`--rd-shadow-focus`), and the dark-mode sidebar
highlight (`--rd-sidebar-active-bg`) are derived from `--rd-brand-rgb`
and update automatically.

After editing, run `pnpm start` (the dev server auto-recompiles LESS).

### Recommended companion palette for `#FF7230`

The orange brand is high-energy and warm. To keep the UI calm and
readable, the rest of the palette is tuned around it:

| Role            | Token                       | Value      | Why                                                                       |
| --------------- | --------------------------- | ---------- | ------------------------------------------------------------------------- |
| Brand hover     | `--rd-color-brand-hover`    | `#f05a12`  | ~8% darker / +saturation — visible state change without going muddy.      |
| Brand active    | `--rd-color-brand-active`   | `#d3490a`  | ~16% darker — pressed/active feedback.                                    |
| Secondary accent| `--rd-color-accent`         | `#0ea5b7`  | Teal — direct visual complement to orange; keeps the UI from feeling monochromatic when used for badges, info chips, charts. |
| Accent (soft)   | `--rd-color-accent-soft`    | `#cff7fa`  | Pairs with the teal accent for subtle backgrounds.                        |
| Info            | `--rd-color-info`           | `#0ea5b7`  | Routed to the same teal so "info" reads distinctly from "warning".        |
| Warning         | `--rd-color-warning`        | `#eab308`  | Yellow shifted away from orange so warning ≠ brand.                       |
| Success         | `--rd-color-success`        | `#16a34a`  | Standard green; stays unchanged — needs to be unambiguously "go".         |
| Danger          | `--rd-color-danger`         | `#dc2626`  | Red kept; reads clearly next to orange because of higher saturation.      |
| Surfaces (light)| `--rd-color-bg` / `-surface-alt` | `#faf8f5` / `#fbfaf7` | Off-white with a faint warm undertone so cards don't look icy next to the orange. |
| Borders (light) | `--rd-color-border`         | `#ece8e1`  | Warm-tinted neutral border — same family as the surfaces.                 |
| Surfaces (dark) | `--rd-color-bg` / `-surface` (dark) | `#100d0a` / `#1a1612` | Very dark warm browns — orange pops against these without screaming. |
| Sidebar active (dark) | `--rd-sidebar-active-text` (dark) | `#ffb089` | Lighter tint of the brand orange — brand-aware highlight that still reads on dark surfaces. |

#### Tips when picking a different brand color
- **Hover/active** = ~8% / ~16% darker than the brand (use HSL
  lightness, not channel math, to keep saturation).
- **Warm brands** (red/orange/yellow) → keep `warning` away from the
  brand hue. Pick a teal/cyan/blue accent.
- **Cool brands** (blue/teal) → keep `info` away from the brand hue.
  Pick a coral/orange accent.
- Run a contrast check against `--rd-color-text-inverse` (white) for
  buttons; if the brand is too light, use a darker hover for the
  primary button text background.

---

## Customizing other token groups

| You want to change…           | Edit in `inc/tokens.less`                                            |
| ----------------------------- | --------------------------------------------------------------------- |
| Page / surface colors         | `--rd-color-bg`, `--rd-color-surface`, `--rd-color-surface-alt`       |
| Body / muted text             | `--rd-color-text`, `--rd-color-text-secondary`, `--rd-color-text-muted` |
| Status (success/warn/error)   | `--rd-color-success`, `--rd-color-warning`, `--rd-color-danger`       |
| Border / divider lines        | `--rd-color-border`, `--rd-color-border-strong`, `--rd-color-divider` |
| Sidebar appearance            | `--rd-sidebar-bg`, `--rd-sidebar-text`, `--rd-sidebar-active-*`       |
| Corner radius scale           | `--rd-radius-xs`..`--rd-radius-xl`, `--rd-radius-pill`                |
| Spacing scale                 | `--rd-space-1`..`--rd-space-10` (4-pt grid)                           |
| Elevation (shadows)           | `--rd-shadow-1`..`--rd-shadow-4`                                      |
| Animation timing              | `--rd-duration-fast/base/slow`, `--rd-ease/in/out`                    |
| Font family / sizes / weights | `--rd-font*`, `--rd-font-size-*`, `--rd-font-weight-*`                |

The `[data-theme="dark"]` block at the bottom of `tokens.less`
overrides only the neutrals (background, surface, text, border) and
shadow scales for dark mode — the brand palette is shared.

---

## Using tokens in your code

### From LESS / CSS files

```less
.my-card {
  background: var(--rd-color-surface);
  color: var(--rd-color-text);
  border: 1px solid var(--rd-color-border);
  border-radius: var(--rd-radius-md);
  box-shadow: var(--rd-shadow-2);
}

.my-button {
  background: var(--rd-color-brand);
  color: var(--rd-color-text-inverse);

  &:focus-visible {
    box-shadow: var(--rd-shadow-focus);
  }
}
```

### From JSX (inline style)

```jsx
<div style={{ background: "var(--rd-color-surface)", color: "var(--rd-color-text)" }} />
```

### From plotly / d3 / canvas

The token values can also be resolved at runtime when a chart library
needs a plain color string:

```ts
const surface = getComputedStyle(document.documentElement)
  .getPropertyValue("--rd-color-surface")
  .trim();
```

`viz-lib/src/visualizations/chart/plotly/getThemePalette.ts` already
implements this pattern for Plotly charts.

---

## Adding a new component

1. **Reach for an existing token first.** A new card/modal almost
   never needs a new color — `--rd-color-surface` + `--rd-color-text`
   + `--rd-color-border` covers 90% of UI surfaces.
2. **Avoid hardcoded hex values.** If you find yourself typing
   `#fafafa`, ask whether `--rd-color-surface-alt` works.
3. **Avoid `rgba(0,0,0,…)` for text.** Use the text token tier
   (`--rd-color-text`, `-secondary`, `-muted`, `-disabled`) so it
   inverts cleanly in dark mode.
4. **Status feedback** uses the dedicated tokens: success/warning/
   danger/info each have a "soft" tint variant for backgrounds.
5. **Need a new token?** Add it to `inc/tokens.less` (under both the
   `:root` and `[data-theme="dark"]` blocks if it differs across
   themes) and document its intent in this file.
