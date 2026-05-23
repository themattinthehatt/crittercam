# Component Library — Storybook Development Brief

## Purpose of this document

This document guides the development of the crittercam UI component library using
Storybook. It is intended to be used with Claude Code in a slow, pedagogical way:
one component at a time, with explanations at each step. The owner has no prior
frontend experience, so every step should teach the concept behind what is being
built, not just produce the code.

---

## What Storybook is and why we are using it

Storybook is a development environment for building UI components in isolation. It
runs as a separate local server (default port 6006) that has nothing to do with the
crittercam dashboard itself. In Storybook you can view, interact with, and evaluate
each component independently — without a running FastAPI server, without a populated
database, and without navigating through the actual app.

The workflow this enables:

1. Build and review a component in Storybook until it looks and behaves correctly
   across all its important states
2. Only then import it into the real app pages

This matters for AI-assisted development because it constrains Claude Code: once the
component library exists, Claude Code assembles pages by composing known, reviewed
components rather than inventing new UI from scratch on every request. The result is
cleaner code, consistent visual style, and outputs that are easier to evaluate.

**Storybook is a development-only tool.** Components are plain React files (`.jsx`).
Storybook never touches the production build. The only Storybook-specific files are
`*.stories.jsx` files that sit alongside each component — these import the component
and render it with specific props. If Storybook were removed tomorrow, every component
would continue to work unchanged in the app.

---

## Setup

Before building any components, Storybook must be installed inside the React app:

```bash
cd crittercam/web/ui
npx storybook@latest init
```

This scaffolds Storybook alongside the existing Vite + React setup. It adds:
- `crittercam/web/ui/.storybook/` — Storybook configuration
- `crittercam/web/ui/src/stories/` — example stories (these can be deleted)
- New entries in `package.json` for storybook dependencies and the `storybook` script

To run Storybook:
```bash
cd crittercam/web/ui
npm run storybook
```

Then open `http://localhost:6006` in the browser. The crittercam dashboard (Vite dev
server) and Storybook can run simultaneously on their separate ports.

---

## Component inventory

The full component library for Phase 4. Build these in order — each group depends on
the previous one being stable.

### Group 1 — Primitives

These are the smallest building blocks. They carry no crittercam-specific knowledge.

| Component | Description |
|---|---|
| `Badge` | A small colored pill. Used for confidence scores (green/amber/red by threshold) and species labels. Props: `label`, `variant` (confidence \| species \| blank) |
| `StatCard` | A number + label pair for summary statistics. Props: `value`, `label` |
| `Button` | A standard button. Props: `label`, `onClick`, `variant` (primary \| ghost), `disabled` |

### Group 2 — Domain components

These know about crittercam data structures.

| Component | Description |
|---|---|
| `DetectionCard` | A thumbnail card for a single detection. Shows the crop image, species label, confidence badge, and captured_at timestamp. Props: `cropUrl`, `label`, `confidence`, `capturedAt`, `onClick` |
| `FilterSidebar` | Species dropdown + date range inputs. Props: `species` (list), `selectedSpecies`, `dateFrom`, `dateTo`, `onChange` |
| `DetailPanel` | Side-by-side crop + full image with SVG bounding box overlay, plus a metadata table (species, confidence, model version, temperature, captured_at). Props: `detection` object |
| `ChartPanel` | A titled container that wraps a Recharts chart. Props: `title`, `children` |

### Group 3 — Layout

| Component | Description |
|---|---|
| `TabShell` | The three-tab top-level layout (Home, Browse, Analytics). Props: `activeTab`, `onTabChange`, `children` |

---

## How to write a story file

Each component gets a `ComponentName.stories.jsx` file in the same directory as the
component. A story is just a named export that renders the component with a specific
set of props, representing one meaningful state.

**Anatomy of a story file** (Claude Code should explain each part when first
introducing this pattern):

