# Agent Implementation Reference - Code Examples

## Quick Navigation

### Where Agents Are Stored

#### 1. PostgreSQL Database (`agent_profiles` table)
**File:** `/home/user/Codexify/sql/complete_schema.sql` (lines 90-96)

```sql
CREATE TABLE IF NOT EXISTS agent_profiles (
  agent_id                  TEXT PRIMARY KEY,
  profile_json              JSONB,
  summarization_frequency   INTEGER DEFAULT 0,
  last_summarized_at        TIMESTAMPTZ
);
```

**Access Methods in PgDB:** `/home/user/Codexify/guardian/core/pgdb.py`

```python
# Get agent profile (line 1416-1453)
def get_agent_profile(self, agent_id: str):
    with self._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT agent_id, profile_json, summarization_frequency, last_summarized_at
                   FROM agent_profiles
                   WHERE agent_id = %s""",
                (agent_id,)
            )
            # Returns normalized profile dict or None

# Update/create agent profile (line 1455-1495)
def upsert_agent_profile(self, agent_id: str, **fields):
    # UPSERT operation for profile_json, summarization_frequency, last_summarized_at
    with self._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO agent_profiles (agent_id, ...)
                   VALUES (...) 
                   ON CONFLICT (agent_id) DO UPDATE SET ..."""
            )
```

---

#### 2. JSON File Registry (`agent_registry.json`)
**File:** `/home/user/Codexify/guardian/agent_registry.json` (Git LFS)

**Loaded by:**
- `/home/user/Codexify/guardian/metacognition.py` (line 52)
- `/home/user/Codexify/guardian/self_check.py` (line 49)
- `/home/user/Codexify/guardian/profiles/manager.py` (line 25)

**Example:**
```python
# MetacognitionEngine.load_agent_registry() (line 56-63)
def load_agent_registry(self) -> Dict[str, Any]:
    try:
        with open(self.registry_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load agent registry: {e}")
        return {}
```

---

#### 3. Companion Profile Files
**Location:** `/home/user/Codexify/guardian/profiles/`

**Managed by:** `/home/user/Codexify/guardian/profiles/manager.py`

```python
# CompanionProfileManager - manages individual profile JSON files
class CompanionProfileManager:
    def __init__(self):
        self.profiles_dir = Path("guardian/profiles")
        self.registry_path = Path("guardian/agent_registry.json")
    
    def save_profile(self, profile: Dict[str, Any]) -> bool:
        """Save individual companion profile to JSON file"""
        safe_name = self._sanitize_filename(profile.get("name"))
        profile_path = self.profiles_dir / f"{safe_name}.json"
        # Writes to disk and updates registry
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        """List all companion profiles"""
        registry = self._load_registry()
        return registry["companions"]
```

---

### How Agents Are Discovered

#### Method 1: Via File Registry + Metacognition
**File:** `/home/user/Codexify/guardian/metacognition.py` (lines 56-96)

```python
def load_agent_registry(self) -> Dict[str, Any]:
    """Load the current agent registry"""
    registry = json.load(open(self.registry_path, "r"))
    return registry

def update_agent_status(self, agent_id: str, status: str, health_status: str = "nominal") -> bool:
    """Update an agent's status in the registry"""
    registry = self.load_agent_registry()
    if agent_id in registry:
        registry[agent_id].update({
            "status": status,
            "health_status": health_status,
            "last_active": datetime.now(UTC).isoformat(),
        })
        # Write back to file
```

#### Method 2: Via Database Queries
**File:** `/home/user/Codexify/guardian/core/pgdb.py` (lines 1416-1453)

```python
def get_agent_profile(self, agent_id: str):
    """Get agent profile from database"""
    with self._connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT agent_id, profile_json, summarization_frequency, last_summarized_at
                FROM agent_profiles
                WHERE agent_id = %s
            """, (agent_id,))
            # Returns dict with agent configuration
```

#### Method 3: Via System Health Check
**File:** `/home/user/Codexify/guardian/metacognition.py` (lines 98-148)

