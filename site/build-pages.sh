#!/usr/bin/env bash
# Assemble the landing page for GitHub Pages: site/ flattened to the web root, with the
# runtime, the stock theme and CHANGELOG.md it reads from the repo copied in beside it.
#
#     site/build-pages.sh [out-dir]      # default: dist/pages
#
# In the repo the page reaches up (../runtime.css); on Pages everything sits in one folder,
# so the three kinds of ../ reference are rewritten here and nowhere else.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-dist/pages}"

rm -rf "$OUT"
mkdir -p "$OUT/themes"
cp site/index.html site/demo.html site/changelog.html "$OUT/"
cp site/themes/slaydy.css "$OUT/themes/"
cp themes/midnight.css "$OUT/themes/midnight.css"     # the stock file itself, not the @import shim
cp runtime.css runtime.js CHANGELOG.md "$OUT/"
[ -d site/images ] && cp -R site/images "$OUT/images"
touch "$OUT/.nojekyll"

sed -i.bak -e 's#"\.\./runtime\.css"#"runtime.css"#' -e 's#"\.\./runtime\.js"#"runtime.js"#' "$OUT/demo.html"
sed -i.bak -e 's#"\.\./CHANGELOG\.md"#"CHANGELOG.md"#' "$OUT/changelog.html"
rm -f "$OUT"/*.bak

# quoted or url() references only; a ../ in a comment is harmless
if grep -nE "[\"'(]\.\./" "$OUT"/*.html "$OUT"/themes/*.css; then
  echo "build-pages: a ../ reference survived; add a rewrite for it above" >&2
  exit 1
fi
echo "built $OUT"
