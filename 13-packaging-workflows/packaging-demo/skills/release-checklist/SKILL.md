---
name: release-checklist
description: Step-by-step checklist for cutting a production release. Only run when the user explicitly invokes /packaging-demo:release-checklist.
disable-model-invocation: true
---

Before releasing to production, walk through this checklist with the user:

1. Confirm the full test suite passes on the release branch.
2. Confirm the CHANGELOG has an entry for every user-facing change since the last tag.
3. Tag the commit with the release version.
4. Push the tag and trigger the deploy.
5. Post the release notes wherever the team tracks releases.
