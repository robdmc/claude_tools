# memhound — Skill Specification (v1)

## 1. Overview

`memhound` is a Claude Code skill that turns a collection of documents into a searchable, source-grounded **memory project**. Documents are decomposed into atomic, decontextualized **Notes** stored in LanceDB; the agent answers questions by navigating those Notes via a grep-loop pattern (iterative search, narrowing filters, fetching source when promising).

The skill is **source-agnostic** — it ingests a canonical markdown-with-frontmatter format. Source-specific converters (e.g., Logseq → canonical) are throwaway scripts that live outside the skill. The skill is also **project-agnostic** — one skill installation can serve many memory projects (different corpora, different scopes), each a self-contained directory of LanceDB tables, replicated source files, and assets.

v1 supports: bulk import, ad-hoc additions (prose, file, file+prose, context-assembled), corpus navigation, and an introspection feature for capturing skill-improvement opportunities.

## 2. Reference project

`/Users/rob/rob/repos/claude_tools/data/skills` provides the **Python environment management pattern only**. Inherit:

- `scripts/pyproject.toml` declares deps; `scripts/uv.lock` pins them
- All Python invoked via `uv run --project {SKILL_DIR}/scripts python ...`
- `allowed-tools` frontmatter whitelists that exact pattern
- Python ≥ 3.12

Do **not** inherit data-skill-specific conventions (polars defaults, marimo workflows, vdopen, etc.). Different deps, different domain.

## 3. Corpus assumptions

- **Source format the skill ingests:** canonical markdown with YAML frontmatter (defined in §6.1)
- **Source location:** declared per-project via `memhound.toml`; can also be passed at import time with `/memhound import <dir>`
- **Bootstrap corpus:** Logseq graph at `/Users/rob/rob/repos/references_logseq`, converted to canonical format by a one-off script (§6.0). The skill itself never sees Logseq.
- **Scale assumption for v1:** hundreds to low thousands of docs, low thousands to ~10k Notes. Extraction costs **~ (segments + 2) LLM calls per doc** — per-segment Note extraction plus one per-doc noun-unification pass and one per-doc summary pass (§6.3). Acceptable at v1 scale; revisit batching if corpora grow past ~10x.
- **Persistence:** corpus persists across sessions in the project directory.

## 4. Directory layout

### 4.1 Memory project layout

A memory project is a directory the user owns:

```
my-memhound-project/
├── memhound.toml               # project config
├── lancedb/                    # LanceDB store
│   ├── notes/                  # notes table (vectors + cols)
│   └── stats.json              # cached corpus stats (§7.2), refreshed per ingest
├── sources/                    # canonical-format docs, one file per doc-id
│   └── <doc-id>.md             # frontmatter + markdown body
├── assets/                     # content-addressed binaries
│   └── ab/cd/abcd1234...pdf    # nested by sha256 prefix (2/2 fanout)
├── assets-manifest.parquet     # asset_id, sha256, original_filename, mime, referenced_by
├── documents.parquet           # doc-level metadata + structural outlines (§5.2)
├── introspections/             # one markdown file per stored introspection
│   └── 20260419-143052-extraction-misses-tables.md
└── logs/                       # ingestion run logs (jsonl, append-only)
    └── ingest-20260419-143052.jsonl
```

### 4.2 Project resolution order

When the skill activates, it resolves the active project in this order:

1. Explicit `--project <path>` flag in the invocation
2. `$MEMHOUND_PROJECT` environment variable
3. Prompt the user to specify

### 4.3 `memhound.toml` schema

```toml
[project]
name = "references"
author = "rob"                 # default for synthesized frontmatter

[ingest]
source_root = "/path/to/canonical-imports"   # default for bulk import
note_globs  = ["**/*.md"]
asset_globs = ["**/*.{pdf,png,jpg,jpeg,gif,webp}"]

[extraction]
model = "claude-sonnet-4-6"    # for note extraction
max_notes_per_segment = 12

[embedding]
# MLX-native, runs locally on Apple Silicon. mxbai-embed-large-v1 is BERT-family,
# 512-token context, 1024-dim. Plenty for atomic Notes (§5) — see §6.7 for rationale.
backend = "mlx"                                       # only backend v1 supports
model   = "mlx-community/mxbai-embed-large-v1"        # bf16 full precision
dim     = 1024
max_length = 512                                      # truncate long Notes / queries
batch_size = 64                                       # ingest-side batch
daemon_idle_seconds = 900                             # embedder daemon idle shutdown (§6.7.1)

[search]
# Hybrid = vector (semantic) + BM25 FTS (keyword) + fuzzy matching, combined by a reranker.
reranker = "rrf"               # one of: rrf, linear, cohere
rrf_k = 60                     # RRF constant; only used when reranker = "rrf"
linear_weight = 0.7            # semantic weight for linear reranker (1 - weight → FTS); only when reranker = "linear"
fuzziness = 1                  # default Levenshtein edit distance for fuzzy FTS queries (0 disables)

[introspection]
impact_threshold = "medium"    # one of: low, medium, high
```

## 5. Note schema

A Note is a row in the `notes` table:

