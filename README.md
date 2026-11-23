# MambaTail

MambaTail is a CPU-first canine observation research portfolio. This public service demonstrates an evidence-bounded path from a browser request through FastAPI and SQLite to deterministic cosine retrieval over a separately mounted frozen CLIP RN50 gallery.

The system reports technical observations and reference similarity. It does not diagnose health, emotion, pain, welfare, or adoption suitability. Reference labels are development-only `SOURCE_MANUAL_REFERENCE_ONLY`; similarity scores are uncalibrated cosine values, not probabilities.

## Verified service path

```text
Browser -> FastAPI -> SQLite metadata -> frozen 51-vector gallery -> Top-k JSON -> Browser
```

The public repository intentionally excludes model weights, embeddings, datasets, raw images and videos, credentials, experiment outputs, and private databases. Operators mount those assets at runtime through environment variables.

## Local run

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Set the three MAMBATAIL_* paths in .env to authorized local assets.
.venv\Scripts\python -m app.bootstrap
.venv\Scripts\python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`. API documentation is available at `/docs`.

## API

- `GET /healthz`: process, database, and gallery readiness.
- `GET /api/v1/cases`: derived-only gallery metadata from SQLite.
- `POST /api/v1/search`: deterministic cached-vector retrieval.
- `GET /api/v1/system-status`: evidence and safety boundaries.

The demo request selects an existing frozen case vector. This is `CACHED_RETRIEVAL_E2E`, not fresh image inference. Fresh RN50 encoding and RTMPose execution remain separate, protected research paths.

## Tests

```powershell
.venv\Scripts\python -m pytest -q
```

## Deployment

The intended public URL is `https://freedom49032.kr`. A live badge or deployment claim is made only after DNS, TLS, root page, API, database-backed retrieval, and browser rendering all pass independently. See [Cloudflare deployment](docs/deployment-cloudflare.md).

## Evidence scope

V50-V55 establish bounded technical evidence, including a 51-reference frozen RN50 gallery, native-17 RTMPose diagnostics, and static CPU latency measurements. They do not establish expert behavior accuracy, source-independent generalization, continuous-video identity binding, or clinical validity. Scientific status remains `SCIENTIFIC_NO_PROMOTION`; protected research release remains `PUBLIC_RELEASE_BLOCKED`.

## License and third-party assets

No project-wide software license has been selected by the rights holder. Until that decision is made, this repository is `LICENSE_UNDECIDED`; no permission beyond applicable law is implied. Third-party datasets, model weights, and media are not redistributed.
