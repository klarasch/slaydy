// A pretend brand, to try the extension points by hand. Not shipped with the skill.
// Serve the repo root (python3 -m http.server) and open /site/brand-demo/deck.html.
const { layouts, transitions, options } = window.slaydy;

// a layout of the brand's own, in the Add-slide picker; Gallery retired
layouts.add({
  key: "claim", label: "Claim",
  wireframe: '<i class="a" style="left:10%;top:30%;width:4%;height:40%"></i><i style="left:18%;top:36%;width:60%;height:12%"></i><i style="left:18%;top:54%;width:40%;height:6%"></i>',
  html: '<section class="slide slide--claim" data-title="Claim"><div class="panel"><p class="eyebrow">Our claim</p><h2 class="h1">One bold sentence.</h2><p class="lead">The proof, in one line.</p></div></section>',
});
layouts.remove("gallery");

// a transition of the brand's own: Options → Transition → swoosh
transitions.add("swoosh");

// an option on an element inside the slide: the claim panel's tone
options.declare({ name: "data-tone", on: ".panel", group: "Slide", label: "Panel tone", values: ["calm", "loud"],
  hint: "Claim slides: a quiet panel or an accent one." });

// brand art in the split image slot, instead of the "+ image" placeholder
options.declare({ name: "data-art", on: ".split__media", group: "Slide", label: "Picture", values: ["mesh", "topo", "none"],
  hint: "Brand art in the empty image slot. Uploading an image replaces it." });
