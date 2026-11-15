# Repository settings as code

Each file here is the exact body the GitHub REST API takes, so you can copy from the API docs
or export a ruleset from the GitHub UI and drop it in. `scripts/repo_settings.py` compares
these with the live repo and applies them.

| file | endpoint | notes |
|---|---|---|
| `repository.json` | `PATCH /repos/{owner}/{repo}` | only the keys listed are managed |
| `actions-permissions.json` | `PUT …/actions/permissions` | which Actions may run |
| `actions-workflow.json` | `PUT …/actions/permissions/workflow` | `GITHUB_TOKEN` defaults; `can_approve_pull_request_reviews` lets release-please open PRs |
| `rulesets/*.json` | `POST`/`PUT …/rulesets` | matched to the live ruleset by `name` |

```
pnpm repo:diff    # show drift between these files and the live repo (exit 1 if any)
pnpm repo:apply   # push the files to GitHub (needs repo admin)
```

CI runs `repo:diff` on every PR that touches this folder. The default Actions token can't read
the Actions-permission endpoints, so those report `skipped` in CI unless a `REPO_ADMIN_TOKEN`
secret (fine-grained PAT, Administration: read) is set. Applying is always done locally.
