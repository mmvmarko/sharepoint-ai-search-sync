# Improving Vectorization Options

This document outlines practical strategies to gain more control over Azure AI Search **integrated vectorization** when the native feature abstracts away low‑level embedding parameters. It presents an escalation path: start with non-invasive optimizations, then introduce controlled customization, and finally augment or partially replace integrated vectorization when needed.

---
## 1. Levers Still Available With Integrated Vectorization
Even though the embedding call is managed, you can still shape quality by influencing:
- The **text surface** (clean vs noisy input)
- **Chunk boundaries** (semantic cohesion improves retrieval)
- **Index schema** (multiple vector fields, hybrid configs)
- **Query strategy & reranking** (fusion, semantic ranker)

> 70–80% of retrieval lift usually comes from cleaner chunks + better segmentation.

---
## 2. Pre‑Processing & Text Hygiene
| Goal | Action | Implementation Pattern |
|------|--------|------------------------|
| Remove noise | Strip headers/footers/nav, legal footers, SharePoint boilerplate | Preprocess in `sharepoint_sync.py` before upload or custom Web API skill |
| Preserve meaning | Split on headings (H1–H3), slides, paragraphs/pages | Local splitter producing multiple logical documents |
| Normalize tables | Convert to Markdown or compact key:value text | Lightweight parser; avoid raw grid dumps |
| Avoid redundant versions | Hash normalized text & skip if unchanged | Store hash in state file (`delta_state.json`) |
| Control file types | Filter out binary artifacts w/ no text value | MIME/type gate before staging |

---
## 3. Chunk Size & Overlap Strategy
| Aspect | Recommendation |
|--------|---------------|
| Target size | 400–1200 tokens (≈ 1.5–5 KB text) |
| Overlap | Only if narrative continuity matters (copy last paragraph) |
| ID schema | `originalId#chunk-<n>` + fields: `parentId`, `chunkIndex` |
| Balance | More chunks → recall ↑ cost ↑; fewer chunks → precision risk |

Add metrics: 90% of chunks within ±20% of target length.

---
## 4. Index Schema Enhancements
| Technique | Description | Benefit |
|-----------|-------------|---------|
| Multi-vector fields | `contentVector`, `summaryVector`, `titleVector` | Different semantic granularity |
| Parent/child linkage | `parentId` + `chunkIndex` | Reconstruction & citation formatting |
| Categorical filters | e.g., `category`, `department` | Pre-filter reduces candidate set |
| Rich metadata | `docType`, `sourceSite`, `permissions` | Security trimming + analytics |
| Alias pattern | Blue/green swap (e.g., `spo-active`) | Zero-downtime schema upgrades |

> Immutable changes (vector dimensions, field type) require rebuild.

---
## 5. Dual-Level / Layered Embeddings
Introduce a **summary embedding** alongside the full-text embedding:
1. Summarize each chunk (LLM or custom skill).
2. Embed summaries into `summaryVector` (short, topic-focused).
3. Two-pass retrieval:
   - Coarse filter on `summaryVector` (k=50)
   - Refine / rerank on `contentVector` (+ lexical)

This reduces noise and boosts alignment for thematic queries.

---
## 6. Hybrid & Query-Time Optimization
| Lever | How to Apply | Outcome |
|-------|--------------|---------|
| Hybrid search | Combine vector + keyword query | Balanced precision/recall |
| Dynamic k | Start k=50 vector → rerank to top 10 | Latency control |
| Client fusion | 0.6 * vectorScore + 0.4 * bm25 | Stabilize relevance |
| Semantic ranker | Enable semantic config post-candidate set | Better natural ranking |
| Filtering first | `filter=category eq 'HR'` before vector | Faster & cleaner candidates |

Add clustering of final hits (cosine ≥ 0.93) to remove duplicates before LLM grounding.

---
## 7. Advanced Content Routing
| Content Type | Strategy |
|--------------|----------|
| Policy PDFs | Heading segmentation + page fallback |
| PPT | Slide-level per chunk; include slide title |
| Tables | Convert to vertical key:value lines |
| OCR-heavy scans | Keep OCR text separate; optionally exclude from primary vector field |
| Highly structured forms | Extract structured JSON → flatten into normalized text |

