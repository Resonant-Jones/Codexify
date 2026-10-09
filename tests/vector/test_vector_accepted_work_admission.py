from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from guardian.core import chat_completion_service as completion
from guardian.core import chat_postgres_deadline as bounds
from guardian.tasks.chat_deadline import (
    AcceptedChatTaskDeadlineExceeded,
    build_accepted_chat_task_deadline,
)
from guardian.vector import store as vector


def envelope(remaining):
    return build_accepted_chat_task_deadline(
        datetime.now(timezone.utc) - timedelta(seconds=720 - remaining)
    )


@pytest.mark.parametrize('backend', ['chroma', 'faiss'])
@pytest.mark.parametrize('surface', ['construction', 'search'])
def test_expired_work_never_enters_native_vector(monkeypatch, backend, surface):
    native = Mock(return_value=[])
    monkeypatch.setenv('CODEXIFY_VECTOR_STORE', backend)
    monkeypatch.setattr(vector, 'Embedder', native)
    instance = vector.VectorStore(initialize_embedder=False)
    instance.embedder = SimpleNamespace(search=native)
    with bounds.accepted_postgres_query_scope(envelope(-0.1)):
        with pytest.raises(AcceptedChatTaskDeadlineExceeded) as caught:
            if surface == 'construction':
                vector.VectorStore()
            else:
                instance.search('query', namespace='thread:7', user_id='owner')
    native.assert_not_called()
    assert caught.value.detail['completion_truth'] == {
        'accepted': True, 'attempted': False, 'fallback_attempted': False,
        'executed': False, 'completed': False,
    }


def test_invalid_envelope_never_enters_native_search():
    native = Mock(return_value=[])
    instance = vector.VectorStore(initialize_embedder=False)
    instance.embedder = SimpleNamespace(search=native)
    with bounds.accepted_postgres_query_scope(None, invalid=True):
        with pytest.raises(ValueError, match='snapshot is invalid'):
            instance.search('query', user_id='owner')
    native.assert_not_called()


@pytest.mark.parametrize('scoped', [False, True])
def test_normal_search_keeps_result_and_authority(scoped):
    expected = [{'text': 'retained', 'score': 0.75, 'metadata': {'user_id': 'owner'}}]
    native = Mock(return_value=expected)
    instance = vector.VectorStore(initialize_embedder=False)
    instance.embedder = SimpleNamespace(search=native)
    with bounds.accepted_postgres_query_scope(envelope(30) if scoped else None):
        assert instance.search('query', k=2, namespace=' thread:7 ', user_id=' owner ') is expected
    native.assert_called_once_with('query', k=2, namespace='thread:7', user_id='owner')


def test_terminal_database_phase_cannot_renew_vector_work():
    native = Mock(return_value=[])
    instance = vector.VectorStore(initialize_embedder=False)
    instance.embedder = SimpleNamespace(search=native)
    with bounds.accepted_postgres_query_scope(envelope(-0.1)):
        bounds.use_postgres_terminal_budget()
        assert bounds._budget.get().remaining() > 0
        with pytest.raises(AcceptedChatTaskDeadlineExceeded):
            instance.search('query', user_id='owner')
    native.assert_not_called()
    # Restoring the caller's absent scope must retain the legacy operation.
    assert instance.search('query', user_id='owner') == []
    native.assert_called_once()


def test_workspace_reconstruction_propagates_exact_deadline(monkeypatch):
    error = AcceptedChatTaskDeadlineExceeded()
    store = SimpleNamespace(store='chroma', chroma_path='/existing', collection='existing')
    monkeypatch.setattr(completion, 'VectorStore', Mock(return_value=store))
    native = Mock(side_effect=error)
    monkeypatch.setattr(completion, '_WorkspaceVectorEmbedder', native)
    with pytest.raises(AcceptedChatTaskDeadlineExceeded) as caught:
        completion._workspace_completion_vector_store()
    assert caught.value is error
    native.assert_called_once()


def test_workspace_expiry_before_reconstruction_enters_no_native(monkeypatch):
    store = SimpleNamespace(store='chroma', chroma_path='/existing', collection='existing')
    monkeypatch.setattr(completion, 'VectorStore', Mock(return_value=store))
    native = Mock(return_value=object())
    monkeypatch.setattr(completion, '_WorkspaceVectorEmbedder', native)
    with bounds.accepted_postgres_query_scope(envelope(-0.1)):
        with pytest.raises(AcceptedChatTaskDeadlineExceeded):
            completion._workspace_completion_vector_store()
    native.assert_not_called()


def test_workspace_optional_non_deadline_error_preserves_existing_store(monkeypatch):
    store = SimpleNamespace(store='chroma', chroma_path='/existing', collection='existing')
    monkeypatch.setattr(completion, 'VectorStore', Mock(return_value=store))
    monkeypatch.setattr(completion, '_WorkspaceVectorEmbedder', Mock(side_effect=RuntimeError('optional')))
    assert completion._workspace_completion_vector_store() is store


@pytest.mark.parametrize('fallback', ['namespace', 'legacy'])
def test_expiry_between_legacy_native_calls_never_starts_replacement(fallback):
    import time

    calls = []

    def native(*args, **kwargs):
        calls.append(kwargs)
        if fallback == 'namespace' or 'user_id' not in kwargs:
            time.sleep(0.04)
        raise TypeError('older signature')

    instance = vector.VectorStore(initialize_embedder=False)
    instance.embedder = SimpleNamespace(search=native)
    with bounds.accepted_postgres_query_scope(envelope(0.03)):
        with pytest.raises(AcceptedChatTaskDeadlineExceeded):
            instance.search('query', user_id='owner')
    assert len(calls) == (1 if fallback == 'namespace' else 2)


def test_constructor_checks_again_after_runtime_resolution(monkeypatch):
    import time

    runtime = SimpleNamespace(backend='chroma', chroma_path='/existing', collection='existing')

    def resolve():
        time.sleep(0.04)
        return runtime

    monkeypatch.setattr(vector, 'resolve_vector_store_runtime', resolve)
    native = Mock()
    monkeypatch.setattr(vector, 'Embedder', native)
    with bounds.accepted_postgres_query_scope(envelope(0.03)):
        with pytest.raises(AcceptedChatTaskDeadlineExceeded):
            vector.VectorStore()
    native.assert_not_called()