| Column | Type | Notes |
|---|---|---|
| `id` | string | stable id, e.g. `<doc-id>-n0007` |
| `text` | string | decontextualized, self-contained content |
| `kind` | string | `thesis \| claim \| decision \| proposal \| question \| task \| constraint \| spec \| reference \| note \| document_summary` |
| `nouns` | list[string] | noun phrases (entities AND concepts) |
| `prior_refs` | list[string] | note ids of explicit cross-refs found in source |
| `source_refs` | list[struct] | each: `{document_id: string, paragraph_range: [int, int]}` |
| `document_id` | string | denormalized for filtering |
| `document_title` | string | denormalized |
| `document_kind` | string | denormalized (canonical doc kind, distinct from note kind) |
| `document_date` | date? | denormalized |
| `document_author` | string? | denormalized |
| `embedding` | vector[dim] | from `text` |
| `created_at` | timestamp | for incremental re-extract debugging |
| `source_hash` | string | sha256 of the Note's source paragraphs, specifically `"\n\n".join(paragraphs[first:last+1])` from `sources/<doc-id>.md` using the Note's `source_refs[0].paragraph_range`. For Notes with multiple `source_refs` (e.g., `document_summary`), concatenate each range with `"\n\n"` between ranges in source order before hashing. Lets §6.3 detect when paragraph content changed without re-embedding untouched Notes. |

**Decontextualization rule:** `text` must be readable in isolation. Pronouns resolved, proper nouns inlined, "the migration plan" rather than "the plan." The extraction prompt enforces this.

**Source grounding rule:** every Note has at least one `source_refs` entry pointing to a paragraph range in `sources/<doc-id>.md`. `document_summary` Notes may span multiple paragraph ranges or the whole document.

### 5.1 Indexes

Two indexes are built on the `notes` table:

- **Vector index** on `embedding` (IVF_PQ or HNSW — LanceDB default; tune at implementation).
- **BM25 full-text index** on `text` (LanceDB native FTS, not Tantivy-external). `nouns` is *not* BM25-indexed; it stays a list-contains filter column. Rebuild on doc re-extraction via `create_fts_index(..., replace=True)`.

These two indexes are what the hybrid search in §7.2 combines.

### 5.2 Documents table

`documents.parquet` at the project root holds doc-level metadata and structural outlines. One row per canonical doc in `sources/`:

| Column | Type | Notes |
|---|---|---|
| `id` | string | matches frontmatter `id` |
| `title` | string | from frontmatter |
| `kind` | string | canonical doc kind |
| `date` | date? | from frontmatter |
| `author` | string? | from frontmatter |
| `paragraph_count` | int | total paragraphs in body |
| `note_count` | int | Notes extracted from this doc |
| `outline` | list[struct] | each: `{level: int, heading: string, paragraph_range: [int, int], note_count: int}` — one entry per markdown heading, in source order |
| `source_hash` | string | sha256 of body; lets §6.3 skip unchanged docs without re-parsing |

Rebuilt in full on every ingest run (cheap — low thousands of rows). Never embedded; not indexed. Read by `outline()`, `list_docs()`, and `corpus_stats()` (§7.2). This table plus `lancedb/stats.json` give the agent cheap corpus orientation without having to issue `find` queries just to understand shape.

## 6. Ingestion pipeline

### 6.0 Source → canonical conversion (out of skill scope)

A separate, throwaway script converts source-specific corpora to canonical format. For the Logseq bootstrap, the script lives at `/Users/rob/rob/repos/claude_tools/memhound-bootstrap/logseq_to_canonical.py` — **outside** the skill directory, since it's not part of the skill surface. Responsibilities for the Logseq variant:

- Walk `pages/` and `journals/` of the graph
- Resolve `((block-uuid))` block refs by inlining the referenced text (so the doc is self-contained)
- Resolve `{{embed [[Page]]}}` and `{{embed ((uuid))}}` by inlining
- Promote `key:: value` properties → frontmatter where they map (`date`, `author`); drop or keep-as-text otherwise
- Promote `#tags` → `tags` frontmatter array
- Resolve `![](../assets/foo.pdf)` references — copy binaries into output `assets/`, rewrite paths as relative
- Generate stable `id` from source path (e.g., `lg-pages-<slugified-name>`, `lg-journals-2024-01-15`)
- Output canonical-format directory ready for `/memhound import`

The skill never sees Logseq syntax.

### 6.1 Canonical import format

A canonical import is a directory:

```
import-dir/
├── docs/
│   ├── 0001-project-x.md
│   ├── 0002-2024-01-15-journal.md
│   └── ...
└── assets/
    ├── diagram.png
    └── proposal.pdf
```

Each doc:

```yaml
---
id: lg-pages-project-x         # stable id; idempotent across re-runs of converter
title: Project X
kind: document                 # default; converter may set: journal, meeting, spec, paper, ...
date: 2024-01-15               # optional
author: rob                    # optional
origin: "logseq:pages/Project X.md"   # provenance breadcrumb, not used by skill
tags: [ml, infra]              # optional, promoted into nouns at extraction
original_asset: null           # for Mode B (PDF/image-derived docs), points to the source binary's asset id
---

<markdown body — assets referenced as ../assets/diagram.png>
```

Asset discovery: scan body for relative paths matching `asset_globs`; anything that resolves to an existing file in `import-dir/assets/` gets copied into the project's `assets/` content-addressed.

### 6.2 Write paths (all under `/memhound`)

| Invocation | Behavior |
|---|---|
| `/memhound import <dir>` | Bulk import canonical-format docs |
| `/memhound store <file-path>` | Single-file ingest; if no frontmatter, synthesize from path/content |
| `/memhound <prose>` | Wrap prose as a new doc, write to `sources/`, extract Notes |
| `/memhound <prose>` + dropped file | **Mode A**: store file as asset, prose as doc body, link via `original_asset` |
| `/memhound decompose <path-or-dropped-file>` | **Mode B**: agent reads binary natively, emits canonical markdown, ingests it; binary kept as asset |
| `/memhound remember <prompt>` | Agent assembles content from current conversation context, shows draft, **always** confirms with user, then stores |
| `/memhound forget <doc-id>` | Delete a doc and all its Notes (§6.8) |

