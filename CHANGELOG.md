# Changelog

What changed upstream, newest first. `take-update.sh` prints the entries added since a fork's
last stamp, so write for someone who has a fork and has not read the commits.

Every change to the runtime, the docs a release owns, or the skeleton adds an entry in the same
commit. Each entry says what changed and, under **Forks**, what a fork has to do or may now
delete. "Nothing" is a valid answer and should be written out.

Tags on an entry: **runtime** (runtime.*), **docs** (the contract docs), **skeleton**
(skeleton.html — port by hand), **attribute** (new or changed `data-*` a deck can carry).

---

## 2026-10-04

### Saving standalone decks
**runtime, docs**
- Standalone decks: Save… (Chrome/Edge) now opens the ordinary save dialog, suggests the deck's own name
  and remembers the last folder; it writes once and keeps nothing, so nothing autosaves and the opened
  file is only replaced if you pick it and confirm the OS's replace prompt. Other browsers download a
  copy. Until saved, the button reads "Unsaved changes — Save…" in amber, the first edit shows a one-time
  "Changes aren't saved yet" toast with a Save… action, and leaving edit mode repeats it. A download also
  clears the unsaved state. The edit bar now has one save button; the duplicate Download copy there is gone
  (the main bar's Download copy and `D` remain).
- Fix (folder decks too): an edit made while an autosave was writing was marked saved; it now stays dirty
  and saves again. A failed background folder write no longer triggers an unasked download. The fallback
  download is named after the deck instead of `deck-edited.html`.

**Forks:** Nothing required, unless you reworded the "Download copy" lines in `SKILL.fork.md`.

### Sticker guides to other objects
**runtime**
- Dragging a sticker now also snaps to the edges and centre of other stickers, and to the edges of the
  slide's text blocks. These guides are blue; margin and centre guides are unchanged. Alt still drags freely.

**Forks:** Nothing.

### Blank split halves
**runtime, docs, attribute**
- `data-clean` now also works on `slide--split`: it hides the image half (empty slot or picture; the
  picture stays in the file) so stickers and text boxes can sit there. Options panel: "Blank canvas".

**Forks:** Nothing.

### Restart in presenter view
**runtime**
- A Restart button (and Shift+R) returns the deck to slide 1 and zeroes the clock, asking first unless it
  is already at the start. `R` still only resets the timer.

**Forks:** `Shift+R` in presenter view is now taken.

### Images no longer break in presenter view
**runtime**
- Fix: images pasted into a slot or sticker, and SVGs the runtime de-grains at boot, showed as broken
  icons in presenter view (their `blob:` URLs don't cross windows, and never on `file://`). The deck
  copy sent to the presenter now carries the original path or a data: URI instead.

**Forks:** Nothing.

### `C` copies the current slide as a PNG
**runtime** — A single-key shortcut for the Copy slide as PNG item; listed in the Export menu and
the `?` sheet. Ignored with Cmd/Ctrl/Alt held and while typing.

**Forks:** `C` is now taken by the runtime. Rebind it if a brand extension uses it.

### Copy or download the current slide as a PNG; Export menu
**runtime**
- The toolbar's "Export PDF" button is now "Export" and opens a small menu: PDF (the `P` key still
  goes straight to it), Copy slide as PNG, Download slide as PNG.
- The slide is cloned into an SVG `<foreignObject>`, drawn to a canvas at 2x (2560x1440) and encoded.
  The page's CSS (including web fonts and images, as data: URIs) travels with it; `html`/`body`/`:root`
  selectors are retargeted at wrapper divs carrying the same attributes, so themes and `data-theme`
  keep working. Steps are shown revealed, entrance animations are off, editing chrome is dropped.
- Needs to fetch fonts and images: works from a server and from a standalone file. A deck opened
  from `file://` with external assets gets a toast listing what could not be included.
- Chromium first; Safari renders foreignObject less faithfully.

**Forks:** nothing to port. A fork that overrides `#btn-print` or relabels "Export PDF" should check
it. Styles that depend on selectors other than `html`, `body`, `:root` or the slide's own ancestors
(`.deck`) will not apply inside the image.

### Slide-options dropdowns get their own chevron
**runtime** — `.opt-select` showed the native chevron flush against the right border. It now draws
its own chevron with right padding so the label cannot run under it.

**Forks:** drop any `select` chevron override in the slide-options panel.

### Overflow guard measures with bounding rects
**runtime**
- `overflows()` used `offsetTop`/`offsetHeight`, which current Chrome reports in the element's own
  zoomed units, so the `data-fit` zoom cancelled itself out and slides that overflowed slightly were
  always shrunk to 0.8 and flagged "Too much text". It now uses `getBoundingClientRect()` divided by
  the stage scale.

**Forks:** drop any workaround for the shrink step not working.

### Sticker snapping, behind-text layer, grouped Slide options — `87c77cd`
**runtime, docs, attribute**
- Dragging a sticker snaps its edges and centre to the slide's `--pad` margins and centre lines;
  guide lines show (`data-gen`, never saved). Alt drags freely.
- New `data-layer="back"` on a sticker puts it behind the slide's text (z-index -1). The sticker
  bar has backward / forward / behind-text buttons; `[` and `]` step through a layer, then the text.
  Documented in LAYOUTS.md.
- Slide-options panel: collapsible groups (`group`), "N set" badge, filter box past 8 rows, Reset
  all, `hint` shown as a (?) tooltip, flags as switches, enums of more than three values as a dropdown.
- The presenter now sees sticker nudges and edits (`deckVersion`, per-session id).
- The sticker bar follows the sticker on resize; overview thumbnails follow edit mode.

**Forks:** nothing to port. A brand's own `slide options` rows get the new grouping and hints
for free if they set `group` / `hint`. Check any custom CSS that sets `z-index` on `.sticker`:
back stickers use -1, front use 4.

### Label the sticker bar's delete button — `17ccb2e`
**runtime** — Cosmetic. **Forks:** nothing.

### Fix sticker bar lingering in view mode, presenter missing deck changes, bar tooltips — `ed6a967`
**runtime** — Bug fixes. **Forks:** nothing. Drop any workaround you carry for the bar staying
visible in view mode.

### Drag to reorder slides, a blank slide, sticker shadow toggle, SVG paste — `bf4e784`
**runtime** — **Forks:** nothing.

### Text boxes in the deck's own type styles, and rotation for stickers — `dc8882d`
**runtime, docs, attribute** — `.sticker.sticker--text` takes one of the deck's type classes and
`data-align`; stickers rotate via `rotate:` in their inline style. See LAYOUTS.md.
**Forks:** make sure your theme defines the type classes text boxes will offer.

### Overview select mode: download a copy without, or with only, the picked slides — `7ce77bc`
**runtime** — **Forks:** nothing.

### Loading cover, and the upstream report's fixes — `70ec072`
**runtime** — **Forks:** nothing.

---

Older history: `git log` in upstream. Entries start here.
