# lead-gen-agent

Automated cold-outreach pipeline: sources leads with **Apify**, writes
personalized emails with **Gemini**, logs everything to a **Google Sheet**,
and stages outreach as **Gmail drafts**. Sending is never automatic — see
Guardrails below.

## What it does

```
Apify (source leads for the active client profile)
   -> dedupe against the Google Sheet (skip emails already logged)
   -> Gemini (write a 3-paragraph personalized email per lead)
   -> Google Sheet (append/update row: lead + email + status)
   -> Gmail (create a draft; only sent when a human explicitly triggers it)
```

Email body structure is assembled in code, not left to the model, so
formatting can't drift between runs:

1. Greeting: recipient's first name, alone on line 1.
2. Paragraph 1 (AI-written): one direct sentence naming the specific pain
   point — addressed as "you", no generic "many companies like X" filler.
3. Paragraph 2 (AI-written): how the offer solves it, 1-2 sentences.
4. Paragraph 3 (AI-written): the call to action, alone, as one question.
5. `Book a Slot: My Calendar` — "My Calendar" is a real hyperlink
   (`CALENDAR_URL` in `.env`) in the HTML part of the message; the plain-text
   part shows the URL in parentheses as a fallback.
6. `Best,` / sender name.

Subject lines are title-cased in code (`_titlecase_subject` in
`email_writer.py`) — first letter of every word capitalized, acronyms and
contractions left alone — regardless of what Gemini returns.

## Guardrails (human-in-the-loop, by design)

Two categories of decision are **never** made automatically:

1. **Which client to target.** Exactly one profile in
   `config/client_profiles.yaml` may have `status: active`. The pipeline
   also refuses to run unless the caller passes `--confirm-profile <name>`
   matching it — so a stale terminal/cron job can't silently email the
   wrong client's list after someone else flips the active profile.
2. **Money and sending real email.**
   - Apify runs cost compute units. Fetching more than a profile's
     `max_free_results` (default 25) requires `--approve-spend <n>`.
   - Gmail drafts are always created first. Actually **sending** requires
     `--send` on the CLI *and* an OAuth token that was authorized with the
     `gmail.send` scope (`python scripts/setup_google_auth.py --allow-send`
     — a one-time, interactive, human-only step; `gmail.send` is
     deliberately not requested by default). Without that scope, sending
     fails outright.

Enforcement lives in `src/leadgen/hitl.py` — every code path that spends
money or sends mail goes through it, so a new caller can't accidentally
bypass a gate.

**Currently authorized scopes:** `spreadsheets`, `gmail.compose`, and
`gmail.send` (upgraded from compose-only on 2026-08-25 to allow scheduled
sending — see below). To drop back to draft-only, delete
`config/google_token.json` and re-run `setup_google_auth.py` without
`--allow-send`.

## How to execute

```bash
# Install deps (once)
pip install -r requirements.txt

# One-time Google OAuth (draft-only scopes)
python scripts/setup_google_auth.py
# ...or with send capability:
python scripts/setup_google_auth.py --allow-send

# Dry run: fetch leads, write emails, log to sheet, create Gmail drafts.
# Nothing is sent.
python scripts/run_pipeline.py --confirm-profile <active-profile-name>

# Approve fetching more than the free-tier cap
python scripts/run_pipeline.py --confirm-profile <name> --approve-spend 100

# Actually send (requires gmail.send scope, see above)
python scripts/run_pipeline.py --confirm-profile <name> --send
```

Current active profile: **`home-service-trades-us`** — US-based
HVAC/plumbing/electrical/cleaning solo operators & small shops, pitching
lead-gen + appointment-setting + an AI intake agent, CTA is a 15-minute
call. Change by editing `config/client_profiles.yaml` (a human decision,
never automated).

### Redoing/fixing drafts already sitting in Gmail

Not a normal pipeline path, but came up when formatting needed a
retroactive fix. Reconstruct `Lead` objects from the Sheet rows (columns:
timestamp, profile, full_name, title, company, email, linkedin_url,
subject, body, status, gmail_draft_id, sent_at), regenerate with
`email_writer.write_outreach_email`, then `gmail_sender.create_draft` +
`gmail_sender.delete_draft` (old id) + `sheets_store.update_row` to
replace the row in place. `gmail_sender.send_draft(creds, draft_id)` sends
an existing draft exactly as it currently reads in Gmail (including manual
edits made in the Gmail UI) rather than reconstructing it — use this, not
`send_email`, when the point is to preserve a human's edits.

### Scheduled sending

Gmail has no native "schedule send" via API, and a cloud-hosted scheduler
can't reach the local, gitignored OAuth token — so a scheduled send is a
**local, detached OS process** on the machine holding the credentials:

```bash
nohup bash -c 'sleep <N> && python3 scripts/send_scheduled_drafts.py' \
  > scheduled_send.log 2>&1 < /dev/null &
disown
```

`scripts/send_scheduled_drafts.py` sends every Sheet row still in
`draft_created` status via `gmail_sender.send_draft` (preserving whatever
edits are currently in each Gmail draft) and flips the row to `sent`.
**Caveat:** since this is a real local process, not a cloud job, the
machine must stay awake (not sleep/shut down) until the scheduled time or
the send stalls/misses the window.

## Layout

```
config/client_profiles.yaml   who to target + how to pitch them (edit this)
src/leadgen/config.py         loads .env + the active profile
src/leadgen/hitl.py           the human-in-the-loop gates described above
src/leadgen/apify_source.py   runs the Apify actor, normalizes results
src/leadgen/sheets_store.py   dedupe + append/update rows in the Sheet
src/leadgen/email_writer.py   Gemini prompt, JSON parsing, body/subject rendering
src/leadgen/gmail_sender.py   Gmail draft/delete/send via OAuth
src/leadgen/pipeline.py       wires the above together
scripts/run_pipeline.py       CLI entrypoint
scripts/setup_google_auth.py  one-time OAuth flow
scripts/send_scheduled_drafts.py  sends all draft_created rows as-is
```

Full setup instructions (Apify/Gemini/Google Cloud credentials, GitHub
Actions cron) are in `README.md`.

## Testing

```bash
python3 -m pytest tests/ -q
```

Covers JSON extraction from Gemini responses, subject title-casing, and
the exact spacing/hyperlink shape of the rendered email body.