### 6.3 Bulk import flow

1. Walk `<dir>/docs/`, list candidate files
2. For each file:
   1. Parse frontmatter; validate `id` and required fields
   2. Compute sha256 of file body
   3. Look up `id` in current `sources/` — if exists and hash matches, skip
   4. If exists with different hash: mark for re-extraction (Notes for this `id` get superseded)
   5. Copy file → `sources/<id>.md`
   6. Scan body for asset references; copy each into `assets/<aa>/<bb>/<sha>` if new; record in `assets-manifest.parquet`
3. For each new-or-changed doc:
   1. Segment by structural boundaries (markdown headings, then paragraph clusters as fallback). Capture the heading hierarchy — `{level, heading, paragraph_range}` per heading — for use in §5.2's outline column.
   2. Call extractor LLM per segment with the extraction prompt (§6.5). Notes come back with doc-local `prior_refs` (e.g., `n0003` referring to another Note from the same doc).
   3. **Assign global `id`s and rewrite `prior_refs`.** After all segments return, walk the combined Note list in source order and assign `id = <doc-id>-n<NNNN>` (zero-padded, monotonic). Build a `{doc-local-id → global-id}` map and rewrite every `prior_refs` entry through it. Drop any `prior_refs` entry that doesn't resolve (silently — extractor hallucinations shouldn't fail the ingest) and log the count.
   4. Unified second pass to extract `nouns` consistently across all Notes from the doc
   5. Generate `document_summary` Note covering the whole doc (assign its `id` after step 3's numbering so it doesn't perturb Note indexing)
   6. Compute each Note's `source_hash` per the rule in §5
   7. Embed each Note's `text`
   8. **Stage-then-swap** (atomicity): insert new Notes with `id` prefixed `staging-<doc-id>-…`. After all staging rows land, run a single transaction: delete final-id rows where `document_id == <doc-id> AND id NOT LIKE 'staging-%'`, then update staging rows' `id` to final form. If the process dies before the swap, staging rows are orphaned but recoverable (no gap in live Notes for the doc).
4. After all docs processed in the run, build/refresh indexes: vector index on `embedding`, BM25 FTS index on `text` (`create_fts_index("text", replace=True)`)
5. Rebuild `documents.parquet` from the current doc set and captured heading hierarchies (§5.2), then rebuild `lancedb/stats.json` (doc counts by kind, top-k nouns, date range, last-ingest timestamp — the payload `corpus_stats()` reads in §7.2). Both are cheap aggregates over current Note / source state; full rebuild per run avoids incremental-bookkeeping bugs and stays under a second at v1 scale.
6. Append a structured log entry to `logs/ingest-<ts>.jsonl` per doc (status, note count, errors)

**Failure handling:** per-doc failures are logged and skipped; ingest continues. A final summary reports successes / skips / failures. Partial failures within a doc (one segment fails) → log + retry once + fall back to a single minimal Note covering the full segment if retry fails.

**Staging cleanup:** at the start of every ingest run, delete any rows with `id LIKE 'staging-%' AND created_at < now() - 1h`. One hour is a generous ceiling for a legitimate in-flight extraction; anything older is crash debris.

### 6.4 Single-file / prose / Mode A / Mode B / remember flows

All converge to "write a canonical doc to `sources/<id>.md` then run §6.3 step 3 on it":

- **Single-file with frontmatter:** use frontmatter as-is
- **Single-file without frontmatter:** synthesize `id = mem-<sha8>`, `title = filename or first heading`, `kind = note`, `date = today`, `author = config`
- **Prose-only:** synthesize `id = mem-<utc-timestamp>`, `title = first line if short else "Memo <ts>"`, `kind = note` (agent may suggest more specific)
- **Mode A (file + prose):** copy file as asset; prose becomes body; frontmatter `original_asset = <asset-id>`
- **Mode B (decompose):** agent uses native Read on the binary, emits canonical markdown to a temp file (instructions in §6.6), then ingests; original binary stored as asset; `original_asset` set
- **Remember (context-assembled):** agent drafts a canonical doc from conversation context, **always** shows draft for user confirmation, only writes after explicit approval

### 6.5 Note extraction prompt (the single biggest quality lever)

Lives at `{SKILL_DIR}/prompts/extract_notes.md`. Inputs: a segment of canonical markdown plus the doc's frontmatter. Outputs: a JSON list of Notes for that segment.

Prompt requirements (to be tuned):

- Define each `kind` value with examples
- Enforce decontextualization: pronouns resolved, proper nouns inlined, no dependence on surrounding context
- One Note per atomic claim/decision/etc. — split aggressively
- Source-ground: each Note declares its paragraph range within the segment
- Find explicit cross-references in the source and record them as `prior_refs` (using doc-local note IDs that get rewritten to global IDs post-hoc)
- Promote frontmatter `tags` into the `nouns` of every Note from this doc
- For Mode B docs: extraction prompt sees the canonical markdown, which is already prose-only (math/figures described, not transcribed)

A separate prompt at `{SKILL_DIR}/prompts/extract_nouns.md` runs after Note extraction across all Notes from a doc, producing a unified noun vocabulary (deduped, normalized casing) so that filter-by-noun is consistent.

