# Windows PowerShell setup and verification

All commands target D:\shyam\Projects\CodeMate-AI. Do not target VoxHire or use port
5432. Python 3.12, Docker Desktop/Engine/Compose, and Node are installed in the
verified environment. If missing, install Python 3.12 from python.org, Docker from
docs.docker.com/desktop/setup/install/windows-install/, and Node from nodejs.org;
reopen PowerShell after installation. Ollama is not required for this milestone.

## Backend dependencies and ignored local secrets

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI'
# Only if absent:
# py -3.12 -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.lock.txt
.\backend\.venv\Scripts\python.exe backend\scripts\setup_local.py
```

The helper appends only missing keys; it never displays generated values or replaces
existing settings. If a pre-existing key is blank/invalid, correct it securely rather
than copying an example over an existing .env. Database and JWT secrets use secure
random generation. Keep root .env, backend/.env, and backend/.env.test private and
ignored; example templates contain no secrets. Environment variables override files.
The development lockfile captures the tested Windows/Python 3.12 dependency versions.

## Start and inspect only CodeMate PostgreSQL

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI'
Get-NetTCPConnection -LocalPort 5433 -State Listen -ErrorAction SilentlyContinue
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\infrastructure\start-postgres.ps1
docker compose -p codemate-ai ps postgres
docker inspect --format '{{.State.Health.Status}}' codemate-postgres
docker ps --format '{{.Names}} | {{.Ports}} | {{.Status}}'
```

The initial port query is read-only. The startup helper stops if another service
owns 5433; do not stop that service or select port 5432. An already-running container
owned by codemate-ai is permitted. The temporary execution-policy flag affects only
the child process, not machine policy. Expected: codemate-postgres healthy,
127.0.0.1:5433 -> 5432; VoxHire remains healthy on its existing 5432 binding.
No full Docker inspection/config output is needed because it can expose passwords.

## Apply and verify migrations

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI\backend'
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic check
```

Expected revision: 0002_github_integration (head); no new upgrade operations detected.
This targets DATABASE_URL in backend/.env (CodeMate on 127.0.0.1:5433). Never set it
to another project's database. Alembic downgrades remove CodeMate tables and are
not a normal development startup step; downgrade testing runs only on the test DB.

## Automated tests and checks

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI\backend'
.\.venv\Scripts\python.exe -m pytest -q -W error
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pip check
```

Expected: 73 passed, no warnings; Ruff/format/dependency checks pass. Tests require
backend/.env.test with the dedicated codemate_test_db and codemate_test_user URL.
They apply migrations and reset only test tables. Do not run another copy of the
suite concurrently against that same database. They do not mutate the development
database, and the test role cannot connect to it.

## Start FastAPI

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI\backend'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --no-proxy-headers
```

In another terminal:

```powershell
Invoke-RestMethod 'http://localhost:8000/health'
Invoke-RestMethod 'http://localhost:8000/health/ready'
Start-Process 'http://localhost:8000/docs'
```

Expected liveness status ok and readiness database ready. Stop the server with Ctrl+C.
No environment activation is required. Missing essential security settings fail at
startup; no SQLite fallback or automatic schema creation occurs.

## Manual registration, login, authenticated profile, refresh, and logout

These requests create a real development USER. Choose a new username/email, and
keep returned tokens in variables rather than printing them. PowerShell has no
browser Origin enforcement, but the API still validates any supplied Origin.

```powershell
$api = 'http://localhost:8000'
$headers = @{ 'X-CodeMate-Request' = '1'; 'Origin' = 'http://localhost:3000' }
$username = Read-Host 'New username (lowercase, 3-32 characters)'
$email = Read-Host 'Email'
$securePassword = Read-Host 'Password (12-128 characters, at least 3 categories)' -AsSecureString
$credential = [System.Management.Automation.PSCredential]::new($email, $securePassword)
$password = $credential.GetNetworkCredential().Password
$registration = @{ username = $username; email = $email; password = $password } | ConvertTo-Json
$profile = Invoke-RestMethod -Method Post -Uri "$api/api/v1/auth/register" -Headers $headers -ContentType 'application/json' -Body $registration
$profile
$login = @{ email = $email; password = $password } | ConvertTo-Json
$tokens = Invoke-RestMethod -Method Post -Uri "$api/api/v1/auth/login" -Headers $headers -ContentType 'application/json' -Body $login -SessionVariable authSession
$authorized = @{ Authorization = "Bearer $($tokens.access_token)" }
Invoke-RestMethod -Uri "$api/api/v1/auth/me" -Headers $authorized
# USER gets 403 here; ADMIN gets a paginated list:
# Invoke-RestMethod -Uri "$api/api/v1/users?limit=20&offset=0" -Headers $authorized
$csrf = Invoke-RestMethod -Uri "$api/api/v1/auth/csrf" -Headers $headers -WebSession $authSession
$refreshHeaders = @{ 'X-CodeMate-Request' = '1'; 'Origin' = 'http://localhost:3000'; 'X-CSRF-Token' = $csrf.csrf_token }
$tokens = Invoke-RestMethod -Method Post -Uri "$api/api/v1/auth/refresh" -Headers $refreshHeaders -WebSession $authSession
$refreshHeaders['X-CSRF-Token'] = $tokens.csrf_token
Invoke-RestMethod -Method Post -Uri "$api/api/v1/auth/logout" -Headers $refreshHeaders -WebSession $authSession
Remove-Variable password,registration,login,tokens,authorized,refreshHeaders,csrf,credential,securePassword,authSession -ErrorAction SilentlyContinue
```

Expected: registration 201, login/profile/refresh 200, logout 204. Refresh cookie is
HttpOnly and never in the token JSON. Reusing the old refresh token fails. Anonymous
profile/list requests return 401, USER list access returns 403. Logout revokes
refresh but existing access JWTs can still work for their remaining 15-minute life.
Production requires HTTPS, Secure cookies, same-site frontend/API, and exact HTTPS
origins; do not use development cookie settings for production.

If an administrator is needed, explicitly run the prompted CLI from backend:

```powershell
.\.venv\Scripts\python.exe scripts\bootstrap_admin.py --email 'operator@example.com' --username 'operator'
```

No default admin exists. This creates a new account and never promotes an existing one.

## Frontend regression

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI\frontend'
npm.cmd ci
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build
npm.cmd audit --omit=dev
npm.cmd audit
npm.cmd run dev
```

