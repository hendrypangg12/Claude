# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Single-file browser game: a Nokia 3310-style Snake clone. Everything (HTML, CSS, game logic) lives in `index.html`. There is no build system, no package manager, no test runner, and no external dependencies.

History note: the repo previously hosted Flappy Bird, then Tetris, then was replaced by Snake (see `git log`). When asked to swap the game, replace `index.html` wholesale rather than layering games side-by-side.

## Running / iterating

- Open `index.html` directly in a browser, or serve the directory (`python3 -m http.server`) and visit it. There is no dev server, no hot reload, no transpile step.
- After edits, just reload the browser. There are no tests or linters configured — visual/manual play-testing is the only verification.
- High score persists in `localStorage` under the key `nokia-snake-hi`; clear it from devtools if you need a fresh run.

## Architecture (inside `index.html`)

The game logic is a single IIFE at the bottom of the file. Key pieces to understand before changing behavior:

- **Grid model.** The canvas is `240×200` with `CELL = 10`, giving a fixed `24×20` grid. Coordinates throughout the code are grid cells, not pixels — only the draw helpers multiply by `CELL`. Changing canvas size or `CELL` requires they stay divisible.
- **`state` object.** Single source of truth for snake body, current/pending direction, food, score, hi-score, status, and timing accumulator. The status state machine is `ready → playing → paused ⇄ playing → over` (with `over → ready` via `reset()`).
- **Direction buffering.** Input writes to `state.pendingDir`; `tick()` commits it to `state.dir`. `setDir()` rejects 180° reversals. This is what prevents a fast double-tap from making the snake collide with itself — preserve this pattern when adding input sources.
- **Fixed-timestep loop.** `loop(t)` uses `requestAnimationFrame` for rendering but advances game logic in discrete `state.tickMs` steps via an accumulator. Difficulty scaling lives in `tick()`: each food eaten subtracts 3ms, floored at 55ms. Don't move speed logic into the render path.
- **Self-collision rule.** When the next head cell equals the food, the tail does NOT vacate this turn, so the collision check uses the full body; otherwise it uses `snake.slice(1)`. This subtlety matters if you refactor movement.
- **Rendering.** `drawBackground` paints the LCD-green palette plus a checkerboard dither and inner border; `drawSnakeSegment` draws the nested-square retro look; overlay screens (`ready`/`paused`/`over`) go through `drawCenteredText`. The Game Boy-ish palette constants (`BG_LIGHT`, `BG_DIM`, `FG_DARK`, `FG_MID`) are the canonical colors — reuse them rather than introducing new hex values.
- **Input surfaces.** Three parallel input paths feed `setDir`/`togglePause`/`reset`: keyboard (`keydown`), on-screen keypad (`.key` click handlers), and canvas touch swipes. Any new control should route through these same functions, not mutate `state` directly.

## Conventions

- Keep the project a single self-contained `index.html`. Don't introduce a build step, framework, or split files unless explicitly asked.
- Match the existing Nokia/Game Boy aesthetic (LCD green palette, pixelated rendering via `image-rendering: pixelated`, monospace HUD font) when adding UI.
- `git log` shows feature work lands via PRs from `claude/<feature>-<id>` branches into `main`. Develop on the branch you've been given and push there.
