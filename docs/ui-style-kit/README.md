# UI Style Kit

This directory packages the core styling primitives taken from the LocalAggregator dashboard so they can be copied into new projects quickly.

## Files

- `variables.css` &ndash; color palette, elevation shadow, and other shared design tokens.
- `components.css` &ndash; base layout, header, navigation, card, button, form, badge, dialog, and toast styles. Each rule assumes the variables file is imported first.

## Using in a New Project

1. Copy the entire `ui-style-kit` folder into your project (for example, `src/styles/ui-style-kit/`).
2. Import the variables before any component-specific stylesheet: `@import './ui-style-kit/variables.css';`.
3. Layer in the component styles with `@import './ui-style-kit/components.css';`.
4. Extend or override classes locally as needed &ndash; the kit is intentionally lightweight and uses semantic class names (`.app-header`, `.nav-button`, `.card`, `.btn`, etc.).
5. If you need additional components (metrics, hero, tables), start from `frontend/src/styles.css` for reference.

## Notes

- The gradient header and gradient text title are included so the "Market Aggregator" brand treatment can be reused.
- Both files rely on modern CSS features (`background-clip: text`, `backdrop-filter`). Provide fallbacks if targeting older browsers.
- The base font stack expects the Inter and JetBrains Mono fonts to be available; include the same Google Fonts import for consistency.
