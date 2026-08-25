# data-viz

Flask + Vue data-visualization app.

## Hosting

- **[Render](https://render.com)** — app hosting.
- **[Neon](https://neon.tech)** — Postgres database.
- **[Resend](https://resend.com)** — transactional email (password reset links).
- **[Cloudflare](https://www.cloudflare.com/)** — File Object Storage R2.

## Releases & Rollback

Deployment is triggered automatically by Render whenever `main` is updated. There is
currently no CI/CD pipeline (no `.github/workflows`) that manages releases.

To make rollbacks easier and more reliable, each release merged into `main` should be
tagged with its `package.json` version, e.g.:

```
git tag v1.2.3 <commit-sha>
git push origin v1.2.3
```

This gives a durable, named reference point in Git history, independent of Render's
deploy history, that can be checked out or reverted to if a later merge breaks
production.

**Known limitation:** A `v1.2.3` tag was created locally for the current `main` commit,
but it has **not** been pushed to GitHub. The environment used to make this
documentation change does not have `git push` access — only branch commits made via
the reporting tool can be pushed. Someone with push access to this repository must run
the commands above (or push the existing local tag) to make `v1.2.3` available on
GitHub. Until that happens, rollback still relies on Render's deploy history or
`git revert` on `main`, as described above.
