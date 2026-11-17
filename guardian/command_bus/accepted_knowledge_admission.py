"""Private catalog and delivery seams for the owning chat loop; not mounted."""

from dataclasses import asdict
from copy import deepcopy
import math
import time

from guardian.command_bus.accepted_knowledge_invoke import (
    _BoundedDB,
    _canonical_payload,
)
from guardian.command_bus.accepted_knowledge_manifest import (
    private_knowledge_commands,
    with_private_knowledge_commands,
)
from guardian.command_bus.accepted_knowledge_read import (
    AcceptedKnowledgeReadUnavailable,
    prepare_accepted_knowledge_read,
)
from guardian.command_bus.accepted_knowledge_transport import _authority
from guardian.command_bus.contracts import InvokeArguments, InvokeRequest
from guardian.command_bus.invoke import _accepted_policy_denial, _accepted_replay
from guardian.command_bus.manifest import build_command_index
from guardian.command_bus.store import CommandBusStore
from guardian.connections import chat_pilot, knowledge_oauth, oauth_store
from guardian.core.chat_account_custody import (
    ChatAccountAcceptancePending,
    resolve_accepted_chat_catalog_account,
)


async def project_accepted_knowledge_tools(*, db, task, grants):
    """Project metadata using current accepted custody and explicit policy.

    grants is a trusted server-resolved sequence of InvokeRequest policy templates,
    never model/queue/client permissions. No credentials or provider data are read.
    Returned descriptors are not execution authority or persistent capabilities.
    """
    if not knowledge_oauth.enabled() or not chat_pilot.enabled():
        return []
    scoped = _BoundedDB(db)
    try:
        initial = await _authority(
            lambda: resolve_accepted_chat_catalog_account(scoped, task)
        )
        templates = {}
        for grant in grants:
            if (
                not isinstance(grant, InvokeRequest)
                or grant.command_id not in chat_pilot.COMMANDS
                or grant.command_id in templates
                or len(templates) >= len(chat_pilot.COMMANDS)
            ):
                raise ValueError("accepted_knowledge_catalog_unavailable")
            templates[grant.command_id] = grant.model_copy(deep=True)
        projected = []
        observed = {}
        for command in private_knowledge_commands():
            template = templates.get(command.command_id)
            if template is None:
                continue
            provider = chat_pilot.COMMANDS[command.command_id][0]
            grant = await _authority(
                lambda: oauth_store.read_grant(scoped, initial.account_id, provider)
            )
            if provider in observed and grant != observed[provider]:
                raise ValueError("accepted_knowledge_catalog_unavailable")
            if (
                grant is None
                or (
                    grant.expires_at is not None
                    and (
                        not math.isfinite(grant.expires_at)
                        or grant.expires_at <= time.time()
                    )
                )
                or (provider == "github" and not grant.repositories)
            ):
                continue
            payload = _canonical_payload(
                template, {**asdict(initial), "provider": provider}
            )
            payload.arguments = InvokeArguments()
            if _accepted_policy_denial(payload, command, initial.account_id):
                continue
            descriptors = deepcopy(
                chat_pilot.project_tools([command], frozenset({provider}))
            )
            # Resource hints are current account metadata, never a provider grant.
            if provider == "github":
                descriptors[0]["input_schema"]["properties"] = {
                    key: dict(value)
                    for key, value in descriptors[0]["input_schema"][
                        "properties"
                    ].items()
                }
                descriptors[0]["input_schema"]["properties"]["repository"]["enum"] = (
                    list(grant.repositories)
                )
            projected.extend(descriptors)
            observed[provider] = grant
        # Re-read immediately before advertisement. No cached catalog authority.
        for provider, grant in observed.items():
            current = await _authority(
                lambda: oauth_store.read_grant(scoped, initial.account_id, provider)
            )
            if current != grant or (
                grant.expires_at is not None and grant.expires_at <= time.time()
            ):
                raise ValueError("accepted_knowledge_catalog_unavailable")
        if (
            not knowledge_oauth.enabled()
            or not chat_pilot.enabled()
            or await _authority(
                lambda: resolve_accepted_chat_catalog_account(scoped, task)
            )
            != initial
        ):
            raise ValueError("accepted_knowledge_catalog_unavailable")
        return projected
    except ChatAccountAcceptancePending:
        raise
    except Exception:
        raise AcceptedKnowledgeReadUnavailable(
            "accepted_knowledge_catalog_unavailable"
        ) from None


async def read_accepted_knowledge_result(*, db, task, payload, run_id, app):
    """Read durable completed evidence after a fresh delivery-authority check.

    Never executes a provider, decrypts credentials, creates a run or accepts a
    caller-provided result body. Use immediately before model delivery. This does
    not commit the assistant response or authorize any other read/tool step.
    """
    scoped = _BoundedDB(db)
    try:
        payload = payload.model_copy(deep=True)
        fence = await _authority(
            lambda: prepare_accepted_knowledge_read(
                scoped,
                task,
                command_id=payload.command_id,
                arguments=payload.arguments,
            )
        )
        lineage = await _authority(fence.lineage)
        canonical = _canonical_payload(payload, lineage)
        index, manifest = build_command_index(app)
        index = with_private_knowledge_commands(index)
        store = CommandBusStore(scoped)

        def read():
            run = store.get_run(run_id)
            if (
                run is None
                or run.get("auth_subject") != lineage["account_id"]
                or run.get("status") != "completed"
                or run.get("result_json") is None
            ):
                raise AcceptedKnowledgeReadUnavailable(
                    "accepted_knowledge_result_unavailable"
                )
            response = _accepted_replay(
                fence=fence,
                run=run,
                payload=canonical,
                command=index[payload.command_id],
                subject=lineage["account_id"],
                store=store,
                provenance={"accepted_knowledge": lineage},
                manifest_version=manifest.manifest_version,
            )
            fence.revalidate()
            return response

        return await _authority(read)
    except ChatAccountAcceptancePending:
        raise
    except Exception:
        raise AcceptedKnowledgeReadUnavailable(
            "accepted_knowledge_result_unavailable"
        ) from None
