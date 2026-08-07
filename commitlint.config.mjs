// The commit message standard, read by the `commit-msg` hook in `lefthook.yml`.
// Conventional Commits with a lower-case subject.
//
// The extension is `.mjs` and not `.js` for a mechanical reason: this repository
// has no `package.json`, so Node reads `.js` as CommonJS and `export default`
// fails. The extension is what declares the module here. Measured alongside it:
// without this file, `commitlint` fails on *every* message, valid or not, with
// `[empty-rules]` — the config is not optional decoration.
//
// Prose in commit messages is pt-BR, like tickets and ADRs; the code is English.
// Neither is lintable, so both live in the written convention rather than here.
export default {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "subject-case": [2, "always", "lower-case"],
  },
};
