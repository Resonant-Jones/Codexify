"""Same-node human solicitation and consent, backed solely by Postgres.

Pair locks serialize affirmative intent in both directions. Profile locks
serialize sender budgets and idempotency keys. No Guardian work is dispatched.
Public service entry points own one commit; materialization helpers only stage.
"""
from datetime import datetime, timedelta, timezone
import uuid

from sqlalchemy import func, or_, select, update

from guardian.db.models import (
    DirectMessage,
    DirectMessageConsent,
    DirectMessageConversation,
    DirectMessageConversationPlacement,
    DirectMessageRelationship,
    MessageRequest,
    MessageRequestAttempt,
    MessageRequestPreferences,
    MessageRequestSuppression,
    MessageRequestVisibility,
    UserProfile,
)
from guardian.messaging import service
from guardian.messaging.tokens import (
    DirectMessageConsentSource as ConsentSource,
    MessageRequestError as Error,
    MessageRequestState as State,
)


def _now():
    return datetime.now(timezone.utc)


def _error(status, code, message):
    return service._err(status, code.value, message)


def require_username(profile):
    if profile.username_state != "active" or not profile.username:
        raise _error(
            403,
            Error.USERNAME_REQUIRED,
            "Choose a username to discover People and send message requests",
        )


def _lock_profile(session, profile_id):
    return session.scalar(
        select(UserProfile)
        .where(UserProfile.profile_id == profile_id)
        # FOR NO KEY UPDATE still serializes this sender's budget/key writes,
        # while permitting FK KEY SHARE checks by the other initiator. Using
        # FOR UPDATE here deadlocks A/B reverse initiation across Profile FKs.
        .with_for_update(key_share=True)
        .execution_options(populate_existing=True)
    )


