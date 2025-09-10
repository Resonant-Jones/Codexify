# ✅ Guardian Test Suite Debug + Fix Checklist

### 📁 1️⃣ Relative Import Fix
- [ ] Identify all `from ..main import ...` style imports in `pattern_analyzer` and other plugin tests.
- [ ] Convert each to **absolute imports**.  
  Example:  
  ```py
  # BAD
  from ..main import PatternAnalyzer

  # GOOD
  from guardian.plugins.pattern_analyzer.main import PatternAnalyzer