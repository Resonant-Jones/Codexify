# ✅ ThreadSpace Test Fix Checklist

### 📂 File: `guardian/plugins/memory_analyzer/tests/test_memory_analyzer.py`

## 1️⃣ Codex Mock Consistency
- [ ] Verify the **real implementation** uses `query_memories`. 
- [ ] Make sure all test mocks use `codex.query_memories` — no mismatch with `query_memory`.

## 2️⃣ Error Handling Path
- [ ] Confirm `analyze_memories()` wraps its `codex.query_memories()` in a `try/except` that calls `metacognition.handle_error()`.
- [ ] Ensure your test error scenario actually triggers that path:
  ```py
  codex.query_memories.side_effect = Exception("Test error")
  with pytest.raises(Exception):
      await analyzer.analyze_memories()
  metacognition.handle_error.assert_called_once()