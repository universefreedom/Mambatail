# Cloudflare deployment

The origin binds to `127.0.0.1:8765`. A named Cloudflare Tunnel may route `freedom49032.kr` to `http://127.0.0.1:8765` after the zone has authoritative DNS and the operator has authenticated `cloudflared`.

Required independent checks:

1. Authoritative DNS resolves.
2. TLS certificate is valid.
3. `/` returns the portfolio HTML.
4. `/healthz` reports 51 database cases and 51 gallery vectors.
5. `/api/v1/search` completes a database-backed retrieval.
6. A real browser displays the returned results on desktop and mobile widths.
7. API responses have `Cache-Control: no-store`.
8. No credential, model, database administration, or raw asset route is public.

A Cloudflare active-zone indicator alone does not satisfy these checks.
