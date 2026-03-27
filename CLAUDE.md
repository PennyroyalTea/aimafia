# Deployment

- Always work on the `staging` branch. Never push directly to `main`.
- When asked to commit and push, push to `staging` (which auto-deploys to staging).
- Only merge `staging` into `main` when the user explicitly requests deploying to prod.
- To deploy to prod: `git checkout main && git merge staging && git push && git checkout staging`
