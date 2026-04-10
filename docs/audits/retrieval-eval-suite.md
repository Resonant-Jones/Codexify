# Retrieval Eval Suite

## Scope

This registry tracks the first executable retrieval evaluation pack for the supported Obsidian backend seam:

- Obsidian vault ingest through the current read-only rebuild path
- Chroma-backed vector storage
- `MemoryOSRetriever` retrieval normalization
- fixture-backed source identity and metadata exposure

It is intentionally narrow. It does not claim API, browser, federation, or generalized multi-source retrieval proof.

## Interpretation Rule

Treat each eval as a contract on the currently proven seam only.

- If the test says retrieval is stable, that means stable for the fixture corpus and supported ingest/retrieve path under the current backend settings.
- If the test says updated content wins, that means the rebuilt vector truth reflects the new file contents after re-ingest.
- If the test says no false hit, that means the retriever does not misrepresent an absent query as grounded evidence.

Do not extend these results into claims about future routing behavior, live sync, or unsupported lifecycle semantics.

## Retrieval Eval Table

| Eval | What it proves | What it does not prove | Test anchor | Release relevance |
| --- | --- | --- | --- | --- |
| Retrieval Eval A: Distinctive hit is retrievable | The distinctive fixture note is ingested, retrievable, and still carries visible source/path metadata through `MemoryOSRetriever`. | It does not prove broad semantic recall or cross-corpus ranking quality. | `test_retrieval_eval_distinctive_fixture_hit` | Confirms the supported ingest-to-retrieve seam still exposes an obvious known truth after packaging changes. |
| Retrieval Eval B: No false widening from absent query | An empty query stays empty and is not misreported as a grounded hit to the distinctive note. | It does not prove model quality on paraphrases or adversarial queries. | `test_retrieval_eval_absent_query_does_not_false_hit_distinctive_note` | Catches regressions where the retrieval layer starts fabricating evidence for absent input. |
| Retrieval Eval C: Re-ingest remains stable | Repeating the same supported ingest path keeps the source identity stable and returns the same note truth without duplicate retrieval identity. | It does not prove arbitrary incremental dedupe semantics or delete/move lifecycle handling. | `test_retrieval_eval_repeat_ingest_is_stable` | Guards against replay drift in the supported rebuild flow. |
| Retrieval Eval D: Updated content wins after re-ingest | After the fixture note changes and the vault is rebuilt, retrieval returns the updated content and new content hash rather than stale text. | It does not prove partial update semantics or live watch-based sync. | `test_retrieval_eval_updated_note_replaces_prior_content` | Verifies the release-critical truth that a fresh rebuild should surface the latest file contents. |

## Extension Notes

- Keep future evals anchored to a proven seam and name the seam explicitly.
- Do not upgrade this registry into a promise of live browser proof or runtime routing coverage unless the test actually exercises that path.
- If a new eval depends on a different backend mode, add a separate entry instead of widening the meaning of the current one.