```python
def system_health_check(self) -> Dict[str, Any]:
    """Comprehensive system health check"""
    registry = self.load_agent_registry()
    
    agent_status = {}
    for agent_id, info in registry.items():
        if isinstance(info, dict):
            agent_status[agent_id] = info.get("health_status", "unknown")
    
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "agent_status": agent_status,
        "memory_status": "...",
        "thread_health": "...",
        "overall_health": "nominal|warning|error"
    }
```

#### Method 4: Via Orchestrator Agent Mapping
**File:** `/home/user/Codexify/guardian/core/orchestrator/pulse_orchestrator.py` (lines 81-86)

```python
# Static mapping of available agent actions
AGENT_ACTIONS = {
    "get_health_summary": get_health_summary,
    "trigger_ritual": trigger_ritual,
    "fetch_memory": fetch_memory,
    "run_foresight": run_foresight,
}

def orchestrate(command: dict):
    """Route and execute agent functions"""
    action = command.get("action")
    agent_function = AGENT_ACTIONS.get(action)
    if agent_function:
        # Execute agent with memory client
```

---

### How Agents Synchronize Across Instances

#### Method 1: Event Outbox Pattern (Database)
**File:** `/home/user/Codexify/guardian/core/pgdb.py` (lines 1351-1399)

```python
def append_event(self, topic: str, payload: Dict[str, Any], tenant_id: str = "default") -> None:
    """Append event to outbox for cross-instance propagation"""
    with self._connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO events_outbox (topic, payload, tenant_id)
                VALUES (%s, %s, %s)
            """, (topic, _to_json(payload), tenant_id))

def list_events_after(self, last_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieve events for subscription processing"""
    with self._connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, topic, payload, tenant_id, created_at
                FROM events_outbox
                WHERE id > %s
                ORDER BY id ASC
                LIMIT %s
            """, (last_id, limit))
            return [dict(row) for row in cur.fetchall()]

def delete_events_through(self, last_id: int, tenant_id: Optional[str] = None) -> None:
    """Mark events as consumed/deleted"""
```

**Table Schema:** `/home/user/Codexify/sql/complete_schema.sql`

```
events_outbox:
  id - auto-incrementing
  topic - event type
  payload - JSONB data
  tenant_id - routing
  status - pending/consumed
  created_at - timestamp
```

#### Method 2: Sync Jobs Table (Distributed Work)
**File:** `/home/user/Codexify/guardian/core/pgdb.py` (lines 988-1067)

```python
def create_sync_job(self, connector_id: str, *, status: str = "queued", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create distributed sync job"""
    with self._connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sync_jobs (connector_id, status, metadata)
                VALUES (%s, %s, %s)
                RETURNING id, connector_id, status, created_at, ...
            """, (connector_id, status, _to_json(metadata)))

def update_sync_job(self, job_id: int, *, status: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Update sync job status and metadata"""
    # UPDATE sync_jobs SET status=%s, metadata=%s WHERE id=%s
```

**Table Schema:**
```
sync_jobs:
  id - primary key
  connector_id - external service identifier
  status - pending/running/completed/failed
  created_at, started_at, finished_at - timestamps
  attempts - retry counter
  last_error - error message
  metadata - JSONB job-specific data
```

#### Method 3: File-Based Registry (NO LOCKING - UNSAFE)
**File:** `/home/user/Codexify/guardian/profiles/manager.py` (lines 43-49)

```python
def _save_registry(self, registry: Dict[str, List[Dict[str, Any]]]) -> None:
    """Save companion registry - VULNERABLE TO CONCURRENT WRITES"""
    try:
        with open(self.registry_path, "w") as f:
            json.dump(registry, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save registry: {e}")

# WARNING: This pattern has no distributed locking!
# In multi-instance deployment:
#   Instance A reads registry
#   Instance B reads registry
#   Instance A writes back
#   Instance B writes back <- OVERWRITES A's changes!
```

---

### Agent Implementations (Predefined)

#### 1. Core Orchestrator Agents
**Location:** `/home/user/Codexify/guardian/core/orchestrator/agents/`

