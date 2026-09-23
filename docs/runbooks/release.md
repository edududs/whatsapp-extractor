# Cutting a release

Releases are cut locally from `main`, from the commit history alone, and published by pushing the tag.
The version lives in the annotated tag; `pyproject.toml` and `uv.lock` follow it.

## Prerequisites

- [git-cliff](https://git-cliff.org) on the PATH.
- A clean working tree on `main`, with every commit since the last tag in
  [Conventional Commits](https://www.conventionalcommits.org) form. Commits that do not follow the
  convention are left out of the notes.
- The gate green: `uv run poe check`.

## Steps

1. Preview the next version and its notes. Nothing changes.

   ```sh
   scripts/release.sh --dry-run
   ```

   `feat` bumps `MINOR`, `fix` bumps `PATCH`. Before 1.0 a breaking change also bumps `MINOR`
   (see `[bump]` in `cliff.toml`).

2. Cut it. The script bumps the version with `uv version`, regenerates `CHANGELOG.md`, commits
   `chore(release): vX.Y.Z` and creates the annotated tag whose message is the release notes.

   ```sh
   scripts/release.sh
   ```

3. Publish. The `release` workflow turns the pushed tag into a GitHub Release using the tag
   message as its body.

   ```sh
   git push --follow-tags
   ```

4. Confirm the install line in `README.md` points at the new tag, and that the release appeared
   under the repository's Releases page.

## If something is wrong before pushing

The release commit and the tag are local. Remove them and start over:

```sh
git tag -d vX.Y.Z
git reset --soft HEAD~1
git restore --staged .
git checkout -- CHANGELOG.md pyproject.toml uv.lock
```

Once the tag is pushed, do not move it. Cut the next version instead.