A third prompt at `{SKILL_DIR}/prompts/document_summary.md` produces the doc-level `document_summary` Note.

### 6.6 Mode B PDF/image extraction

Prompt at `{SKILL_DIR}/prompts/decompose_binary.md`. Instructs the agent to:

- Read the binary directly via Claude's native multimodal Read
- Output canonical-format markdown (with frontmatter)
- For mathematical content: describe in prose what the math establishes, do **not** transcribe LaTeX or notation
- For figures/charts/diagrams: describe what is shown, what the axes mean, what conclusion the figure supports — do not attempt to reproduce the image
- For tables: render as markdown tables only if they fit cleanly; otherwise describe in prose
- Preserve section structure (headings) so segmentation works
- Set `kind` based on content (paper, report, etc.)
- Set `original_asset` to the binary's asset id (computed before the call)

The output file goes to `sources/<id>.md` and the standard ingestion pipeline runs.

**Provenance trade-off (accepted for v1):** `source_refs` index the canonical markdown, not PDF page numbers. The original PDF lives in `assets/`; user can fetch it any time via the `original_asset` link, but searchable provenance is markdown-paragraph-level only.

### 6.7 Embeddings (MLX-native)

**Backend:** `mlx-embeddings` (`blaizzy/mlx-embeddings`), running on Apple Silicon via the MLX framework. Chosen over PyTorch/MPS (`sentence-transformers`) and ONNX/CoreML (`FastEmbed`) because on M-series hardware MLX is the fastest native path, and memhound is a Mac-only skill.

**Model:** `mlx-community/mxbai-embed-large-v1` (bf16), 1024-dim, 512-token context. BERT-family. Weights auto-downloaded to `~/.cache/huggingface/` on first use (~670 MB).

**What gets embedded:** Note `text` only — never whole documents. Atomic Notes rarely exceed a few sentences, so 512 tokens is ample and long-context embedders would be wasted here. Queries are embedded at search time by the same model.

**Apple-blessed path caveat:** Apple publishes MLX and `mlx-lm` but no first-party embedding library. `mlx-embeddings` is the community de facto standard — SKILL.md should state this openly so the user isn't surprised by the lack of an Apple-branded dep.

**LanceDB integration:** a custom embedding function is registered against LanceDB's embedding registry so `SourceField`/`VectorField` and auto-embed-on-search still work. Implementation lives at `{SKILL_DIR}/scripts/embedder.py`:

```python
from lancedb.embeddings import TextEmbeddingFunction, register
from mlx_embeddings import load, generate
import numpy as np

@register("mlx")
class MLXEmbedder(TextEmbeddingFunction):
    name: str = "mlx-community/mxbai-embed-large-v1"
    max_length: int = 512
    # FIXME at implementation: TextEmbeddingFunction is Pydantic-based, so
    # _model/_tokenizer are treated as model fields, not private state.
    # Use pydantic.PrivateAttr (or module-level lazy cache keyed by `name`)
    # and confirm the registry round-trips through model_dump/model_validate.
    _model: object = None
    _tokenizer: object = None
    _dim: int = 1024

    def ndims(self) -> int:
        return self._dim

    def generate_embeddings(self, texts: list[str]) -> list[np.ndarray]:
        if self._model is None:
            self._model, self._tokenizer = load(self.name)
        out = generate(
            self._model, self._tokenizer,
            texts=list(texts),
            padding=True, truncation=True, max_length=self.max_length,
        )
        return [np.asarray(v) for v in out.text_embeds]
```

Schema wiring (extends §5):

```python
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector

embedder = get_registry().get("mlx").create(
    name="mlx-community/mxbai-embed-large-v1",
    max_length=512,
)

class Note(LanceModel):
    id: str
    text: str = embedder.SourceField()
    embedding: Vector(embedder.ndims()) = embedder.VectorField()
    # ...other columns per §5
```

### 6.7.1 Warm-state daemon

Each `/memhound` invocation shells out via `uv run`, which starts a fresh Python process. Cold MLX + model load is ~3–5s; per-query inference on M-series is ~20ms. A grep loop of 5–10 rounds (§7.3) is the difference between tens of seconds of dead time and well under a second. To keep the loop interactive, embedding runs through a persistent daemon rather than being done inline in each CLI invocation.

**Architecture:**

- `scripts/embedder_daemon.py` — loads MLX + model once, listens on `~/.cache/memhound/<project-slug>/embed.sock`, speaks line-delimited JSON: `{"op": "embed", "texts": [...]}` → `{"vectors": [[...], ...]}`. Idle timeout 15 min (configurable via `memhound.toml [embedding].daemon_idle_seconds`).
- `scripts/embedder_client.py` — thin client that connects to the socket, sends a request, returns the vectors.
- `scripts/embedder.py` (§6.7) keeps its registered shape as the LanceDB embedding function, but its `generate_embeddings` delegates to the client instead of calling `mlx_embeddings.generate` directly. The LanceDB integration is unchanged — the registry round-trip, `SourceField`/`VectorField`, and auto-embed-on-search all stay the same.
- **Auto-start.** The client connects; on `ConnectionRefusedError` it double-forks a new daemon, writes its PID to `~/.cache/memhound/<project-slug>/daemon.pid`, and retries once. No explicit user action required.
- **Fallback.** If spawn fails (sandboxed environment, no socket permissions, etc.), the client falls back to in-process embedding. The daemon is an optimization, not a hard dependency; skill correctness does not depend on it.
- **Cache.** The daemon keeps an in-memory LRU keyed by `sha256(text)` → vector, sized for the current session. The §7.4 fallback ladder re-embeds the same text repeatedly (e.g., retrying with `nouns=None` or `fuzziness=2`), so this cache is load-bearing for loop latency.
- **Lifecycle.** `/memhound daemon status|stop|restart` as an admin subcommand. Idle-timeout is the default shutdown path; explicit stop is only needed when swapping embedding models.