**Files:**
- `foresight_agent.py` - Predictive insights
- `health_agent.py` - Health metrics
- `memory_agent.py` - Memory I/O
- `ritual_agent.py` - Ritual execution

**Example: Memory Agent**
```python
# /guardian/core/orchestrator/agents/memory_agent.py
def fetch_memory(memory_client: Memoryos, query: str, limit: int = 10) -> dict:
    """Fetches memories based on query"""
    try:
        results = memory_client.query(query, limit=limit)
        return {"status": "ok", "memories": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

#### 2. Main Agents
**Location:** `/home/user/Codexify/guardian/agents/`

**Files:**
- `axis.py` - Core decision-making and routing
- `vestige.py` - Memory and continuity
- `echoform.py` - Reflection
- `imprint_zero.py` - System initialization

**Example: Axis Agent**
```python
# /guardian/agents/axis.py
class AxisAgent:
    """Core decision-making and routing agent"""
    
    def __init__(self, codex: CodexAwareness, metacognition: MetacognitionEngine):
        self.codex = codex
        self.metacognition = metacognition
        self.decisions: List[Decision] = []
    
    async def make_decision(self, decision_type, context, options):
        """Make routing/resource/priority decisions"""
        # Uses metacognition engine for validation
```

---

### Abstract Database Interface

**File:** `/home/user/Codexify/guardian/core/chat_db.py` (lines 593-634)

```python
class ChatDB(ABC):
    """Common interface both SQLite and Postgres adapters must implement"""
    
    @abstractmethod
    def get_agent_profile(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get an agent profile"""
        ...
    
    @abstractmethod
    def upsert_agent_profile(self, agent_id: str, **updates: Any) -> None:
        """Upsert an agent profile"""
        ...
    
    @abstractmethod
    def check_summarization_allowed(self, agent_id: str, requested_by: str) -> Tuple[bool, Optional[str]]:
        """Check if summarization is allowed based on frequency limits"""
        ...
```

---

## Multi-Instance Deployment Considerations

### Safe Pattern:
```
1. Use agent_profiles table (PostgreSQL) for canonical state
2. Publish agent status changes to events_outbox
3. Subscribe to events for eventual consistency
4. Cache locally but invalidate on event notification
```

### Unsafe Pattern:
```
1. Relying on agent_registry.json for multi-instance scenarios
2. No distributed locking on file updates
3. Last-write-wins leads to data loss
4. No mechanism to synchronize across instances
```

---

## Testing and Debugging

### Check Agent Profiles
```python
from guardian.core.pgdb import PgDB

db = PgDB(dsn)
profile = db.get_agent_profile("axis")
print(profile)
# {'agent_id': 'axis', 'profile': {...}, 'summarization_frequency': 0, 'last_summarized_at': None}
```

### List All Agents
```python
from guardian.profiles.manager import profile_manager

agents = profile_manager.list_profiles()
for agent in agents:
    print(f"{agent['name']} - Active: {agent['active']}")
```

### Check System Health
```python
from guardian.metacognition import MetacognitionEngine

engine = MetacognitionEngine()
health = engine.system_health_check()
print(f"Overall Health: {health['overall_health']}")
print(f"Active Agents: {health['agent_status']}")
```

---

## File References Quick Index

| Task | File | Lines | Method |
|------|------|-------|--------|
| Store agent | `/guardian/core/pgdb.py` | 1455-1495 | `upsert_agent_profile()` |
| Retrieve agent | `/guardian/core/pgdb.py` | 1416-1453 | `get_agent_profile()` |
| List agents | `/guardian/profiles/manager.py` | 151-159 | `list_profiles()` |
| Deploy agent | `/guardian/profiles/manager.py` | 161-193 | `deploy_profile()` |
| Publish event | `/guardian/core/pgdb.py` | 1351-1364 | `append_event()` |
| Read events | `/guardian/core/pgdb.py` | 1366-1381 | `list_events_after()` |
| Register status | `/guardian/metacognition.py` | 65-96 | `update_agent_status()` |
| Orchestrate | `/guardian/core/orchestrator/pulse_orchestrator.py` | 81-160 | `orchestrate()` |

---

## Investigation Date
November 7, 2025
