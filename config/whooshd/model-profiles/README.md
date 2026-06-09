# Whoosh'd Model Profiles

This directory contains data-only Whoosh'd local model profiles. Profiles describe local runtime expectations and acceptance gates for future MLX-backed model use.

A profile is not a routed provider. All profiles in this directory must keep `provider_id` as `local` unless a future ADR explicitly changes provider routing doctrine. Whoosh'd is display/vendor metadata under the current provider-governance contract.

Profiles describe runtime start hints, model-family notes, Guardian defaults, transcript leakage policy, acceptance checks, and release posture. They do not prove runtime support by existing.

Catalog/UI surfaces may expose profiles as selectable local model choices. The selected model id should remain the runtime model repo that the Whoosh'd/MLX server expects, while the profile id remains metadata for governance and acceptance tracking.

Live proof still requires health, catalog, supported-profile, queue/worker, and Guardian completion evidence. A profile must not be treated as release-supported until that separate proof exists and the release posture is updated through the normal architecture path.

New profiles must include thought/final-answer leakage policy when the model family supports hidden, analysis, thinking, or channelized output. Guardian-facing transcript output must reject prompt echo and hidden/process/channel leakage before any routed use.