Expected: lint/typecheck/build pass; production-only audit has zero findings;
full audit still has five high development-tooling findings. No forced fix or
incompatible ESLint downgrade is applied. Open http://localhost:3000 with the API
running; System status should show Backend API and PostgreSQL Online. Use the
Refresh system status button for an immediate check. Visit /register, /login and
/dashboard. Registration uses the development DB in normal operation; no default
account exists. GitHub cards now use the authorized data described below; AI
remains unavailable until Milestone 5.
npm.cmd avoids PowerShell's npm.ps1 execution-policy issue.

## Stop only CodeMate, preserving data

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI'
docker compose -p codemate-ai stop postgres
```

Do not run docker prune or docker compose down -v. No VoxHire command is necessary.

## Milestone 3 frontend routes and browser testing

Normal frontend startup uses the existing public `.env.local` API URL, default
`http://localhost:8000`. This file contains only public configuration; do not add
backend signing or database credentials. Keep the browser at `http://localhost:3000`
so the backend's explicit CORS origin and same-site Strict cookie behavior match.
Use Node 22.12+ or 24+ for the Vitest toolchain (verified Node 24.17.0).

Open `/login` or `/register`, then `/dashboard`, `/dashboard/profile`, and
`/dashboard/settings`. The root `/` is a public landing page. Verified ADMIN
accounts additionally see `/dashboard/admin/users`; a USER is denied even when
entering its URL. Appearance settings are local to the browser. On reload, the
frontend restores the cookie session through CSRF bootstrap and refresh, then
verifies `/auth/me` before showing protected content. On an API outage it offers
session-check retry. Failed logout explicitly says server revocation is unconfirmed.

Run backend pytest first, then E2E, sequentially. Both use the same dedicated test
DB; do not run them concurrently. Start CodeMate PostgreSQL using the helper above.
The normal API on 8000 may remain running. Port 3000 must be free, so stop your own
frontend development server with Ctrl+C before E2E. Port 8001 must also be free;
the runner refuses to kill any existing listener.

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI\backend'
.\.venv\Scripts\python.exe -m pytest -q -W error
Set-Location '..\frontend'
Get-NetTCPConnection -LocalPort 3000,8001 -State Listen -ErrorAction SilentlyContinue
npm.cmd run test:e2e
# Restore normal generated Next type references after the isolated E2E build:
npm.cmd run build
npm.cmd run typecheck
```

The runner requires the existing backend venv, backend/.env.test and installed
Microsoft Edge. Playwright uses `channel: "msedge"`, so no Playwright browser
installation/download is needed on this verified Windows machine. It independently
validates exact `codemate_test_db` / `codemate_test_user` / 127.0.0.1:5433 and the
live identity before writing. It ignores DATABASE_URL / TEST_DATABASE_URL overrides,
applies real migrations, clears only test login-throttle rows for the exclusive
suite, and generates random credentials in process memory. Registration creates
exact disposable accounts only in the test DB; test-only admin promotion is guarded
there too. Cleanup deletes only those exact usernames/emails and their cascaded
refresh sessions. No development or VoxHire data is reset.

The suite builds production frontend assets in `.next-e2e` with the test API URL
`http://localhost:8001`, starts only its own API and frontend child processes,
executes five real-browser tests, then stops those processes and cleans its accounts.
The ordinary `.next` build and development config stay separate. Next regenerates
`next-env.d.ts` for its most recent build; run normal `npm.cmd run build` afterward
before using standalone typecheck/start. Both generated directories are ignored.
The E2E lock prevents concurrent browser suites, but backend pytest must still be
kept separate. If an interrupted process leaves `.e2e-lock`, inspect the 3000/8001
listeners and its owner before removing only that empty lock directory; never stop
an unknown service. Traces/video are disabled; screenshots contain UI only and
remain ignored in `frontend/test-results`.