**Project-scoped sockets.** Socket path is keyed by a hash of the project directory so multiple projects can run simultaneously without cross-project cache pollution.

**macOS-only.** Matches MLX's scope. A non-Apple-Silicon port would need a CUDA/CPU fallback embedder and a different daemon invocation; out of scope for v1.

### 6.8 Forget flow

`/memhound forget <doc-id>` removes a doc and its derived state atomically enough that a crash mid-delete leaves the project in a recoverable state.

1. **Confirm with the user.** Show `{id, title, kind, date, note_count}` and require explicit confirmation before any destructive action. `--yes` skips the prompt for scripted use.
2. **Delete Notes.** `DELETE FROM notes WHERE document_id = '<doc-id>'` in a single transaction. Log the deleted count.
3. **Remove the source file.** `sources/<doc-id>.md` → unlink.
4. **Prune orphaned assets.** For each asset referenced by the removed doc (from the doc's body scan or `assets-manifest.parquet`'s `referenced_by` column): if the asset is no longer referenced by any surviving doc, unlink the asset file and drop its manifest row. Shared assets stay.
5. **Rebuild derived state.** Regenerate `documents.parquet` and `lancedb/stats.json` per §6.3 step 5. Rebuild the FTS index (`create_fts_index("text", replace=True)`) only if the deleted Notes were a material fraction (>5%) of the corpus; otherwise LanceDB's index handles tombstones fine.
6. **Log.** Append a `{op: "forget", doc_id, note_count, assets_pruned, ts}` entry to a new `logs/forget-<ts>.jsonl`.

**Crash recovery.** If the process dies between steps 2 and 5, the next ingest run's §6.3 step 5 full-rebuild of `documents.parquet` and `stats.json` restores consistency; orphaned assets get caught by a sweep on the following forget or a `/memhound gc` (future). Deletion is idempotent — re-running `/memhound forget` on an already-missing doc is a no-op with a warning.

**Scope.** v1 deletes exactly one doc per invocation. Bulk deletion (by kind, date range, glob) is deferred — the common case is "I put this in by mistake" or "this doc is obsolete," which is always one id.

## 7. Navigation pattern

### 7.1 Activation

Only `/memhound <input>` triggers the skill. No phrase-based implicit activation. SKILL.md description states this explicitly so Claude doesn't auto-load on "what did I write about X" without the slash command.

### 7.2 Retrieval primitives

Implemented as Python scripts the agent invokes via Bash. The headline primitive is `find`, which runs **hybrid search** — semantic (vector) + keyword (BM25) + fuzzy matching — combined by a reranker.

- `find(text=None, nouns=None, filters=None, mode="hybrid", fuzziness=None, limit=20) → {hits: [...], total_count: int}`
  - `mode`:
    - `"hybrid"` (default) — `table.search(text, query_type="hybrid", fts_columns="text").rerank(<configured reranker>)`. Combines vector similarity over `embedding` with BM25 over `text`.
    - `"vector"` — pure semantic search (escape hatch for when keywords hurt).
    - `"fts"` — pure BM25 with fuzzy matching. Uses `MatchQuery(text, "text", fuzziness=<resolved>)` so that typos and near-matches still hit.
  - `fuzziness` — per-call override of `[search].fuzziness`. Applied in `fts` mode and to the FTS arm of `hybrid` mode. `0` forces exact matching.
  - `nouns` → list-contains filter over `nouns` column (pre-filter applied to both arms).
  - `filters` → arbitrary column predicates (`kind`, `document_kind`, date range, author, doc_id) pushed down as a LanceDB `where` clause so both vector and FTS arms see the same candidate set.
  - Returns `{hits: [...], total_count, query_nouns, coverage}`. Each hit carries `id`, `text`, `kind`, doc metadata, `source_refs`, a combined `score`, and per-arm `_vector_score` / `_fts_score` when available. `query_nouns` is the list of nouns extracted from the query by the same logic as §6.5's noun pass. `coverage` is `{nouns_matched_in_top_k: int, nouns_total: int, hits_per_matched_noun: {noun: int}}` — a structural "have I found enough" signal the agent uses in §7.4 to decide between stopping and broadening.
- `fetch(document_id, paragraph_range=None) → string`
  - Returns text from `sources/<document_id>.md` for the given paragraph range, or whole doc if range is None
- `fetch_asset(asset_id) → path`
  - Returns the local file path for the asset; agent then reads with native tools
- `corpus_stats() → dict`
  - Reads `lancedb/stats.json`. Returns `{doc_count, note_count, date_range, kinds: [{kind, count}], top_nouns: [{noun, count}], last_ingest_at}`. Refreshed by ingest (§6.3 step 5). Cheap session-opener — agent reads this before the first `find` to know what shape the corpus actually has.
- `list_doc_kinds(min_count=1) → [{kind, count}]`
  - Group-by on `document_kind`. Scan of the Notes table (cheap at v1 scale).
