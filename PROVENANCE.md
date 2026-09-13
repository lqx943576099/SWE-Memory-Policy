# Provenance

## 2026-09-13: Token-only renderer

This revision retains one compression definition: each output image has a strict
estimated visual-token budget relative to its own unscaled base PNG. The former
width-and-height division API, old fixed-scale policies, and unused composition
compatibility code have been removed. Existing experiment outputs were not
rewritten or deleted.

The compact renderer originates from the local recent3 implementation synchronized
on 2026-09-11. The Python suite-boundary repair and the frozen
`luna_patch32_high_20260906_v2` estimator are aligned with the later standard-token
experiment renderer snapshot. The public package implements validation, offline
input adaptation, explicit unattainable-budget records, and byte-preserving 1×
output; it is not an exact byte copy of an experiment runner.

The estimator is pinned to the project's `gpt-5.6-luna` / `high` profile:
32-pixel patches, maximum dimension 2048, patch budget 2500, multiplier 6/5 with
integer ceiling. Its output is an offline estimate, not measured provider usage.
This repository does not contain a model proxy or imply that every displayed
factor is a completed benchmark condition.

[LOCAL_SOURCE_MANIFEST.json](docs/LOCAL_SOURCE_MANIFEST.json) records current public
source fingerprints. [The gallery manifest](docs/images/gallery/manifest.json)
also fixes the input hash, rendering-source hashes, dependency versions, font
names/hashes, and actual output dimensions and token estimates.

The [gallery input](examples/render_gallery.json) is synthetic source code authored
for this repository. The ten PNG files are deterministic output from the actual
renderer. No private benchmark observation, API request, model answer, font binary,
provider credential, dataset, or task runner is included.

## 2026-09-11: local renderer synchronization

Comparison base: `1edd2a9fe0ab774a701cd9cf73e280b28c61f91c`.
The original synchronization used the local
`luna-recent3-cacheaware-stratified20/SWE-Memory-Policy` experiment worktree, with
its neighboring proxy as the integration reference. The older embedded copy in
the main research checkout was not the source of this synchronization.

That revision introduced strict Responses call/result pairing, OA-window
selection, compact module rendering, visual cleanup, source-line fallback, and
an offline adapter. It still included a historical tile estimator and dimension
scaling. Those compression paths are superseded by the Token-only implementation
above; their old manifests must not be relabeled as the new profile.

## Earlier repository provenance

The initial implementation was extracted on 2026-07-23 from the local
`swe-BENCH` research workspace at commit
`bd2f17e8ab7cc5070f21c9242c0741450554be78`.

The extracted source corresponded to `image_memory.history`,
`image_memory.rendering`, `image_memory.strategies`, and shared deterministic
hashing and serialization helpers. Runtime-specific OpenHands, provider, runner,
dataset and harness code were excluded.

Integrations should consume a pinned repository commit. An experiment manifest
should record that commit, the agent-framework and dataset revisions, the
estimator profile, dependency versions and font hashes.
