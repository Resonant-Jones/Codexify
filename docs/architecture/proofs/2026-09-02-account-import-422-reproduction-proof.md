# Account Import Multipart `422` Reproduction Proof

- Date: 2026-09-02
- Lane: `standard`
- Task kind: `proof`
- Evidence posture: `live-runtime proven`
- Repository HEAD at reproduction: `1a15805b5873305a4d179cdd5add4cb314ce1669`
- Runtime: repository-owned `codexify_private_preview` Compose project
- Verdict: **PASS — classification A, browser/frontend request-envelope specific**

## Conclusion

The real candidate files are not the cause of the `422`. The exact 25 files
immediately after the 1,799 files durably staged by Safari were replayed as
repeated `files` and `relative_paths` multipart parts through a disposable,
authenticated private-preview job. Nginx forwarded the 18.7 MB request,
FastAPI parsed both repeated fields, and Guardian durably recorded all 25 files
and all 18,687,149 declared bytes with HTTP `200`.

The failed Safari request reached Nginx and Guardian but did not carry a
parseable multipart envelope containing either required field. This is not a
generic importer failure and is not caused by the candidate file, path, batch
count, aggregate byte size, Nginx request-size handling, or Starlette/FastAPI's
ability to parse a valid version of this multipart body.

The smallest owning seam for the next repair is the browser request-envelope
construction/transport in `uploadOpenAIAccountImportBatch()` in
`frontend/src/lib/api.ts`, including its Axios/WebKit `FormData` interaction.
No repair was made in this proof task.

## Safety and scope

- `/Volumes/Dev_SSD/Account Exports` was used read-only.
- No export file was copied, renamed, normalized, reorganized, modified, or
  deleted.
- No conversation content was inspected or persisted. Inspection was limited
  to paths, filenames, sizes, filesystem entry order, MIME guesses, and the
  existing Guardian staging manifest.
- Existing import jobs and staged files were not changed or deleted.
- The replay used a new disposable job and left it in `receiving` state.
- No frontend, Guardian, Nginx, database, parser, queue, retry, or lifecycle
  implementation was modified.

## Source inventory and selected set

The supplied directory exists and was readable.

| Scope | Files | Bytes |
|---|---:|---:|
| `/Volumes/Dev_SSD/Account Exports` (all files) | 6,892 | 9,225,401,328 |
| `OpenAI-export` | 6,881 | 8,990,043,748 |
| Browser-selected six extracted export roots | 6,850 | 5,038,106,892 |

The 6,850-file declaration recorded by Guardian maps exactly to these six
visible extracted roots (dot-prefixed metadata files excluded):

| Extracted root | Files |
|---|---:|
| `workspace` | 948 |
| `workspace 3` | 655 |
| `conversations__...-part-0003` | 984 |
| `workspace 2` | 733 |
| `conversations__...-part-0001` | 2,024 |
| `__533c2b29-f445-4dd4-a5b5-e9dd81ccedac` | 1,506 |

The operator's earlier 1,506-file / 1,081.5 MiB observation maps exactly to
the final root above. The larger supplied parent also contains archive copies
and other exports; those were inventory context, not members of this failed
job.

A metadata-only manifest was generated under `/private/tmp`. It contained
relative path, filename, byte size, and MIME guess only. It was not committed
because it contains user-specific filenames.

## Browser ordering proof

The product does not sort the selected files:

- folder selection uses `Array.from(FileList)` and retains
  `webkitRelativePath` order;
- drag/drop recursively consumes each directory reader's native
  `readEntries()` order, and `Promise.all(...).flat()` retains input order.

Filesystem order alone was therefore not treated as proof. Ordering was
established by comparing a native, unsorted `os.scandir()` traversal against
the existing browser-produced `staged_manifest` for job
`1c6212ee-4fe4-4780-8ae5-cdd49d4bd1c9`:

- entries 1–1,506 exactly matched native order for
  `__533c2b29-f445-4dd4-a5b5-e9dd81ccedac` by relative path and byte size;
- entries 1,507–1,799 exactly matched the first 293 native-order entries of
  `conversations__...-part-0001`;
- the complete observed prefix matched 1,799 of 1,799 entries.

This is an empirical reconstruction from durable browser output, not an
alphabetical filesystem guess.

## Exact frontend batching contract

`uploadBatches()` currently uses:

- maximum 25 files per batch;
- target 32 MiB (`32 * 1024 * 1024`) per batch;
- a batch boundary before the next file when the current batch is non-empty
  and either limit would be exceeded;
- a file larger than 32 MiB as a one-file batch rather than splitting it.

Applying that exact algorithm to the proven ordering makes batch 72 the last
successful batch and batch 73 the first failing candidate.

The live database corrects the initial visual estimate that failure occurred
after 200 files: the job contains 1,799 staged files and 1,327,852,561 staged
bytes. Nginx records 72 successful batch uploads followed by the `422`.

## Previous successful batch — batch 72