Verified result: **5 passed, 0 failed, 0 skipped** in headless Edge. Coverage includes
real registration/login/duplicate errors, profile, cookie rotation on reload,
browser preferences, verified logout and anonymous protected denial, mobile
keyboard/modal navigation, concurrent tab restoration and logout invalidation,
backend ADMIN role/directory, outage recovery and local-only logout notice.
Desktop dark dashboard, mobile dashboard, registration, light settings and admin
screenshots were reviewed. This is not a full browser matrix or formal WCAG audit.

Frontend unit result: **49 passed** across five files. Lint reports zero errors and
warnings; strict TypeScript and normal production build pass. Backend regression
remains **73 passed** with warnings as errors. Full npm audit exits 1 with the same
five high dev-tooling findings; `npm.cmd audit --omit=dev` exits 0 with zero findings.
No forced fix, downgrade, security suppression, or speculative override was used.
Historical result: Milestone 3 is COMPLETE. Current Milestone 4 results follow.


## Milestone 4: exact PowerShell commands

Use the existing project and preserve CodeMate port 5433. Never run `down -v`, volume
prune, or commands against VoxHire on 5432. Start Docker Desktop if it is closed.
`start-postgres.ps1` refuses a conflicting container/5433 listener before starting
only the CodeMate postgres service.

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI'
docker version
docker info
powershell -NoProfile -ExecutionPolicy Bypass -File .\infrastructure\start-postgres.ps1

Set-Location .\backend
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock.txt
.\.venv\Scripts\python.exe scripts\setup_github_key.py
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\alembic.exe current
.\.venv\Scripts\alembic.exe check
.\.venv\Scripts\pytest.exe -q -W error
.\.venv\Scripts\ruff.exe check app tests scripts
.\.venv\Scripts\ruff.exe format --check app tests scripts
.\.venv\Scripts\python.exe -m pip check
# Start API in this terminal after manually configuring the App in backend/.env:
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

In a second terminal:

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI\frontend'
npm.cmd install
npm.cmd run test
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
npm.cmd audit --omit=dev
npm.cmd audit
# Run browser tests while ports 3000 and 8001 are free; never alongside backend pytest:
npm.cmd run test:e2e
# Restore the ordinary generated Next.js types/build after the E2E-specific build:
npm.cmd run build
npm.cmd run dev
```

In another terminal, open the connection page:

```powershell
Start-Process 'http://localhost:3000/dashboard/github'
```

E2E starts and stops only its own test API8001 / Next3000 children, uses guarded
`codemate_test_db`/`codemate_test_user` on 5433, generates disposable test credentials,
injects a test-only GitHub HTTP fixture, and deletes only exact disposable account
names. It does not use the local GitHub App secret, register an App, or claim live
OAuth. Edge desktop/mobile checks pass; other browser engines were not verified.

Current results supersede earlier historical entries: **135 backend tests, 73 frontend
tests and seven E2E tests pass**; Ruff, frontend lint, strict TypeScript and normal build
pass. The production-only audit is zero; full audit retains the same five high dev-only
findings. Development migration is `0002_github_integration` with no schema drift.
Live GitHub authorization remains pending manual App setup and the checklist in
[GITHUB_INTEGRATION.md](GITHUB_INTEGRATION.md). Milestone 5 has not started.


## Milestone 5 local AI startup

Do not overwrite existing .env secrets or recreate the working virtual environment.
Apply `0003_ai_investigations` with the normal Alembic upgrade command. The worker
is a separate process and is required for queued investigations and retention.

```powershell
Get-Command ollama
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/tags
# Only if the selected model is missing; never an automatic download:
ollama pull qwen2.5-coder:3b
# Only if the endpoint is stopped, in its own foreground terminal:
ollama serve
Set-Location 'D:\shyam\Projects\CodeMate-AI\backend'
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe scripts\ai_worker.py
```

Start FastAPI and Next.js in separate terminals using the existing commands above.
Open http://localhost:3000/dashboard/ai after signing in. Run Pytest, browser E2E
and the live fixture verifier sequentially; all use the exclusive guarded test DB.
The exact complete command sequence and model/privacy/worker lifecycle are in
[AI_DIAGNOSTICS.md](AI_DIAGNOSTICS.md). The local fixture command, after migrations:

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI\backend'
.\.venv\Scripts\python.exe scripts\verify_local_ai.py
ollama ps
```

