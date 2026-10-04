# slaydy

This folder is the slaydy skill's source. `SKILL.md` is its instruction set, and it applies here
even though the skill isn't installed from this folder.

- Asked to set up a brand ("set up slaydy for Acme from acme.com", a brand PDF, a logo):
  follow `SKILL.md` §8. The brand goes in a new fork beside this checkout, never in here.
- Asked to take a slaydy update inside a fork: follow `SKILL.md` §9.
- Asked for a deck: follow `SKILL.md` from §1.

Changing the runtime itself rather than using it: `HANDOFF.md`.

Changing the runtime, a contract doc or the skeleton: add an entry to `CHANGELOG.md` in the same
commit, with a **Forks:** line saying what a fork must do or may delete. `take-update.sh` shows
forks the entries added since their stamp.