```jsx
import DetectionCard from './DetectionCard'

// The default export tells Storybook the component's name and where it lives
// in the left-panel navigation tree
export default {
  title: 'Domain/DetectionCard',
  component: DetectionCard,
}

// Each named export is one story — one specific state of the component.
// Storybook renders it with these props and lists it under the component name.

export const Default = {
  args: {
    cropUrl: 'https://placehold.co/300x200',
    label: 'white-tailed deer',
    confidence: 0.91,
    capturedAt: '2026-03-14T02:17:00',
  },
}

export const LowConfidence = {
  args: {
    cropUrl: 'https://placehold.co/300x200',
    label: 'anatidae (family)',
    confidence: 0.34,
    capturedAt: '2026-03-14T02:17:00',
  },
}

export const Blank = {
  args: {
    cropUrl: null,
    label: 'blank',
    confidence: 0.98,
    capturedAt: '2026-03-14T02:17:00',
  },
}
```

The `args` object maps directly to the component's props. Storybook automatically
generates Controls in the bottom panel for each arg, so the owner can adjust values
interactively without editing code.

Use `https://placehold.co/WxH` for placeholder images in stories — no real database
or server needed.

---

## Pedagogy guidelines for Claude Code

The owner is a data analyst and ML engineer with no prior frontend experience. When
building each component:

1. **Explain before generating.** Before writing any code for a new component or
   concept, explain in plain language what it is and why it is written the way it is.
   Draw analogies to Python or data concepts the owner will recognise where possible.

2. **One concept at a time.** Introduce one new HTML/CSS/React/JS concept per
   component. For example: `Badge` introduces JSX and props. `DetectionCard` introduces
   CSS layout (flexbox or grid). `FilterSidebar` introduces controlled inputs and
   callbacks. Do not introduce multiple new concepts simultaneously.

3. **Read before writing.** Before generating any component code, read the existing
   components in `crittercam/web/ui/src/components/` so the new component is
   consistent in style and conventions with what already exists.

4. **Stories first, implementation second.** When starting a new component, begin by
   writing the story file together with the owner — this forces clarity about what
   props the component needs and what states it must handle before a line of
   implementation is written.

5. **Explain the Controls panel.** After each component is built, point the owner to
   the Controls panel in Storybook and explain how to use it to probe edge cases (long
   species names, missing images, confidence at exactly 0.5, etc.).

6. **No new primitives in page assembly.** Once the component library is complete,
   page-level code (`App.jsx`, tab components) should only import from the established
   library. If a page seems to need a new visual element, stop and build it as a named
   component with its own story first.

---

## Suggested first session

The first Storybook session should cover exactly one component: `Badge`.

Reasons: it is the simplest possible component (a single styled element, no images,
no API calls, no layout complexity), it introduces the core concepts of props and JSX
in a completely contained way, and the confidence-threshold color logic (green above
0.7, amber between 0.4 and 0.7, red below 0.4) is a concrete, testable behavior that
the Controls panel makes immediately satisfying to verify.

The session should proceed as:
1. Explain what a React component is (a function that takes props and returns JSX),
   using the analogy of a Python function that takes arguments and returns a string
2. Install Storybook if not already done
3. Write `Badge.stories.jsx` first — establish the three stories (`HighConfidence`,
   `LowConfidence`, `VeryLow`) and what props are needed
4. Write `Badge.jsx` to satisfy those stories
5. Run Storybook, verify all three stories, use the Controls panel to find edge cases
6. Explain what just happened: a component was defined by its states before it was
   implemented — this is the right order of operations

---

## File locations

```
crittercam/web/ui/
    .storybook/              # Storybook configuration (do not edit by hand)
    src/
        components/
            Badge.jsx
            Badge.stories.jsx
            StatCard.jsx
            StatCard.stories.jsx
            Button.jsx
            Button.stories.jsx
            DetectionCard.jsx
            DetectionCard.stories.jsx
            FilterSidebar.jsx
            FilterSidebar.stories.jsx
            DetailPanel.jsx
            DetailPanel.stories.jsx
            ChartPanel.jsx
            ChartPanel.stories.jsx
            TabShell.jsx
            TabShell.stories.jsx
```

Each component and its story file live together. No separate `stories/` directory.

---

## Definition of done for each component

A component is complete and ready to be used in page assembly when:

- [ ] All planned stories render correctly in Storybook
- [ ] The Controls panel confirms that edge-case prop values are handled gracefully
      (long labels, null values, boundary confidence scores)
- [ ] The component is visually consistent with the others already in the library
- [ ] The owner can describe in plain language what the component does and what
      props it accepts