- Ordinals: 1,775–1,799
- File count: 25
- Total bytes: 11,540,298
- Largest file: `file-QvcGehX6ojFqrG7PkgUvcN.dat` (2,154,354 bytes)
- MIME guesses: 25 `application/octet-stream`
- Zero-byte files: none
- Unusual properties: no spaces, non-ASCII text, non-NFC text, backslashes,
  or `..` path segments

All paths share this exact prefix:

`conversations__03ad57391cf037335881deeacc6bcfadbd67f7655ca312c9681db498e45ced23-chatgpt-0001-part-0001/__533c2b29-f445-4dd4-a5b5-e9dd81ccedac/`

The exact relative paths are that prefix plus, in order:

1. `file-2nEKqRD7CUdaqWS9rmNasN.dat`
2. `file-ViJ3CAKHQcNhBzzt7oC7kV.dat`
3. `file-FzBrC4QaejksbRCcjBKSYf.dat`
4. `file-2qx2gt7QKf9s3qbkWehWgP.dat`
5. `file-KL6bYSTcJXqvA1upzTxr7G.dat`
6. `file-8dEizLJdY5Y9vrmeisgLTP.dat`
7. `file-WngMRHbSC3vT7WsgNd5Hkg.dat`
8. `file-J5RfjVTqYboyDhfb37uU6W.dat`
9. `file-EPCjW94aLGbJcJ3tfp2g6p.dat`
10. `file-8FatNiMbhe67b5wopsiB1N.dat`
11. `file-J2rqdk3ZWjwqVxmFgU3yKA.dat`
12. `file-1DLewQYGVMtF1vwSrxTLmh.dat`
13. `file-QXFS9Jwox1AmgJcQGCbko9.dat`
14. `file-4RgDJ1gwvy3r8aVhRMsGGX.dat`
15. `file-CsyKLWkBeUaAPgEnmXQpY1.dat`
16. `file-NaVqp97ATppU4TXrX3AwXH.dat`
17. `file-4QaF3xZApqFncjTPYjqynR.dat`
18. `file-GNWnQhE6zp3jxrHkrjG9S6.dat`
19. `file-7iSXkaFLkqJWXRYF9N6Vta.dat`
20. `file-QvcGehX6ojFqrG7PkgUvcN.dat`
21. `file-72kZocvnvBzcTxvjzDG8bi.dat`
22. `file-N9y3rvw1CUXwNQx8HWV9q3.dat`
23. `file-YXQ1dV7gYqWMFh4KJ8Qz9v.dat`
24. `file-JFr2JbU9tq5XxrxmqbaR1v.dat`
25. `file-99uGQAUfvMmQc41LpTaZwA.dat`

## First failing candidate — batch 73

- Ordinals: 1,800–1,824
- File count: 25
- Total bytes: 18,687,149
- Largest file: `conversations-030.json` (10,394,174 bytes)
- MIME guesses: one `application/json`, 24 `application/octet-stream`
- Zero-byte files: none
- Unusual properties: no spaces, non-ASCII text, non-NFC text, backslashes,
  or `..` path segments

All paths use the same exact prefix recorded for batch 72. The exact relative
paths are that prefix plus, in order:

1. `file-72i6hQgufiR8a2XFBpptFE.dat`
2. `file-1EMxPNR3BbpZeYarBF9H7J.dat`
3. `file-U3b9ZTTFHxBdta6D5ULyVi.dat`
4. `file-GWPQrKswy6xLiXigFAnecr.dat`
5. `file-1FdcbupU4BtngBpnPMwxvo.dat`
6. `file-5aXd3SqsPzBNkqoWVtsZtc.dat`
7. `file-H4e1szKkJpiLvEXPY4Ckya.dat`
8. `file-68vAX2GzCBHhr7CoXCZBpv.dat`
9. `file-AtTv8r1S5KXH8cRawZ6ccp.dat`
10. `file-SuVVCfNbGtys4hymZ1MsjD.dat`
11. `file-3JyRk1fkD8F56hzG5PcTij.dat`
12. `file-9bAsPxHi3NPAyLh9Ar7iJt.dat`
13. `file-VktUEFVy5AV7HcuCqVak4y.dat`
14. `file-5QunpJPLUYGAn65CVd81qz.dat`
15. `file-B1k6p8gwFbf5XAzdi5cshc.dat`
16. `file-R9ugPmTCmd4aci3F7vqq1B.dat`
17. `file-9RKn4gRhBTNcwddhWGFa9o.dat`
18. `file-4Z323MHVXJMNq5EQn7kN7V.dat`
19. `file-75CTSCrN8F4jbHAm4bhKQj.dat`
20. `conversations-030.json`
21. `file-9q8M7EekfooDCxuVb4YjZk.dat`
22. `file-AmVhh1VEgVYSw8Ex8an8LD.dat`
23. `file_000000000004722fbd950490d192fcf3.dat`
24. `file-BJ2xuX9kfcVYMCX7ptkCKK.dat`
25. `file-Y6GgC7BLMWx3zERdsi8HmP.dat`

## Browser failure evidence

For the 6,850-file job, private-preview Nginx recorded:

- 72 successful Safari uploads (`HTTP 200`);
- a final successful upload at `2026-09-02 18:30:02 UTC`;
- the next upload at the same second as `HTTP 422`, response size 177;
- no redirect and no Nginx `413` for the failed request.

The supplied FastAPI response reports both required fields missing:

```json
{
  "detail": [
    {"type": "missing", "loc": ["body", "files"], "msg": "Field required", "input": null},
    {"type": "missing", "loc": ["body", "relative_paths"], "msg": "Field required", "input": null}
  ]
}
```

Each preceding large successful request produced Nginx's expected
`client request body is buffered to a temporary file` warning. The `422`
request did not. A valid batch 73 body is approximately 18.7 MB and does
produce that warning on direct replay. This is evidence that the failed Safari
request arrived at Nginx without the expected large multipart body, rather
than Nginx rejecting that body.

Two later Safari jobs declaring 2,024 and 984 files also received an upload
`422` before staging any file. That independent behavior further excludes one
particular candidate file or an ordinal-1,800 threshold.

The exact failed Safari request's `Content-Type`, boundary, `Content-Length`,
and transfer encoding were not retained by the current access-log format or
the now-navigated browser tab. No product instrumentation was added because
that would exceed this proof-only task. Accordingly, the evidence proves the
browser/frontend envelope boundary but does not yet distinguish an Axios
serialization defect from a WebKit transport defect or a Safari-specific
interaction with the public edge.

## Direct multipart replay

Disposable job: `9cd83ab5-a520-4107-add5-4bf2bdaa657a`

The replay used the repository-owned private-preview Nginx origin at
`127.0.0.1:8081`, the canonical slashless create endpoint, a short-lived
approved session, and the exact candidate files and relative paths. The
request consisted only of repeated multipart fields in the same shape as the
frontend:

- 25 `files` parts;
- 25 `relative_paths` parts;
- `Content-Type: multipart/form-data; boundary=<32-character boundary>`;
- `Content-Length: 18698131`;
- no `Transfer-Encoding` header;
- prepared body length: 18,698,131 bytes.

Observed receipts:

| Layer | Result |
|---|---|
| Create endpoint | HTTP `200`, no redirect |
| Nginx create receipt | `POST /api/imports/openai-account` → `200` |
| Nginx upload receipt | exact job `/files` path → `200`; body buffered to Nginx temp storage |
| Guardian response | HTTP `200`, JSON, request ID `req_bc3dd58515604519aabb381946dfde83` |
| Guardian database | `receiving`, 25/25 files, 18,687,149/18,687,149 bytes, manifest length 25 |

No bisect was warranted: the entire exact candidate batch passed unchanged.

## Classification matrix

| Candidate | Result | Evidence |
|---|---|---|
| A. Browser sends malformed/empty multipart | **Supported** | Safari request reached Guardian with neither field; expected large body was absent at Nginx; exact valid envelope succeeds |
| B. Intermediary removes an otherwise valid body | Not supported as a general server-path defect | The same Safari flow crossed the same public edge for 72 successful batches; Nginx accepts the direct valid body. Exact failed edge headers were not retained. |
| C. FastAPI/Starlette cannot parse valid multipart | Excluded | Exact candidate envelope parsed and staged 25/25 fields |
| D. Particular real file breaks serialization/server parsing | Excluded on the server path | Exact 25 real files, including `conversations-030.json`, replay successfully |
| E. Count/size/path/Nginx limit or another server-side importer condition | Excluded for this candidate | Same count, bytes, paths, Nginx route, Guardian route, and service succeed |

The operational classification is therefore **A: browser/frontend
request-envelope specific**. The narrower cause inside that boundary remains
to be captured before implementing a repair.

## Recommended next implementation seam

Use a separate frontend repair task focused on
`uploadOpenAIAccountImportBatch()` and Safari/WebKit. First pin a regression
that captures sanitized request-envelope facts (multipart media type, boundary
presence, body presence/size, and repeated-field counts) without logging paths,
filenames, content, or credentials. Then repair the smallest proven transport
seam—for example, if confirmed, allowing the browser to own the multipart
`Content-Type`/boundary or replacing only this upload call's Axios transport
with authenticated `fetch`.

Do not change batching, importer lifecycle, Nginx, Cloudflare, FastAPI fields,
or the outage fuse without new evidence.

## Validation record

- Required source searches: passed; constants, `FormData.append()` calls, and
  FastAPI `UploadFile`/`relative_paths` declarations match the contracts above.
- Read-only real-export inventory: passed.
- Browser-order comparison: passed, 1,799/1,799 durable entries matched.
- Exact candidate direct replay: passed, HTTP `200`, 25 files and 25 paths.
- Nginx receipt: passed, upload HTTP `200`, no redirect or `413`.
- Guardian durable receipt: passed, 25 files and 18,687,149 bytes staged.
- Conversation-content inspection: not performed.
- Importer implementation tests: not applicable; no runtime code changed.

## ADR impact

No ADR impact. This proof identifies a malformed browser request boundary and
does not change account-import semantics, authority, persistence, queueing, or
lifecycle state.
