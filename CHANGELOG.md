# Changelog

What changed upstream, newest first. `take-update.sh` prints the entries added since a fork's
last stamp, so write for someone who has a fork and has not read the commits.

Every change to the runtime, the docs a release owns, or the skeleton adds an entry in the same
commit. Each entry says what changed and, under **Forks**, what a fork has to do or may now
delete. "Nothing" is a valid answer and should be written out.

Tags on an entry: **runtime** (runtime.*), **docs** (the contract docs), **skeleton**
(skeleton.html — port by hand), **attribute** (new or changed `data-*` a deck can carry), and
one kind: **feature** or **fix**.

The **Forks:** line opens with one word, which the site's changelog page (`site/changelog.html`)
turns into a badge: **nothing** (no fork has anything to do), **check** (only a fork that touches
the named thing has something to do or to delete), **port** (every fork has to act).

---

## 2026-10-05

### A hook for standalone.py, and minified files judged by content
**runtime, docs, feature, fix**
- `standalone.py` has an extension point, the twin of the browser's `slaydy:serialize`: a
  fork-owned `standalone_hook.py` beside it (or one folder down) defines `hook(folder, html)`
  and returns JavaScript, or `{"js", "css"}`, that goes into the bundle ahead of the runtime.
  `--explode` takes it back out, so a rebuild never carries it twice. `CUSTOMIZING.md`,
  "Lazy-loaded assets", has an example.
- `build.sh` and `standalone.py` no longer decide by file time whether `runtime.min.*` are
  current. Each `.min` opens with a stamp of the source it was built from. An update or a clone
  resets file times, which used to send the next build looking for esbuild and could rewrite the
  tracked `.min` files with a different esbuild.
- The esbuild download in `build.sh` gives up after 90 seconds instead of hanging on a registry
  that never answers; the existing `.min` files are kept, as on any other failure.

**Forks:** check. A fork that patched `standalone.py` to inline its own assets can move that
into `standalone_hook.py` and take upstream's file again. After this update `./build.sh` should
print "runtime.min.* are up to date"; if it minifies instead, the fork's `runtime.js` or
`runtime.css` differs from upstream's.