This verifier commits/reloads a report for a harmless fixture, then deletes only
its disposable test account. It does not create a real failed GitHub workflow.
VoxHire on port 5432 remains separate and untouched.


## Milestone 6 local voice setup (Python 3.12, Windows 11)

These additions use the existing virtual environment and PostgreSQL port 5433.
Do not overwrite backend/.env, frontend/.env.local, or another project's resources.
The example configuration documents defaults that work when FastAPI starts from
backend. Earlier milestone revision notes above are historical; the current head
is 0004_voice_agent. Ollama is required for natural-language interpretation and
general explanations, while known navigation commands work without it.

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI\backend'
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -c "import ctranslate2; print(ctranslate2.get_supported_compute_types('cpu'))"
```

Verified direct runtimes: faster-whisper 1.2.1, CTranslate2 4.8.3, PyAV 19.0.1,
piper-tts 1.8.0, ONNX Runtime 1.31.0. Official Windows wheels were installed; no
unknown installer scripts or separate FFmpeg executables were used. All transitive
versions are recorded in requirements-dev.lock.txt. CI installs dependencies but
never downloads or initializes speech models in ordinary tests.

### Explicit first-run models

Run the following only after approving the model downloads. The script downloads
from Systran/faster-whisper-base and rhasspy/piper-voices through official Hugging
Face endpoints. It pins resolved commit revisions and records voice SHA-256 hashes
and the model card in ignored backend/models. It never executes downloaded scripts.
Models are not committed. The user approved this download on 2026-10-14.

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI\backend'
.\.venv\Scripts\python.exe scripts/setup_voice_models.py --download
# Optional small multilingual model, increases RAM and processing time:
# .\.venv\Scripts\python.exe scripts/setup_voice_models.py --download --whisper small
# Then configure WHISPER_MODEL_SIZE=small and WHISPER_MODEL_PATH=models/whisper-small.
```

