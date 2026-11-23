# Architecture

```text
Browser
  -> same-origin FastAPI
  -> SQLite reference_case lookup and request receipt
  -> read-only frozen CLIP RN50 gallery adapter
  -> deterministic cosine Top-k
  -> SQLite search_result receipt
  -> JSON and browser result panel
```

Runtime embeddings and metadata remain external mounts. Raw media, weights, protected experiments, administration, and fresh inference are outside the public service boundary.