def _lock_pair(session, relationship_id):
    return session.scalar(
        select(DirectMessageRelationship)
        .where(DirectMessageRelationship.id == relationship_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def _expire(session, now, *predicates):
    # Conditional UPDATE locks the request rows, never reclassifies a terminal
    # attempt, and records the deadline rather than the time of this lazy sweep.
    session.execute(
        update(MessageRequest)
        .where(
            MessageRequest.state == State.PENDING.value,
            MessageRequest.expires_at <= now,
            *predicates,
        )
        .values(state=State.EXPIRED.value, transitioned_at=MessageRequest.expires_at)
        .execution_options(synchronize_session=False)
    )
    session.expire_all()


def _validated_attempt(note, key):
    if not isinstance(note, str) or not note.strip() or len(note.strip()) > 32000:
        raise _error(
            422,
            Error.INVALID_NOTE,
            "The introductory note must contain 1–32000 characters",
        )
    if not isinstance(key, str) or not key.strip() or len(key.strip()) > 128:
        raise _error(
            422, Error.INVALID_KEY, "A request key of 1–128 characters is required"
        )
    return note.strip(), key.strip()


def _materialize(session, request, relationship, now):
    """Only called under pair/request locks; never commits part of acceptance."""
    conversation = DirectMessageConversation(
        id=uuid.uuid4().hex,
        relationship_id=relationship.id,
        created_by_profile_id=request.sender_profile_id,
        kind="direct",
        created_at=now,
        latest_activity_at=now,
    )
    session.add(conversation)
    session.flush()
    for _, profile_id in service.relationship_participant_addresses(
        session, relationship
    ):
        session.add(
            DirectMessageConversationPlacement(
                id=uuid.uuid4().hex,
                conversation_id=conversation.id,
                profile_id=profile_id,
                project_id=None,
                created_at=now,
                updated_at=now,
            )
        )
    sender = session.scalar(
        select(UserProfile).where(UserProfile.profile_id == request.sender_profile_id)
    )
    first = DirectMessage(
        id=uuid.uuid4().hex,
        conversation_id=conversation.id,
        sender_node_id=sender.node_id,
        sender_profile_id=sender.profile_id,
        content_type="text/plain",
        body=request.note,
        client_message_key=f"request:{request.id}",
        created_at=now,
    )
    session.add(first)
    session.flush()
    request.state = State.ACCEPTED.value
    request.transitioned_at = now
    request.conversation_id = conversation.id
    request.first_message_id = first.id
    relationship.updated_at = now
    session.flush()
    if session.get(DirectMessageConsent, relationship.id) is None:
        session.add(
            DirectMessageConsent(
                relationship_id=relationship.id,
                source=ConsentSource.ACCEPTED_REQUEST.value,
                request_id=request.id,
                established_at=now,
            )
        )
    return conversation


def create_request(
    session,
    sender,
    destination_node_id,
    destination_profile_id,
    note,
    client_request_key,
):
    note, key = _validated_attempt(note, client_request_key)
    sender, recipient = service._resolve_local_peer(
        session, sender, destination_node_id, destination_profile_id
    )
    require_username(sender)
    # Only actively discoverable usernames can receive this username-based flow.
    # Historical conversations and future non-username addressing remain separate.
    if recipient.username_state != "active" or not recipient.username:
        raise _error(400, Error.UNAVAILABLE, "Unable to initiate this message request")
    if sender.node_id != recipient.node_id:
        raise _error(400, Error.UNAVAILABLE, "Unable to initiate this message request")
    relationship = service.resolve_or_create_relationship(
        session, sender, destination_node_id, destination_profile_id
    )
    sender_id, recipient_id, pair_id = (
        sender.profile_id,
        recipient.profile_id,
        relationship.id,
    )
    _lock_profile(session, sender_id)
    relationship = _lock_pair(session, pair_id)
    now = _now()
    _expire(session, now, MessageRequest.relationship_id == pair_id)
    existing_attempt = session.scalar(
        select(MessageRequestAttempt).where(
            MessageRequestAttempt.sender_profile_id == sender_id,
            MessageRequestAttempt.client_request_key == key,
        )
    )
    if existing_attempt is not None:
        if (
            existing_attempt.recipient_profile_id != recipient_id
            or existing_attempt.note != note
        ):
            raise _error(
                409,
                Error.KEY_CONFLICT,
                "This request key belongs to a different attempt",
            )
        result = session.get(MessageRequest, existing_attempt.request_id)
        session.commit()
        return result, True
    # Previously established pairs use ordinary Conversations. Reject a new
    # solicitation rather than manufacturing new acceptance provenance.
    if session.get(DirectMessageConsent, pair_id) is not None:
        raise _error(
            400,
            Error.UNAVAILABLE,
            "Unable to initiate this message request; open your existing conversation",
        )
    suppressed = session.get(MessageRequestSuppression, (sender_id, recipient_id))
    if suppressed is not None and suppressed.cleared_at is None:
        raise _error(400, Error.UNAVAILABLE, "Unable to initiate this message request")
    hourly = session.scalar(
        select(func.count())
        .select_from(MessageRequestAttempt)
        .where(
            MessageRequestAttempt.sender_profile_id == sender_id,
            MessageRequestAttempt.created_at > now - timedelta(hours=1),
        )
    )
    daily = session.scalar(
        select(func.count())
        .select_from(MessageRequestAttempt)
        .where(
            MessageRequestAttempt.sender_profile_id == sender_id,
            MessageRequestAttempt.created_at > now - timedelta(days=1),
        )
    )
    if hourly >= 10 or daily >= 50:
        raise _error(
            429, Error.RATE_LIMIT, "Please wait before sending another message request"
        )
    pending = session.scalar(
        select(MessageRequest)
        .where(
            MessageRequest.relationship_id == pair_id,
            MessageRequest.state == State.PENDING.value,
        )
        .order_by(MessageRequest.created_at, MessageRequest.id)
        .with_for_update()
    )
    own_suppression = session.get(MessageRequestSuppression, (recipient_id, sender_id))
    if own_suppression is not None and own_suppression.cleared_at is None:
        # Sender is the recipient who previously declined. Their new initiation
        # is affirmative intent, independent of the old terminal request.
        own_suppression.cleared_at = now
    affirmative = pending is not None and pending.sender_profile_id == recipient_id
    if pending is not None and not affirmative and pending.note != note:
        raise _error(
            409, Error.TRANSITION_CONFLICT, "An introductory request is already pending"
        )
    if pending is None:
        pending = MessageRequest(
            id=uuid.uuid4().hex,
            relationship_id=pair_id,
            sender_profile_id=sender_id,
            recipient_profile_id=recipient_id,
            note=note,
            state=State.PENDING.value,
            created_at=now,
            expires_at=now + timedelta(days=30),
        )
        session.add(pending)
        session.flush()
    attempt = MessageRequestAttempt(
        id=uuid.uuid4().hex,
        request_id=pending.id,
        sender_profile_id=sender_id,
        recipient_profile_id=recipient_id,
        note=note,
        client_request_key=key,
        created_at=now,
    )
    session.add(attempt)
    if affirmative:
        conversation = _materialize(session, pending, relationship, now)
        # Preserve reverse initiator's submitted note as the next human message.
        second_time = max(datetime.now(timezone.utc), now + timedelta(microseconds=1))
        second = DirectMessage(
            id=uuid.uuid4().hex,
            conversation_id=conversation.id,
            sender_node_id=sender.node_id,
            sender_profile_id=sender_id,
            content_type="text/plain",
            body=note,
            client_message_key=f"request-attempt:{attempt.id}",
            created_at=second_time,
        )
        session.add(second)
        session.flush()
        attempt.materialized_message_id = second.id
        conversation.latest_activity_at = second_time
    # Clearing one's prior recipient-owned suppression deliberately allows
    # a new request; the peer still decides whether to accept it.
    session.commit()
    session.refresh(pending)
    return pending, False


def transition_request(session, profile, request_id, target):
    request = session.get(MessageRequest, request_id)
    caller = profile.profile_id
    if request is None or caller not in (
        request.sender_profile_id,
        request.recipient_profile_id,
    ):
        raise _error(404, Error.NOT_FOUND, "Message request not found")
    expected_actor = (
        request.sender_profile_id
        if target == State.WITHDRAWN
        else request.recipient_profile_id
    )
    if caller != expected_actor:
        raise _error(404, Error.NOT_FOUND, "Message request not found")
    pair_id = request.relationship_id
    relationship = _lock_pair(session, pair_id)
    request = session.scalar(
        select(MessageRequest)
        .where(MessageRequest.id == request_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    now = _now()
    if request.state == State.PENDING.value and _aware(request.expires_at) <= now:
        request.state = State.EXPIRED.value
        request.transitioned_at = request.expires_at
        session.commit()  # terminal deadline must survive the rejected action
        raise _error(
            409, Error.TRANSITION_CONFLICT, "This request is no longer pending"
        )
    if request.state == target.value:
        session.commit()
        return request, True
    if request.state != State.PENDING.value:
        raise _error(
            409, Error.TRANSITION_CONFLICT, "This request is no longer pending"
        )
    if target == State.ACCEPTED:
        _materialize(session, request, relationship, now)
    else:
        request.state = target.value
        request.transitioned_at = now
        if target == State.DECLINED:
            suppression = session.get(
                MessageRequestSuppression,
                (request.sender_profile_id, request.recipient_profile_id),
            )
            if suppression is None:
                suppression = MessageRequestSuppression(
                    sender_profile_id=request.sender_profile_id,
                    recipient_profile_id=request.recipient_profile_id,
                    source_request_id=request.id,
                    created_at=now,
                )
                session.add(suppression)
            else:
                suppression.source_request_id = request.id
                suppression.created_at = now
                suppression.cleared_at = None
    session.commit()
    session.refresh(request)
    return request, False


def _aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def request_payload(session, request, profile):
    if profile.profile_id not in (
        request.sender_profile_id,
        request.recipient_profile_id,
    ):
        raise _error(404, Error.NOT_FOUND, "Message request not found")
    peer_id = (
        request.recipient_profile_id
        if profile.profile_id == request.sender_profile_id
        else request.sender_profile_id
    )
    peer = session.scalar(select(UserProfile).where(UserProfile.profile_id == peer_id))
    return {
        "request_id": request.id,
        "relationship_id": request.relationship_id,
        "sender_profile_id": request.sender_profile_id,
        "recipient_profile_id": request.recipient_profile_id,
        "peer": service.social_profile_payload(peer),
        "note": request.note,
        "state": request.state,
        "created_at": _aware(request.created_at).isoformat(),
        "expires_at": _aware(request.expires_at).isoformat(),
        "transitioned_at": _aware(request.transitioned_at).isoformat()
        if request.transitioned_at
        else None,
        "conversation_id": request.conversation_id,
        "first_message_id": request.first_message_id,
        "outgoing": request.sender_profile_id == profile.profile_id,
    }


def _participant_predicate(profile_id):
    return or_(
        MessageRequest.sender_profile_id == profile_id,
        MessageRequest.recipient_profile_id == profile_id,
    )


def list_requests(session, profile, *, history=False, limit=100):
    profile_id = profile.profile_id
    _lock_profile(session, profile_id)
    now = _now()
    _expire(session, now, _participant_predicate(profile_id))
    preference = session.get(MessageRequestPreferences, profile_id)
    if preference is not None and preference.auto_hide_terminal:
        terminal = session.scalars(
            select(MessageRequest).where(
                _participant_predicate(profile_id),
                MessageRequest.state.in_(
                    [State.DECLINED.value, State.WITHDRAWN.value, State.EXPIRED.value]
                ),
                ~select(MessageRequestVisibility.request_id)
                .where(
                    MessageRequestVisibility.request_id == MessageRequest.id,
                    MessageRequestVisibility.profile_id == profile_id,
                )
                .exists(),
            )
        )
        for request in terminal:
            session.add(
                MessageRequestVisibility(
                    request_id=request.id, profile_id=profile_id, hidden_at=now
                )
            )
        session.flush()
    query = (
        select(MessageRequest)
        .where(
            _participant_predicate(profile_id),
            (MessageRequest.state != State.PENDING.value)
            if history
            else (MessageRequest.state == State.PENDING.value),
            ~select(MessageRequestVisibility.request_id)
            .where(
                MessageRequestVisibility.request_id == MessageRequest.id,
                MessageRequestVisibility.profile_id == profile_id,
            )
            .exists(),
        )
        .order_by(MessageRequest.created_at.desc(), MessageRequest.id)
        .limit(min(max(limit, 1), 200))
    )
    result = [
        request_payload(session, request, profile) for request in session.scalars(query)
    ]
    session.commit()
    return result


def history_preferences(session, profile, auto_hide_terminal=None):
    profile_id = profile.profile_id
    _lock_profile(session, profile_id)
    preference = session.get(MessageRequestPreferences, profile_id)
    if auto_hide_terminal is not None:
        if preference is None:
            preference = MessageRequestPreferences(
                profile_id=profile_id,
                auto_hide_terminal=auto_hide_terminal,
                updated_at=_now(),
            )
            session.add(preference)
        else:
            preference.auto_hide_terminal = auto_hide_terminal
            preference.updated_at = _now()
    result = {"auto_hide_terminal": bool(preference and preference.auto_hide_terminal)}
    session.commit()
    return result


def archive_request(session, profile, request_id):
    _lock_profile(session, profile.profile_id)
    request = session.get(MessageRequest, request_id)
    if request is None or profile.profile_id not in (
        request.sender_profile_id,
        request.recipient_profile_id,
    ):
        raise _error(404, Error.NOT_FOUND, "Message request not found")
    if request.state == State.PENDING.value:
        raise _error(
            409,
            Error.TRANSITION_CONFLICT,
            "Pending requests must be accepted, declined or withdrawn first",
        )
    if session.get(MessageRequestVisibility, (request_id, profile.profile_id)) is None:
        session.add(
            MessageRequestVisibility(
                request_id=request_id, profile_id=profile.profile_id, hidden_at=_now()
            )
        )
    session.commit()