---
## 8. Embedding Drift Monitoring
Maintain resilience when the embedding model updates under the hood:
- Store `embedding_model_version` (your label) in each document.
- Keep a **stability set** (sample of canonical chunks); recompute cosine similarity monthly.
- Trigger re-vectorization pipeline if mean similarity drops below threshold (e.g., 0.92 baseline → 0.87 current).

---
## 9. Observability & Quality Metrics
| Metric | Purpose | Collection Idea |
|--------|---------|-----------------|
| Chunks/doc distribution | Detect over/under splitting | Log histogram at ingestion |
| Top-k coverage | % queries with relevant in top-k | Golden set eval script |
| Dead chunks | Chunks never surfaced in k=50 | Query logs frequency analysis |
| Drift score | Track embedding shift | Stability set comparisons |
| Latency buckets | Triage slow queries | Timer around vector + hybrid phases |

Add a `evaluate_retrieval.py` harness with NDCG@10 & MRR.

---
## 10. When to Partially Exit Integrated Mode
Leave some fields managed, add **custom embeddings** when you need:
| Trigger | Augmentation Path |
|---------|-------------------|
| Domain jargon poorly handled | Domain glossary expansion preprocessor |
| Need code/math semantic accuracy | Custom tokenizer + external embeddings |
| Multi-modal cues (image + text) | Separate vector field from vision encoder |
| Need late interaction (ColBERT) | Standalone retrieval service parallel to integrated |

Hybrid pattern: Integrated for baseline; beta index for experimental vectors → A/B evaluate.

---
## 11. Blue/Green Evolution Pattern
1. Current: `idx-spo-v1` (live)
2. Build: `idx-spo-v2` (new chunking + summaryVector)
3. Dual population period (shadow queries)
4. Compare metrics (precision@5, MRR, latency)
5. Flip alias: `spo-active → idx-spo-v2`
6. Retire `v1` after soak period

---
## 12. Actionable Starter Sprint (Suggested Order)
| Order | Task | Outcome |
|-------|------|---------|
| 1 | Implement splitter + cleaner | Higher semantic cohesion |
| 2 | Add parentId/chunkIndex fields | Traceability |
| 3 | Add summary generation + summaryVector | Layered retrieval |
| 4 | Hybrid + dynamic k client logic | Latency/relevance balance |
| 5 | Golden set + eval harness | Measurable progress |
| 6 | Logging: chunk + query stats | Feedback loop |
| 7 | Blue/green index rollout | Safe iteration |
| 8 | Drift monitoring script | Future stability |

---
## 13. Risk vs Reward Snapshot
| Lever | Effort | Risk | Expected Gain |
|-------|--------|------|---------------|
| Pre-cleaning | Low | Low | +Precision |
| Smart chunking | Medium | Low | +Recall & grounding |
| Multi-vector fields | Medium | Low/Med | Richer semantic signals |
| Dual-level retrieval | Medium | Medium | Higher answer quality |
| Client fusion rerank | Medium | Low | Better ordering |
| Evaluation harness | Medium | Low | Objective tuning |
| Blue/green strategy | Medium | Low | Safe experimentation |
| Custom embeddings add-on | Higher | Medium | Advanced domain fit |

---
## 14. Minimal Schema Field Additions (Example)
Proposed additive fields (safe update):
- `parentId` (Edm.String, filterable)
- `chunkIndex` (Edm.Int32, filterable/sortable)
- `summary` (Edm.String, searchable, retrievable)
- `summaryVector` (vector field, same dimensions as model)

> If adding a second vector field, ensure vector configuration allows multiple vector fields (most recent API versions do).

---
## 15. Suggested Supporting Utilities
| File | Purpose |
|------|---------|
| `preprocess.py` | Clean + split + emit chunk docs |
| `evaluate_retrieval.py` | Golden set scoring (NDCG/MRR) |
| `metrics_logger.py` | Collect ingestion/query stats |
| `drift_monitor.py` | Stability set similarity analysis |

---
## 16. Summary
You can materially influence integrated vectorization quality without abandoning it by **owning the text pipeline, chunk granularity, multi-vector semantics, and query orchestration**. Progress is unlocked fastest by: (1) cleaning & chunking, (2) adding a summary vector, (3) instituting evaluation metrics, and (4) safely iterating via blue/green indexing.

---
**Next:** Let me know if you want me to scaffold any of the helper scripts or modify your existing index setup code to add new fields.
