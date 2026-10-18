# Studio Posts (Postmanager)

A web app for the dance studio's Instagram: plan posts by hand, or let them go out automatically.

- **Posts**: photo posts, carousels (2–10 items), Reels and Stories. Publish now, schedule, or save as a draft.
- **Recurring posts**: the same post every week on chosen days and times (e.g. the timetable every Monday 09:00).
- **Content queue**: mark photos and videos in the library, and the app posts the next one on a schedule.
- **AI captions** (optional): Claude suggests captions in the studio's voice from a short description and the photos.
- **Library**: upload once, reuse anywhere. Photos are converted to JPEG automatically, and photos too tall or wide for the feed get blurred borders instead of being rejected.
- **Accounts**: sign up with Google or with email + password. New people wait until an owner approves them.
  **Editors** create, schedule and publish posts; **owners** also manage the team, the Instagram connection,
  recurring posts and the queue.
- Failed-post alerts with one-click retry, and a mobile-friendly layout.

## Run it on your Mac

```sh
cd ~/Project/Postmanager
cp .env.example .env                       # then edit the values
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver       # http://localhost:8000 → "Create an account"
.venv/bin/python manage.py run_scheduler   # in a second terminal: publishes due posts
```

The first account you create (or any address in `OWNER_EMAILS`) becomes an owner. Teachers and staff sign up at
`/accounts/signup/`; you get an email (once email is set up) and approve them on the **Team** page.
Without email settings, emails such as password resets are printed in the `runserver` terminal.

> Instagram downloads each photo/video from the app's address at the moment of publishing, so **publishing only works
> when the app is online** with a public `https://` address. Locally you can set everything up, but posts will fail
> with a "media download" error.

## Put it online (Vercel, free plan)

Vercel's free "Hobby" plan is meant for non-commercial use, so Vercel may ask a business to upgrade.
On Vercel the app uses Neon Postgres for data, Vercel Blob for photos/videos (1 GB free), and an external
timer that runs the scheduler every 5 minutes.

1. **Token:** create one at [vercel.com/account/tokens](https://vercel.com/account/tokens) and add
   `VERCEL_TOKEN=...` to the `.env` file. Also fill in `OWNER_EMAILS`, `STUDIO_NAME`, `TIME_ZONE` etc. in
   `.env`, because they're copied to Vercel the first time.
2. **Create the project:** `.venv/bin/python deploy/vercel_deploy.py`
3. **Storage:** in the Vercel dashboard open the project → **Storage**:
   - **Create Database → Neon** (free) → connect to the project.
   - **Create Database → Blob** (free) → connect to the project.
4. **Deploy:** run `.venv/bin/python deploy/vercel_deploy.py` again. It prints the live address, e.g.
   `https://postmanager.vercel.app`. Open it and create your account.
5. **Scheduler timer:** the free plan's built-in cron runs only once a day, so use
   [cron-job.org](https://cron-job.org) (free): create a cronjob for
   `https://<your-app>.vercel.app/cron/tick/?key=<CRON_SECRET>` **every 5 minutes**. Find `CRON_SECRET`
   in Vercel → project → Settings → Environment Variables. "Publish now" doesn't wait for the timer.
6. Use the Vercel address for the Instagram and Google redirect URLs below.

To deploy changes later, run step 4's command again. Settings can be changed in Vercel → Settings →
Environment Variables (redeploy afterwards).

## Put it online (Render)

1. Push this folder to a GitHub repository.
2. On [render.com](https://render.com): **New → Blueprint** and pick the repo. `render.yaml` sets up one web service with
   a 5 GB disk for the database and uploads, plus the scheduler (Starter plan, about $7/month; the free plan sleeps,
   which would stop scheduled posts).
3. Fill in the environment variables it asks for: `SITE_URL` (e.g. `https://studio-posts.onrender.com`),
   `ALLOWED_HOSTS` (`studio-posts.onrender.com`), `TIME_ZONE`, `STUDIO_NAME`, `STUDIO_VOICE`, and the keys below.
4. Set `OWNER_EMAILS` to your email **before** sharing the link, then open the site and create your account.

Any host that runs `./start.sh` with a persistent disk works the same way (Railway, Fly.io, a VPS).

## Connect Instagram (one-time, ~10 minutes)

The studio account must be an Instagram **Business or Creator** account.

1. Go to [developers.facebook.com/apps](https://developers.facebook.com/apps) → **Create app** → use case
   **"Manage messaging & content on Instagram"** → app type **Business**.
2. In the app: **Instagram → API setup with Instagram login**.
   - Copy the **Instagram app ID** and **Instagram app secret** into `INSTAGRAM_APP_ID` / `INSTAGRAM_APP_SECRET`.
   - Under **Business login settings → OAuth redirect URIs**, add `https://<your-site>/instagram/callback/`.
   - Under **Roles → Instagram testers** (or "Add account"), add the studio's Instagram account and accept the invite
     in the Instagram app (Settings → Website permissions → Apps and websites → Tester invites).
3. In Postmanager open **Instagram → Connect Instagram** and log in with the studio account.
   (Or generate a token on the API setup page and paste it under "Option B".)

The app stays in Meta's **development mode**, which is fine: it only has to work for your own account, so no
App Review is needed. The token lasts 60 days and the scheduler renews it automatically.

## Sign in with Google (optional)

1. [console.cloud.google.com](https://console.cloud.google.com) → create a project.
2. **APIs & Services → OAuth consent screen**: user type **External**, app name (e.g. "Studio Posts"), support
   email. Then click **Publish app**. With only the basic email/profile scopes, Google doesn't need to review it.
3. **APIs & Services → Credentials → Create credentials → OAuth client ID** → type **Web application**.
   Under **Authorized redirect URIs** add:
   - `https://<your-site>/accounts/google/login/callback/`
   - `http://localhost:8000/accounts/google/login/callback/` (for trying it locally)
4. Copy the client ID and secret into `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` and restart. A
   **Continue with Google** button appears on the sign-in and sign-up pages.

If someone first signs up with email and later uses Google with the same address, it's the same account.

## Email (optional, recommended online)

Needed for password resets and new-member alerts. With Gmail: turn on 2-step verification, create an
**App password** (Google Account → Security → App passwords), then set `EMAIL_HOST=smtp.gmail.com`,
`EMAIL_HOST_USER=<your gmail>`, `EMAIL_HOST_PASSWORD=<app password>`.

## AI captions (optional)

Create an API key at [console.anthropic.com](https://console.anthropic.com) and set `ANTHROPIC_API_KEY`. The model is
`claude-opus-5-5` (change it with `CAPTION_MODEL`). Each set of three suggestions costs a few cents.
Without a key, everything else works and the AI buttons are hidden.

## Instagram limits worth knowing

- At most 100 API-published posts per 24 hours (carousels count as one).
- Captions: up to 2,200 characters and 30 hashtags.
- Reels: MP4/MOV, 3 s – 15 min, 9:16 recommended. Stories: one photo or video.
- Instagram can't publish to personal accounts, can't add music or filters, and can't tag people's
  photos by position through the API. Do those in the Instagram app.

## Development

```sh
.venv/bin/python manage.py test studio
```

Code layout: `studio/instagram.py` (Graph API publishing), `studio/scheduler.py` (automation),
`studio/ai.py` (captions), `studio/media.py` (uploads), `studio/accounts.py` + `studio/middleware.py`
(sign-up approval), `studio/views.py` + `studio/templates/` (UI).
