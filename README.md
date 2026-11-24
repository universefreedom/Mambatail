# MambaTail

MambaTail is a CPU-first canine observation research portfolio. It contains a cached-reference search and a separately gated real-video job path. The video path streams an authorized MP4 to a bounded private store, persists a SQLite job, runs a configured single CPU worker, and serves only the completed annotated artifact to the owning browser.

The system reports technical observations and reference similarity. It does not diagnose health, emotion, pain, welfare, or adoption suitability. Reference labels are development-only `SOURCE_MANUAL_REFERENCE_ONLY`; similarity scores are uncalibrated cosine values, not probabilities.

## Verified service path

```text
Browser -> FastAPI -> SQLite metadata -> frozen 51-vector gallery -> Top-k JSON -> Browser
Browser -> streaming MP4 upload -> SQLite job -> single worker -> configured private model runner -> H.264 artifact -> Browser
```

The public repository intentionally excludes model weights, embeddings, datasets, raw images and videos, credentials, experiment outputs, and private databases. Operators mount those assets at runtime through environment variables.

## Local run

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Set the MAMBATAIL_* paths in .env to authorized local assets and a compatible runner.
.venv\Scripts\python -m app.bootstrap
.venv\Scripts\python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`. API documentation is available at `/docs`.

## API

- `GET /healthz`: process, database, and gallery readiness.
- `GET /api/v1/cases`: derived-only gallery metadata from SQLite.
- `POST /api/v1/search`: deterministic cached-vector retrieval.
- `GET /api/v1/system-status`: evidence and safety boundaries.
- `POST /api/v1/videos`: bounded streaming MP4 upload; returns HTTP 202 and a durable job ID.
- `GET /api/v1/jobs/{job_id}`: owner-scoped persistent job state.
- `GET /api/v1/jobs/{job_id}/results`: derived result and artifact metadata.
- `GET /api/v1/jobs/{job_id}/artifacts/{artifact_id}`: owner-scoped completed MP4.

The cached search remains `CACHED_RETRIEVAL_E2E`, not fresh image inference. In the verified local private runtime, two distinct CC BY 4.0 videos completed real decode, Dog detector inference, RTMPose native17 inference, full-frame RN50 `encode_image` sampling, frozen 51-reference retrieval, H.264 encode/readback, SQLite persistence, and Edge playback. Model assets and the site-specific runner remain excluded from this public repository and must be mounted by an authorized operator.

The verified scope is frame observation and reference similarity only: `TEMPORAL_EMA_DISABLED`, `IDENTITY_NOT_BOUND`, and `LIMITED_EXPERT_ASSISTED_RECOMMENDATION`. Reference labels are never copied into a definitive uploaded-video behavior claim, and identity-bound velocity is not computed.

Public anonymous video upload is disabled by default. Set `MAMBATAIL_PUBLIC_UPLOAD_ENABLED=1` only behind an appropriate authentication and abuse-control boundary; the local validation environment enabled it explicitly.

## Tests

```powershell
.venv\Scripts\python -m pytest -q
```

The current public suite has three API/DB/security tests. Real model and browser evidence is kept outside the public repository because it contains local runtime paths and media receipts.

## Deployment

The public read-only demonstration is live at `https://freedom49032.kr` through the existing dashboard-managed `mambatail-web` Tunnel. Root, health, case listing, and cached retrieval have been verified externally. Anonymous video upload is disabled by default until least-privilege authentication is implemented, so public upload-to-playback E2E is not claimed. Local real-video E2E evidence remains separate from this public deployment gate. See [Cloudflare deployment](docs/deployment-cloudflare.md).

- Main demonstration: https://freedom49032.kr/
- API-independent 220-frame pose demonstration: https://demo.freedom49032.kr/
- Offline-first reveal.js presentation: https://freedom49032.kr/presentation/

## Evidence scope

V50-V55 establish bounded technical evidence, including a 51-reference frozen RN50 gallery, native-17 RTMPose diagnostics, and static CPU latency measurements. They do not establish expert behavior accuracy, source-independent generalization, continuous-video identity binding, or clinical validity. Scientific status remains `SCIENTIFIC_NO_PROMOTION`; protected research release remains `PUBLIC_RELEASE_BLOCKED`.

## License and third-party assets

No project-wide software license has been selected by the rights holder. Until that decision is made, this repository is `LICENSE_UNDECIDED`; no permission beyond applicable law is implied. Third-party datasets, model weights, and media are not redistributed.