- `list_nouns(limit=50, min_count=3, doc_kind=None, since=None) → [{noun, count, example_doc_ids}]`
  - Explode the `nouns` column, group, count, with optional filters. Useful when the agent is forming a first query and wants to see which nouns actually appear in the corpus (vs. guessing based on the user's wording).
- `list_docs(kind=None, since=None, until=None, author=None, limit=100) → [{id, title, kind, date, author, note_count}]`
  - Filter over `documents.parquet`. Session-opener for "what docs are in this corpus."
- `outline(document_id) → {id, title, kind, paragraph_count, note_count, outline: [{level, heading, paragraph_range, note_count}]}`
  - Reads `documents.parquet` (§5.2). Lets the agent orient inside a long doc — "hit was in §3 of 7; adjacent sections start at ¶45 and ¶78" — before deciding whether to fetch section-level or paragraph-level source.
- `neighbors(note_id, direction="both", depth=1, limit=50) → [{note, direction, distance}]`
  - `direction="out"`: follow this Note's `prior_refs` (`SELECT * FROM notes WHERE id IN <prior_refs>`).
  - `direction="in"`: Notes whose `prior_refs` contain `note_id` (`array_contains(prior_refs, note_id)`).
  - `depth > 1`: BFS, deduped, with `distance` recording hop count.
  - First-class traversal for the cross-reference walk in §7.3 step 4.

**Reranker choice:** configured in `memhound.toml [search].reranker`. Default is RRF (Reciprocal Rank Fusion) — no tuning knobs beyond `rrf_k`, robust across query shapes. `linear` is available when the user wants explicit semantic-vs-keyword weighting.

**Why fuzzy matters here:** users searching personal notes mistype proper nouns, mix capitalization, and half-remember terms. BM25 alone punishes this; hybrid + fuzzy FTS recovers it without needing vector search to do all the work.

### 7.3 The grep loop

The agent (Claude in the current session) drives navigation:

1. Read the question. **If this is the first `/memhound` query of the session**, call `corpus_stats()` (and `list_doc_kinds()` / `list_nouns(limit=30)` if stats leave gaps) to orient on what the corpus actually contains. Skip orientation on subsequent queries in the same session — it's a one-time tax, not per-query.
2. Form initial `find` query (text + likely nouns, `mode="hybrid"`)
3. Inspect hits; if total_count is huge, narrow with `filters` or `nouns`; if too narrow, broaden (drop filters, bump `fuzziness`, or try `mode="vector"` for conceptual queries / `mode="fts"` for known exact phrasing). If a hit lands deep in a long doc, call `outline(doc_id)` before `fetch` to decide whether to pull a paragraph range or a whole section.
4. Fetch source paragraphs for promising hits
5. Iterate: refine queries based on what surfaced, follow `prior_refs` cross-references via `neighbors(note_id)`
6. When confident, compose the answer

Mode-switching heuristic the agent should follow: **hybrid is the default**; fall back to `vector` when the user's question is abstract/conceptual and keyword overlap with the corpus is unlikely; fall back to `fts` (with `fuzziness=0`) when the user quotes a specific phrase or cites an exact term and wants literal recall.

The substrate stays simple; complexity lives in agent reasoning.

### 7.4 Fallback ladder

When a query doesn't immediately surface useful hits, the agent applies the following steps **in order**, stopping as soon as a step yields a usable hit set. Each step is attempted **at most once** — if the full ladder still returns nothing, the agent reports "no matches" rather than grinding.

1. **Initial query.** `mode="hybrid"`, `text=<question>`, `nouns=<entities/concepts extracted from the question>`, default `fuzziness` from `memhound.toml [search]`.
2. **Literal-phrase augmentation.** If the user's question contains a quoted phrase, run that phrase additionally as `mode="fts", fuzziness=0` and merge into the hit set. Quoted text is a signal the user wants literal recall.
3. **If `total_count == 0` after step 1:**
   1. Retry with `nouns=None` (drop noun pre-filter — common failure mode is over-specific nouns).
   2. Still zero → retry with `fuzziness=2` (catches typos, transliteration variants, missing/extra hyphens).
   3. Still zero → retry as `mode="vector"` (semantic-only; useful when the corpus doesn't use the user's wording).
4. **If `total_count` is large (>50) and hits look noisy / low-scoring:** narrow with `filters` (`document_kind`, date range, author, or specific `document_id`) before fetching sources. Don't fetch indiscriminately.
5. **Conceptual-query augmentation.** If the question is abstract and step 1's hits look keyword-skewed (all hits cluster on the same surface term, low semantic variety), add a parallel `mode="vector"` call and merge.

**Stopping rule:** the ladder is for *discovery*, not *confirmation*. Once a step returns a plausible hit set — or `find`'s `coverage` shows most of the query's nouns surfaced in top-k — move on to `fetch` and source review. Don't keep climbing the ladder looking for more hits.

**Why this lives in the agent, not in `find`:** the substrate has no view on what "noisy," "conceptual," or "plausible" mean for a given question. The agent does. Keeping the ladder prose-level also means we can tune it by editing SKILL.md / §7.4 rather than cutting a new `find` release.

### 7.5 Output format

Default: natural prose with **inline citations** in the form `[<doc-id> ¶<n>]` or `[<doc-id> ¶<a>–<b>]`, and a **Sources** section at the end listing each cited doc with title and date:

```
The migration was deferred until Q3 because the dependency on the auth rewrite [proj-x ¶12]
made an earlier cut-over risky [meeting-2024-02-14 ¶3–5].

Sources:
- proj-x — "Project X plan" (2024-01-30)
- meeting-2024-02-14 — "Planning sync" (2024-02-14)
```

### 7.6 Process narration

Quiet by default — the agent answers without showing the grep loop. If the user appends `--trace` to the invocation or includes phrases like "show your work" / "show me how you found that," the agent narrates each `find` / `fetch` step.

## 8. Introspection feature

### 8.1 Trigger

`/memhound introspect` and natural-language synonyms inside the `/memhound` namespace (e.g., `/memhound that was rough, what would have helped`, `/memhound reflect on the last query`).

### 8.2 Scope

Reflects on the **most recent query in the current session**. (Multi-query introspection is out of scope for v1; if the user wants to introspect a specific earlier query, they re-ask it and then introspect.)

### 8.3 Content

The agent writes:

1. **Query summary** — one line describing what was asked
2. **What made it harder than it should have been** — concrete observation: missing schema field, weak extraction on a doc kind, retrieval pattern that took N rounds when 1 should have sufficed, etc.
3. **Suggested skill change** — actionable: prompt edit, schema extension, new filter, new retrieval helper
4. **Impact assessment** — `low | medium | high`, with a one-line justification

### 8.4 Storage gate

Only stored if `impact ≥ memhound.toml [introspection].impact_threshold` (default `medium`). Below-threshold introspections are still shown to the user but discarded — keeps the introspection log signal-rich.

### 8.5 Storage format

One markdown file per stored introspection:

```
introspections/<utc-timestamp>-<slug>.md
```

```yaml
---
id: insp-20260419-143052
created_at: 2026-04-19T14:30:52Z
impact: high
related_query: "Find decisions about auth migration"
---

## Observation
<what made it harder>

## Suggested change
<actionable description>

## Impact
high — <one-line justification>
```

### 8.6 Review

`/memhound review introspections` (and semantic synonyms like `/memhound can we review your introspections`) loads all stored introspections, summarizes by theme (e.g., "extraction misses N times across N introspections," "navigation could benefit from a date-range filter — N introspections"), and proposes prioritized changes. No automatic pattern detection — review is on demand only.

## 9. Skill file organization

```
memhound/
├── SKILL.md                          # entry point; activation conditions, command grammar, dispatch rules
├── README.md                         # human-readable
├── CLAUDE.md                         # dev/maintenance instructions for Claude
├── scripts/
│   ├── pyproject.toml                # uv-managed deps
│   ├── uv.lock
│   ├── memhound.py                   # CLI dispatcher: import, store, find, fetch, daemon, etc.
│   ├── ingest.py                     # canonical-format ingestion (§6.3); rebuilds documents.parquet + stats.json
│   ├── retrieval.py                  # find / fetch / fetch_asset (§7.2)
│   ├── orientation.py                # corpus_stats / list_doc_kinds / list_nouns / list_docs (§7.2)
│   ├── graph.py                      # outline / neighbors (§7.2)
│   ├── project.py                    # project resolution, config loading
│   ├── lancedb_store.py              # schema, table init, insert/update
│   ├── embedder.py                   # LanceDB-registered embedding function (§6.7); delegates to daemon
│   ├── embedder_daemon.py            # persistent MLX embedder process (§6.7.1)
│   ├── embedder_client.py            # socket client + auto-spawn for embedder_daemon
│   ├── assets.py                     # content-addressed copy, manifest IO
│   └── extract_call.py               # LLM call wrapper for extraction (uses anthropic SDK)
├── prompts/
│   ├── extract_notes.md
│   ├── extract_nouns.md
│   ├── document_summary.md
│   ├── decompose_binary.md
│   └── introspect.md                 # used by the agent in-session for introspection
├── references/
│   ├── canonical-format.md           # full spec of the import format
│   ├── note-schema.md                # full Note schema reference
│   └── grep-loop-pattern.md          # how the agent should navigate
└── tests/
    └── extraction_eval/              # §13: eval harness for extraction prompt
        ├── docs/                     # hand-picked canonical inputs
        ├── expected/                 # hand-labeled expected Notes per doc
        └── baseline.json             # last committed eval scores
```

The Logseq→canonical converter lives **outside** the skill at `/Users/rob/rob/repos/claude_tools/memhound-bootstrap/logseq_to_canonical.py`. It's a one-off script, not part of the skill surface, and keeping it out of `memhound/` prevents confusion about what ships as the skill.

`scripts/pyproject.toml` initial dependencies:

```toml
[project]
name = "memhound-skill"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "lancedb>=0.10.0",             # hybrid search (vector + BM25 FTS), native fuzzy via MatchQuery
    "mlx>=0.18.0",                 # Apple Silicon runtime (Apple-published)
    "mlx-embeddings>=0.1.0",       # community embedder on top of MLX (§6.7)
    "pyarrow>=15.0.0",
    "pydantic>=2.0.0",
    "anthropic>=0.40.0",
    "tomli>=2.0.0",                # for memhound.toml on py<3.11; ok on 3.12 via stdlib but pin for clarity
    "python-frontmatter>=1.0.0",
]
```

(Final dep list to be confirmed at implementation; embedding client choice is a deferred decision.)

## 10. Activation conditions

`SKILL.md` frontmatter — first draft, lock this in before implementation and iterate from usage:

```yaml
---
name: memhound
description: >-
  Source-grounded memory over a corpus of canonical markdown docs. Invoke
  ONLY on explicit /memhound commands: /memhound import, /memhound store,
  /memhound find, /memhound <prose>, /memhound decompose, /memhound remember,
  /memhound forget, /memhound introspect, /memhound review introspections,
  /memhound stats, /memhound daemon. Do NOT activate
  implicitly on phrases like "in my notes," "what did I write," "search my
  writing," "look in my references," or similar — the user must type the
  slash command. Use when the user has explicitly invoked /memhound. Do not
  use for general web search, ad-hoc file reading, or code-search tasks.
allowed-tools: >-
  Read, Glob, Write,
  Bash(uv run --project {SKILL_DIR}/scripts python *)
---
```

Two things that matter most in the description:

- **Name the phrases that must NOT trigger.** Claude's activation heuristics key off surface phrases, so listing them explicitly is load-bearing.
- **Put the command grammar inline.** Dispatch can happen without loading the body of SKILL.md.

## 11. Open questions / deferred decisions

1. **Embedding model.** Decided: `mlx-community/mxbai-embed-large-v1` (bf16), via `mlx-embeddings`. Revisit only if MTEB-on-our-corpus eval surfaces a materially better MLX-available alternative (e.g., ModernBERT-based embedders on `mlx-community`, or a Qwen3-Embedding variant if quality > speed on longer Notes).
2. **Reranker default.** RRF is the current call (parameter-free, robust). Revisit if eval shows a linear reranker with tuned weights outperforms on this corpus — or if a cross-encoder reranker (Cohere, bge-reranker) is worth the latency cost.
3. **Apple-first-party embedding library.** None exists as of 2026-04. If `ml-explore` ships an official embedding API (e.g., via `mlx-lm` `embed` subcommand), migrate to it — the swap point is `scripts/embedder.py`, nothing else in the skill cares.
4. **Segmentation strategy details.** Heading-based with paragraph fallback is the high-level call; exact thresholds (max segment length, min for splitting) tuned during prompt iteration.
5. **`logseq_to_canonical.py` Logseq quirks.** Block ref resolution edge cases (refs to deleted blocks, circular embeds), property mappings beyond `date`/`author`, journal date formats — handled iteratively when the bootstrap is run.
6. **Multi-source per project.** Architecturally supported (just run `/memhound import <dir>` multiple times pointing at different sources). No special config needed in v1.
7. **DOCX / HTML / EPUB Mode B.** Not in v1 — only PDFs and images via Claude's native multimodal Read. If needed later, route through `pandoc` or add Python parsers.

## 12. Explicit non-goals (v1)

- **No Question-Notes** that capture prior queries and answers (deferred to v2)
- **No automatic cross-Note link discovery** beyond `prior_refs` extracted from explicit source references
- **No grouping abstractions** (collections, tags-as-folders, etc.)
- **No agent reasoning storage** beyond the narrow introspection mechanism
- **No access control or multi-user**
- **No Logseq-aware code in the skill** — the converter is a separate one-off
- **No format-specific code in the skill** — everything is canonical markdown
- **No PDF coordinate-level provenance** — `source_refs` index canonical markdown only
- **No implicit activation** — `/memhound` is the only entry point
- **No automatic introspection** — explicit trigger only
- **No batched/parallelized extraction** — per-doc LLM calls; revisit if scale demands
- **No wipe-and-rebuild ingest on doc update** — content-hash-based incremental only
- **No in-place schema migration.** If a column is added post-v1, the rebuild path is: bump a `schema_version` in `memhound.toml`, drop the `notes` table, re-run `/memhound import` pointed at `sources/` (which is the authoritative corpus — LanceDB is a derived cache). Embedder cost is re-paid; extraction cost only re-paid if prompts also changed (source hashes still match).

## 13. Evaluation

The extraction prompt (§6.5) is called out as the single biggest quality lever; without a feedback loop, prompt edits are blind. v1 ships with a small, cheap harness.

### 13.1 Layout

```
memhound/tests/extraction_eval/
├── docs/
│   └── <case-name>.md           # canonical-format input (frontmatter + body)
├── expected/
│   └── <case-name>.yaml         # hand-labeled expected Notes for that doc
└── baseline.json                # last committed scores, for diff
```

Target: 10–20 cases covering each `kind` value, at least one Mode B-derived doc, at least one dense journal-style doc. A one-afternoon hand-labeling job; adequate signal, not a benchmark.

### 13.2 Metrics

The harness runs the current extraction prompt on each `docs/<case>.md` and computes three numbers per case, then averages:

- **Coverage.** For each Note in `expected/<case>.yaml`, check whether any produced Note has cosine similarity > 0.8 (via the skill's configured embedder). Coverage = matched / expected.
- **Decontextualization.** Regex/heuristic pass over produced `text` fields: flag leading pronouns ("It", "This", "That", "They") and bare definite noun phrases ("the plan", "the project", "the team") with no proper noun earlier in the sentence. Score = 1 − flagged / total.
- **Noun consistency.** For each doc, group produced `nouns` by case-folded form; score = 1 − (distinct casings per group, minus 1) / total nouns. A doc that surfaces "Project X" / "project x" / "ProjectX" loses points.

All three land in `[0, 1]`; no weighting — they're reported separately so a regression on one doesn't hide behind a gain on another.

### 13.3 Invocation

`/memhound eval` (hidden command, not listed in the main grammar for end users) runs the harness, prints per-case and aggregate scores, and diffs against `baseline.json`. `/memhound eval --update-baseline` overwrites the baseline after a prompt change that's judged to be an improvement.

### 13.4 When to run

- Before every commit that touches `prompts/extract_notes.md`, `prompts/extract_nouns.md`, or `prompts/document_summary.md`.
- Before bumping the `[extraction].model` in `memhound.toml`.
- Before promoting any introspection-suggested change from §8 into the skill.

Not a CI gate for v1 (LLM calls cost money), but the baseline-diff makes regressions loud when it is run.