Piper uses en_US-ljspeech-medium (one English female speaker, 22050 Hz). The
[official model card](https://huggingface.co/rhasspy/piper-voices/raw/main/en/en_US/ljspeech/medium/MODEL_CARD)
identifies the [LJ Speech dataset](https://keithito.com/LJ-Speech-Dataset/) as public
domain and describes training from scratch by Bryce Beattie. The voice repository metadata declares MIT licensing. Preserve upstream license
and copyright notices and include attribution to the Piper voices project and
voice author Bryce Beattie when redistributing the selected model. The setup
script retains both the repository README and this model card with pinned source
revisions; the public-domain dataset status does not remove model distribution
notice requirements. The [Piper engine](https://github.com/OHF-Voice/piper1-gpl)
is GPL-3.0-or-later, separately from the dataset/model card. Distributing Piper
requires preserving its license and complying with its GPL source obligations.
The Python wheel includes COPYING and bundled dependency license notices.
French STT is supported by the multilingual Whisper base/small models. This page
offers English TTS only; French voice output requires an independently installed,
license-reviewed French voice and is not offered by the current UI.

### Services and verification

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\infrastructure\start-postgres.ps1
Set-Location backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic check
Invoke-RestMethod http://127.0.0.1:11434/api/tags
# If the existing local model is absent, explicitly approve/download it:
# ollama pull qwen2.5-coder:3b
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# In a separate backend PowerShell for investigation processing:
.\.venv\Scripts\python.exe scripts/ai_worker.py
# In a separate frontend PowerShell:
Set-Location 'D:\shyam\Projects\CodeMate-AI\frontend'
npm.cmd ci
npm.cmd run dev
```

Use one API process for practical model memory/concurrency limits. Model paths
are server configuration, never user-supplied filesystem paths. No .env settings
were overwritten during implementation. Both whisper and Piper defaults point to
the approved downloaded files relative to backend.

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI\backend'
$env:PYTHONPATH = $PWD.Path
.\.venv\Scripts\python.exe scripts/verify_voice_local.py
Remove-Item Env:PYTHONPATH
.\.venv\Scripts\python.exe -m pytest -q -W error --tb=no
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
Set-Location ..\frontend
npm.cmd test
npm.cmd run lint -- --max-warnings=0
npm.cmd run typecheck
npm.cmd run build
```

The local smoke script generates synthetic English speech through Piper, decodes
and transcribes it with real faster-whisper, then asks real Ollama to classify a
natural phrasing. It is not a physical microphone or listening test.

### Manual hardware and live-account checklist

Sign in at http://localhost:3000/dashboard/voice. In Windows Settings enable
microphone privacy access for desktop apps, then allow localhost microphone access
in Edge/Chrome. Browser recording requires a secure context; localhost qualifies.
No microphone is accessed until Start recording is pressed. Stop transcribes;
Cancel discards audio. A maximum 30-second recording is stopped automatically.

1. Record "CodeMate, open my GitHub repositories." Review/edit the transcript,
   send it, and click the returned internal link.
2. Type "List my connected repositories." Choose a listed owner/repository.
   Then ask "Show my latest CI pipeline" and "Find the latest failed workflow".
   Verify the IDs/status against your authorized GitHub installation.
3. Say/type "Analyze that workflow." Check owner, repository, run and status.
   Cancel first and verify no investigation starts. Repeat and explicitly Confirm.
   Open the saved report; repeated confirmation must not create another report.
4. Ask "Explain what caused this failure" after an investigation completes.
   Generate voice response, then Play, Pause, Stop playback and Replay. Check
   that actual output is audible and that no audio overlaps a new request.
5. Test permission denial, cancellation, browser refresh, New conversation,
   expired sessions/actions, unknown repositories and rapid repeated clicks.

Known deterministic phrases: Open dashboard/profile/settings/AI diagnostics,
Open CI/CD monitoring, Select repository owner/repo, List connected repositories,
Show latest pipeline, Find latest failed workflow, Show failed jobs, Open workflow
logs, Analyze that workflow, Show previous investigations, Open latest report,
Explain what caused this failure, What can you do, yes and cancel. Natural variations
use local Ollama. Voice-only yes never authorizes investigation creation.

Troubleshooting: missing speech model means check the configured model files and
restart/check services. Inference timeout suggests shorter input or CPU int8.
Permission denial does not block typed commands. Piper generation does not auto-play;
press Play to satisfy browser autoplay rules. GitHub authorization errors require
reviewing the existing GitHub connection/selected repositories. Expired conversation
errors require New conversation. Restore codemate-postgres on 5433 for database
errors; never point tests at development data. Nothing downloads models in response
to these errors. Physical microphone, audible output and the personal live GitHub
flow remain separate manual checks until verified by the user.


### Explicit real-model Edge fixture check

This optional verifier is separate from ordinary CI and uses real local speech
models with controlled GitHub data, synthetic microphone input and a disposable
account. Do not run Pytest concurrently. Use one fresh prefix matching e2e_ plus
ten hex digits consistently. Ensure ports 3000/8001 are free before launching
servers, and stop only servers you own. No personal browser session is used.

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI\backend'
$env:PYTHONPATH = $PWD.Path
.\.venv\Scripts\python.exe scripts/verify_voice_local.py --investigate
Remove-Item Env:PYTHONPATH
Set-Location ..
.\backend\.venv\Scripts\python.exe frontend/scripts/e2e_backend.py prepare e2e_637af28490
$env:CODEMATE_REAL_VOICE = '1'
.\backend\.venv\Scripts\python.exe frontend/scripts/e2e_backend.py serve e2e_637af28490
```

Start `npm.cmd run dev` in another frontend terminal. In a third frontend terminal:

```powershell
$env:E2E_ACCOUNT_PREFIX = 'e2e_637af28490'
node.exe scripts/verify-voice-browser.mjs
```

Replace the example prefix consistently for a fresh run. The helper guards the
test role/database on port 5433, never loads live GitHub credentials, and uses a
unique mock GitHub identity per prefix. The verifier checks recording/transcription,
workflow facts, Cancel, one explicit Confirm, Piper decoding/playback controls and
history restoration. It does not establish physical microphone or audible output.
Stop the two test servers with Ctrl+C in their own terminals, then clean only that
prefix from the project root:

```powershell
.\backend\.venv\Scripts\python.exe frontend/scripts/e2e_backend.py cleanup e2e_637af28490
```
