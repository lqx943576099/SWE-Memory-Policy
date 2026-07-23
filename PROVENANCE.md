# Provenance and synchronization

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
