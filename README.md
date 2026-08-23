# Lead Gen Agent

Automated pipeline that sources leads with **Apify**, writes personalized outreach
copy with **Gemini Pro**, logs every lead to a **Google Sheet**, and stages
outreach as **Gmail drafts** (never auto-sends without explicit approval).

```
Apify (source leads)
   -> dedupe against Google Sheet
   -> Gemini Pro (write custom email per lead)
   -> Google Sheet (append row: lead + email + status)
   -> Gmail (create draft; send only with --send)
```

## Human-in-the-loop, by design

Two things in this pipeline are **never** decided automatically, per the
project's own rule:

1. **Which client profile to target.** Every profile in
   `config/client_profiles.yaml` ships with `status: draft`. The pipeline
   refuses to run unless exactly one profile is `active` *and* you pass
   `--confirm-profile <name>` matching it on the command line. Flipping a
   profile to `active` is a manual edit you make in the YAML file.
2. **Money.** Apify runs cost compute units; Gemini calls cost tokens.
   Any run that would fetch more than `max_free_results` (set per-profile,
   default 25) refuses to proceed without `--approve-spend <n>`. Actually
   *sending* email (as opposed to drafting it in Gmail) additionally
   requires `--send`. Default behavior is always: draft-only, capped
   free-tier volume.

Everything else (which leads look like duplicates, exact email phrasing,
retry logic, sheet formatting) runs on its own.

## One-time setup (you need to do this — these are credentials, not decisions)

1. **Apify**: sign up at apify.com, grab an API token, and pick/build an
   actor that scrapes the kind of lead list you want (e.g. an Apollo.io or
   LinkedIn search scraper). Put the token in `.env` as `APIFY_API_TOKEN`
   and the actor id as `APIFY_ACTOR_ID` (or set per-profile in
   `client_profiles.yaml`, which overrides the global default).
2. **Gemini**: get an API key from Google AI Studio (aistudio.google.com).
   Put it in `.env` as `GEMINI_API_KEY`.
3. **Google Sheets + Gmail**: create a Google Cloud project, enable the
   "Google Sheets API" and "Gmail API", create an OAuth client (type:
   Desktop app), download the JSON as
   `config/google_oauth_client_secret.json`, then run:
   ```
   python scripts/setup_google_auth.py
   ```
   This opens a browser once, asks you to approve access, and saves a
   refresh token to `config/google_token.json` (gitignored — never commit
   it). Scopes requested: `spreadsheets` (read/append) and
   `gmail.compose` (drafts). `gmail.send` is only requested if you ever
   pass `--send`.
4. **The Sheet**: a starter sheet has already been created in your Drive
   ("Lead Gen Agent - Master Leads Sheet") with the right header row — see
   `.env` for its `GOOGLE_SHEET_ID`. Reuse it or point at your own by
   changing that value.
5. **GitHub**: this repo is initialized locally with git. To push it, this
   agent doesn't have `gh` or Homebrew available in this environment, so
   either:
   - run `gh auth login` yourself and tell the agent to continue (it will
     use `gh repo create` + `git push`), or
   - hand the agent a GitHub Personal Access Token (repo scope) via
     `GITHUB_TOKEN` and it will create the repo through the REST API and
     push over HTTPS.

Install Python deps: `pip install -r requirements.txt`.

## Running it

```
# Dry run: fetch leads for the active profile, write emails, log to sheet,
# create Gmail drafts. Nothing is sent.
python scripts/run_pipeline.py --confirm-profile ecommerce-brands

# Approve fetching more than the free-tier lead cap for this run
python scripts/run_pipeline.py --confirm-profile ecommerce-brands --approve-spend 100

# Actually send (still requires an active profile + explicit confirmation)
python scripts/run_pipeline.py --confirm-profile ecommerce-brands --send
```

## Routine / scheduled runs

`.github/workflows/schedule.yml` runs the pipeline on a cron schedule using
GitHub Actions. Because there's no human at the keyboard for a scheduled
run, the human-in-the-loop gates are pre-authorized by *you*, in advance,
as repo variables/secrets — the workflow will refuse to run if they're
unset:

- `CONFIRMED_PROFILE` (repo variable) — must match the active profile name.
- `APPROVED_SPEND` (repo variable) — max results per scheduled run.
- `ALLOW_SEND` (repo variable, `"true"`/`"false"`, default false) — if
  false, scheduled runs only ever create Gmail drafts, never send.

Secrets required: `APIFY_API_TOKEN`, `GEMINI_API_KEY`, `GOOGLE_SHEET_ID`,
`GOOGLE_OAUTH_CLIENT_SECRET` (contents of the client secret JSON),
`GOOGLE_TOKEN` (contents of the token JSON produced by the one-time setup).

## Layout

```
config/client_profiles.yaml   who to target + how to pitch them (edit this)
src/leadgen/config.py         loads .env + the active profile
src/leadgen/hitl.py           the human-in-the-loop gates described above
src/leadgen/apify_source.py   runs the Apify actor, normalizes results
src/leadgen/sheets_store.py   dedupe + append rows to the Google Sheet
src/leadgen/email_writer.py   Gemini Pro prompt + JSON parsing
src/leadgen/gmail_sender.py   Gmail draft/send via OAuth
src/leadgen/pipeline.py       wires the above together
scripts/run_pipeline.py       CLI entrypoint
scripts/setup_google_auth.py  one-time OAuth flow
```