### standalone.py lints the deck
**docs, feature** — Building the share file now checks the deck first and prints what it finds:
the density budgets per layout, deck structure (title first, end last, no two bullets in a
row), speaker notes where the tier requires them, and markup the skill forbids (inline styles,
undeclared `<style>` and `<script>`, typed separators, missing or base64 images, a layout that
is not in the deck's stylesheets). Those are `fix` lines. `check` lines are judgment calls:
divider spacing, an agenda on a short deck, reveals and count-ups. The file is written either
way, and an error inside the lint never fails a build. `standalone.py --lint deck.html` only lints, and exits 1 on any `fix`. SKILL.md §3
and §5 tell Claude to clear the `fix` lines before handing a deck over.

**Forks:** check. A layout a fork adds is known to the lint as soon as its `.slide--<name>` rule
is in a stylesheet the deck links, and it gets no budget checks. An install with its own
`skeleton.html` is not held to the stock shell: its wiring, and any inline `<style>` or
`<script>` the skeleton carries, are accepted as they are. A brand whose voice file allows
something the lint flags (a separator character, say) should say in `themes/<name>.md` that the
line is expected.

## 2026-10-04

### SKILL.md is under 400 lines
**docs, fix**
- The body was 552 lines, over the 500-line cap some skill registries enforce, and a fork
  could only add to it. It is now 392. Reference material moved, text unchanged, into the docs
  SKILL.md already pointed at: the brand setup procedure is now `BRANDING.md` §8, the update
  procedure `UPDATING.md` §6, and the custom-content contract sits in `LAYOUTS.md` "Custom
  content". Section numbers in SKILL.md are unchanged; §7, §8 and §9 are now short pointers.
  No new files.
- Tightened after test runs with smaller models: section dividers open groups of 4–7 content
  slides and never fewer, a new hard rule against invented facts, and a word count after the
  deck is written. The setup runbook now says to compute the `--accent-fg` contrast (4.5:1,
  the brand's dark on a mid-tone accent), how to derive tokens the brand did not supply, gives
  `SKILL.fork.md` as a template, and has `skeleton.html` copied from `LAYOUTS.md` character
  for character.
- `build.sh` no longer ships `site/` (upstream's landing page) inside the skill, where the
  "copy everything" rule carried it into every generated deck folder.

**Forks:** check. Nothing to port. If `SKILL.fork.md` or a brand's `themes/<name>.md` cites the
setup or update steps by their old place in SKILL.md, point it at the new sections. A fork with
its own top-level `site/` folder that must ship should rename it.

### Saving is Download copy, everywhere
**runtime, docs, feature, fix**
- The save dialog on single-file decks and the folder picker with autosave on folder decks are
  both removed. Every deck has one way to keep edits: **Download copy** (`D`, and now `⌘S` /
  `Ctrl+S`, also while typing), a self-contained file named after the deck. It is in the edit bar
  for every deck again, with its own download icon.
- The amber "Unsaved changes — Save…" label and the first-edit toast are gone. Unsaved changes are
  a small dot on Download copy, in view mode too, and its tooltip reads "Unsaved changes —
  download a copy to keep them". Downloading clears it. Leaving edit mode with unsaved changes
  still shows a reminder, now on folder decks as well, and closing the tab still asks.
- `⌘S` used to fall through to the browser's own "Save page as".
- The Delete slide button no longer shows ⌫ as its shortcut. ⌫ deletes a selected sticker or pin,
  never a slide.
- SKILL.md's hand-off, the README and UPDATING.md §5 describe the download only.

**Forks:** check. The dot is `var(--tb-unsaved, var(--accent))`; set `--tb-unsaved` in a theme to
recolour it. Delete any override of `.tb-btn.is-warn`, `.tb-btn.is-status` or `#btn-save`, they
are gone. If `SKILL.fork.md` tells users about Save… or Save as…, reword it to Download copy
(D or ⌘S). Revising is unchanged: `standalone.py --explode` on the downloaded file.

### Changelog entries carry a kind and a fork level
**docs, feature** — Entries are now tagged `feature` or `fix`, and every Forks line opens
with `nothing`, `check` or `port`. `site/changelog.html` renders this file with those as
badges and filters.

**Forks:** nothing. A fork that keeps its own changelog in this format can adopt the same words.

### Slide PNGs include icons and canvas content
**runtime, fix**
- The PNG is drawn from an isolated copy of the slide, so icons that point at a sprite elsewhere in
  the page (`<use href="#i-…">`, list icons, separators, a brand's own sprite) came out blank. The
  symbols a slide references now travel with it.
- A `<canvas>` on the slide is exported with its current pixels instead of blank.

**Forks:** nothing. Video and iframes on a slide still export empty.

### Save falls back to a download where the save dialog is refused
**runtime, docs, fix**
- A standalone deck inside a cross-origin frame (an embedded preview) has a save dialog the browser
  refuses to open. It now offers "Download copy" from the start there, and if the dialog is refused
  anywhere else the click downloads the copy instead of failing with a toast.
- The file is built before the chosen target is opened, so a deck that fails to serialise never
  touches the file being replaced.
- SKILL.md's hand-off example and the README no longer say a single-file deck saves over itself.
  Autosave is unchanged: a deck saved into a folder autosaves, a single-file deck never does.

**Forks:** check. If `SKILL.fork.md` copied the old hand-off line ("pick this file once and it saves over
itself"), reword it: Save… is a one-shot save dialog.

### Overflow guard no longer measures slides in motion
**runtime, fix**
- Since the switch to bounding rects, a slide measured while its content was still animating in
  was read as overflowing: the `rise` offset, a `push` or `zoom` entrance, or an un-revealed step
  resting 10px low. A bottom-anchored slide (the title) could not be shrunk out of it, so it was
  flagged "Too much text" until the next visit. Late web fonts, an image load or a resize landing
  inside the entrance triggered it; a `push` deck hit it on every arrival.
- The guard now fits the arriving slide before its entrance starts, holds any measurement asked for
  mid-transition until the slide has settled, and takes a child's own translation back out.
- Every slide is re-fitted when a web font finishes loading at any point (not only the first
  `fonts.ready`), after a theme switch, and just before printing. Nothing is re-fitted while print
  styles are active, so the PDF carries exactly the fit the screen settled on.
- Printed with speaker notes, the notes under a shrunk slide are no longer shrunk with it.

**Forks:** check. Nothing to port. Drop any workaround that re-measured after a delay. A brand extension that
changes slide layout on its own (injects content, swaps a stylesheet) should dispatch `resize` on
`window` afterwards; that re-fits every slide.

### Saving standalone decks
**runtime, docs, feature, fix**
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

**Forks:** check. Nothing required, unless you reworded the "Download copy" lines in `SKILL.fork.md`.

### Sticker guides to other objects
**runtime, feature**
- Dragging a sticker now also snaps to the edges and centre of other stickers, and to the edges of the
  slide's text blocks. These guides are blue; margin and centre guides are unchanged. Alt still drags freely.

**Forks:** Nothing.

### Blank split halves
**runtime, docs, attribute, feature**
- `data-clean` now also works on `slide--split`: it hides the image half (empty slot or picture; the
  picture stays in the file) so stickers and text boxes can sit there. Options panel: "Blank canvas".

**Forks:** Nothing.

### Restart in presenter view
**runtime, feature**
- A Restart button (and Shift+R) returns the deck to slide 1 and zeroes the clock, asking first unless it
  is already at the start. `R` still only resets the timer.

**Forks:** check. `Shift+R` in presenter view is now taken.

### Images no longer break in presenter view
**runtime, fix**
- Fix: images pasted into a slot or sticker, and SVGs the runtime de-grains at boot, showed as broken
  icons in presenter view (their `blob:` URLs don't cross windows, and never on `file://`). The deck
  copy sent to the presenter now carries the original path or a data: URI instead.

**Forks:** Nothing.

### `C` copies the current slide as a PNG
**runtime, feature** — A single-key shortcut for the Copy slide as PNG item; listed in the Export menu and
the `?` sheet. Ignored with Cmd/Ctrl/Alt held and while typing.

**Forks:** check. `C` is now taken by the runtime. Rebind it if a brand extension uses it.

### Copy or download the current slide as a PNG; Export menu
**runtime, feature**
- The toolbar's "Export PDF" button is now "Export" and opens a small menu: PDF (the `P` key still
  goes straight to it), Copy slide as PNG, Download slide as PNG.
- The slide is cloned into an SVG `<foreignObject>`, drawn to a canvas at 2x (2560x1440) and encoded.
  The page's CSS (including web fonts and images, as data: URIs) travels with it; `html`/`body`/`:root`
  selectors are retargeted at wrapper divs carrying the same attributes, so themes and `data-theme`
  keep working. Steps are shown revealed, entrance animations are off, editing chrome is dropped.
- Needs to fetch fonts and images: works from a server and from a standalone file. A deck opened
  from `file://` with external assets gets a toast listing what could not be included.
- Chromium first; Safari renders foreignObject less faithfully.

**Forks:** check. Nothing to port, but a fork that overrides `#btn-print` or relabels "Export PDF" should check
it. Styles that depend on selectors other than `html`, `body`, `:root` or the slide's own ancestors
(`.deck`) will not apply inside the image.

### Slide-options dropdowns get their own chevron
**runtime, fix** — `.opt-select` showed the native chevron flush against the right border. It now draws
its own chevron with right padding so the label cannot run under it.

**Forks:** check. Drop any `select` chevron override in the slide-options panel.

### Overflow guard measures with bounding rects
**runtime, fix**
- `overflows()` used `offsetTop`/`offsetHeight`, which current Chrome reports in the element's own
  zoomed units, so the `data-fit` zoom cancelled itself out and slides that overflowed slightly were
  always shrunk to 0.8 and flagged "Too much text". It now uses `getBoundingClientRect()` divided by
  the stage scale.

**Forks:** check. Drop any workaround for the shrink step not working.

### Sticker snapping, behind-text layer, grouped Slide options — `87c77cd`
**runtime, docs, attribute, feature**
- Dragging a sticker snaps its edges and centre to the slide's `--pad` margins and centre lines;
  guide lines show (`data-gen`, never saved). Alt drags freely.
- New `data-layer="back"` on a sticker puts it behind the slide's text (z-index -1). The sticker
  bar has backward / forward / behind-text buttons; `[` and `]` step through a layer, then the text.
  Documented in LAYOUTS.md.
- Slide-options panel: collapsible groups (`group`), "N set" badge, filter box past 8 rows, Reset
  all, `hint` shown as a (?) tooltip, flags as switches, enums of more than three values as a dropdown.
- The presenter now sees sticker nudges and edits (`deckVersion`, per-session id).
- The sticker bar follows the sticker on resize; overview thumbnails follow edit mode.

**Forks:** check. Nothing to port. A brand's own `slide options` rows get the new grouping and hints
for free if they set `group` / `hint`. Check any custom CSS that sets `z-index` on `.sticker`:
back stickers use -1, front use 4.

### Label the sticker bar's delete button — `17ccb2e`
**runtime, fix** — Cosmetic. **Forks:** nothing.

### Fix sticker bar lingering in view mode, presenter missing deck changes, bar tooltips — `ed6a967`
**runtime, fix** — Bug fixes. **Forks:** check. Drop any workaround you carry for the bar staying
visible in view mode.

### Drag to reorder slides, a blank slide, sticker shadow toggle, SVG paste — `bf4e784`
**runtime, feature** — **Forks:** nothing.

### Text boxes in the deck's own type styles, and rotation for stickers — `dc8882d`
**runtime, docs, attribute, feature** — `.sticker.sticker--text` takes one of the deck's type classes and
`data-align`; stickers rotate via `rotate:` in their inline style. See LAYOUTS.md.
**Forks:** port. Make sure your theme defines the type classes text boxes will offer.

### Overview select mode: download a copy without, or with only, the picked slides — `7ce77bc`
**runtime, feature** — **Forks:** nothing.

### Loading cover, and the upstream report's fixes — `70ec072`
**runtime, feature, fix** — **Forks:** nothing.

---

Older history: `git log` in upstream. Entries start here.
