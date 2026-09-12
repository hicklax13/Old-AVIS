---
name: youtube-account
description: "Read a profile's private YouTube data via OAuth."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [YouTube, OAuth, Media]
---

# YouTube Account

Use this skill for read-only access to the YouTube account authorized in the
current Hermes profile. The grant is deliberately separate from Google
Workspace and uses only `https://www.googleapis.com/auth/youtube.readonly`.

For public video transcripts and summaries, use `youtube-content` instead.
YouTube Music and YouTube TV do not have account-control routes in this skill.

## Setup

`SKILL_DIR` is the directory containing this file. Run scripts with the same
Hermes-managed Python environment used by the active profile.

1. Check the current profile:

   ```bash
   python SKILL_DIR/scripts/setup.py --check
   ```

2. If needed, store a Google Desktop OAuth client. Reusing the same client
   application as Google Workspace is allowed; the YouTube token remains
   separate.

   ```bash
   python SKILL_DIR/scripts/setup.py --client-secret /path/to/client.json
   ```

3. If `--check` reports that authorization is needed, start the protected
   loopback flow. Never automate or collect the user's Google password, MFA,
   security-key response, callback URL, or authorization code.

   ```bash
   python SKILL_DIR/scripts/setup.py --authorize
   ```

4. The script opens Google's official consent page in the system browser and
   listens only on an ephemeral `127.0.0.1` port. Tell the user to finish the
   consent screen in that browser. The callback is captured directly, checked
   against the exact OAuth state, and exchanged with PKCE in the same process.
   Do not ask the user to copy anything from the address bar or chat.

   ```bash
   python SKILL_DIR/scripts/setup.py --check
   ```

The authorization wait defaults to five minutes and can be bounded from 30 to
900 seconds with `--timeout`. Cancellation, denial, timeout, or token-exchange
failure preserves the existing working token. Dependencies are exact-pinned in
`scripts/requirements.txt`; `--install-deps` installs only those pins.

Google Cloud must have YouTube Data API v3 enabled for the OAuth project. Treat
administrator or Google policy denials as authoritative.

## Read-only commands

```bash
python SKILL_DIR/scripts/youtube_api.py channel
python SKILL_DIR/scripts/youtube_api.py subscriptions --max 25
python SKILL_DIR/scripts/youtube_api.py playlists --max 25
python SKILL_DIR/scripts/youtube_api.py playlist-items PLAYLIST_ID --max 25
```

Return only the private account data the user requested. Never print or expose
the OAuth client, access token, refresh token, or pending PKCE state. This skill
has no write operations.
