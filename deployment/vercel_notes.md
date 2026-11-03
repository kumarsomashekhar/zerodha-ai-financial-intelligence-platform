# Frontend hosting (Vercel, free Hobby plan)

The website is a Next.js app deployed from its own GitHub repository (`zerodha-frontend`). It is a separate repository from the backend, because Vercel builds from the folder that contains `package.json`. The `frontend-files/` folder in the backend repository holds a copy of the same source for reference.

## Terms

The Hobby plan is free but limited to personal, non-commercial use. A project demo fits, but a site that charges anyone or serves paying clients does not. Check Vercel's current terms and limits before relying on them.

## Steps

1. Sign in at vercel.com with GitHub and choose the Hobby plan.
2. **Add New → Project**, and import the `zerodha-frontend` repository. If it is not listed, adjust the GitHub app's permissions to include it.
3. Leave the framework as Next.js and the root directory as it is.
4. Add the environment variable before the first deploy:
   - Name: `NEXT_PUBLIC_API_URL`
   - Value: the backend address, for example `https://your-backend.onrender.com`, ending in `.com` with no `/` at the end
   - Type: **Config**
5. Deploy.
6. Copy the site address and put it in the backend's `ALLOWED_ORIGINS` setting on Render (again with no `/` at the end).

Every push to `main` in the frontend repository redeploys the site.

## Changing the backend address later

`NEXT_PUBLIC_` values are fixed into the site at build time. Edit the variable, then open **Deployments**, choose the newest deployment's menu, and click **Redeploy**. Editing the variable alone changes nothing.

## Problems met during the first deployment

| Symptom | Cause and fix |
|---|---|
| Page loads, but the dropdown is empty and says it cannot reach the backend | The Console (F12) shows the address being called. Ours was cut off at `onrender.` with `com` missing (`ERR_NAME_NOT_RESOLVED`). Fix the variable and redeploy |
| Vercel will not let you edit the variable and warns about the public prefix | It was saved as a Secret. Delete it and add it again as **Config** |
| Console shows "blocked by CORS policy" | The backend's `ALLOWED_ORIGINS` is missing or differs from the site address |
| First load is slow | The free backend was asleep |

## Updating the frontend

The running copy is in the `zerodha-frontend` repository. After editing a file there, run `git add -A`, `git commit -m "..."` and `git push` from that folder. Keep `frontend-files/` in the backend repository in step by copying the changed files back, as done during development.