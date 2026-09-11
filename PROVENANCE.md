# Provenance

## 2026-09-11 local renderer synchronization

Upstream comparison base: `1edd2a9fe0ab774a701cd9cf73e280b28c61f91c`.

Authoritative implementation: the local
`luna-recent3-cacheaware-stratified20/SWE-Memory-Policy` experiment worktree.
The neighboring `image-memory/src/image_memory/proxy.py` compact/fallback and
scaling branches define the integration behavior; `conditions.py` defines the
online recent3 clean registrations.

The existing main checkout contains an older policy copy and was not used as
the authority. The experiment worktree and historical outputs were not modified.
Core file SHA256 fingerprints are recorded in
[LOCAL_SOURCE_MANIFEST.json](docs/LOCAL_SOURCE_MANIFEST.json).

The new `offline.py` is an extraction adapter, not a copied experiment runner.
It calls the synchronized core renderer and scale functions, with
`compact_visual_whitespace_v2`, and adds local JSON/TXT ingestion and manifests.
Existing upstream composition helpers remain for compatibility. Two former
history display functions live in `legacy.py`; package-level exports remain.
No benchmark inputs, model request logs, provider credentials, generated images,
or font binaries are included.

The token estimator is the historical local `openai_high_detail_tiles_v1`
implementation. Its results are estimates, not universal model billing.
Only token2p0 was registered online in the inspected condition file; additional
offline factors do not constitute additional online experiments.

## Earlier repository provenance


The initial implementation was extracted on 2026-07-23 from the local
`swe-BENCH` research workspace at commit
`bd2f17e8ab7cc5070f21c9242c0741450554be78`.

The extracted source corresponds to these former modules:

- `image_memory.history`
- `image_memory.rendering`
- `image_memory.strategies`
- shared deterministic hashing and serialization helpers

The package namespace was changed to `swe_memory_policy`, corrupted Unicode
test fixtures were replaced with explicit `中文 ✓` fixtures, and runtime-specific
OpenHands, proxy, provider, runner, dataset, and harness code was intentionally
excluded.

After this repository is published, it should become the canonical source for
rendering and image-history policies. Agent integrations should consume a pinned
commit rather than maintain copied policy implementations. Experiment manifests
should record that commit alongside the agent-framework and dataset revisions.
