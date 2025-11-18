# Agent Storage and Management Investigation - Codexify Codebase

## Executive Summary

The Codexify codebase implements a **hybrid agent management system** that uses both:
1. **Database-based storage** (PostgreSQL/SQLite) for agent profiles and state
2. **File-based registry** (JSON) for agent discovery and metadata
3. **In-memory orchestration** for agent execution and communication

Agents are not created dynamically in real-time but are predefined and configured through:
- Static agent modules (Python files)
- Registry files (JSON)
- Database profiles (PostgreSQL agent_profiles table)

## 1. Agent Configuration/Definition Storage

### A. Primary Storage Locations

#### 1. **Agent Profile Database Table** (`agent_profiles`)
- **Location**: PostgreSQL table (defined in `sql/complete_schema.sql`)
- **Schema**:
  ```sql
  CREATE TABLE agent_profiles (
    agent_id TEXT PRIMARY KEY,
    profile_json JSONB,
    summarization_frequency INTEGER DEFAULT 0,
    last_summarized_at TIMESTAMPTZ
  );
  ```
- **Purpose**: Stores persistent agent configuration and state
- **Accessed Via**: `PgDB.get_agent_profile()` and `PgDB.upsert_agent_profile()` methods
- **Multi-Instance Access**: YES - Any database-connected instance can query this table

#### 2. **Agent Registry JSON File** (`guardian/agent_registry.json`)
- **Location**: File-based registry at `guardian/agent_registry.json`
- **Format**: Git LFS pointer (actual content not directly readable)
- **Purpose**: Maintains companion agent registry and metadata
- **Structure**: Contains list of companion agents with:
  - Name, path, and active status
  - Last active timestamp
  - Health status
- **Accessed By**:
  - `MetacognitionEngine.load_agent_registry()`
  - `CompanionProfileManager._load_registry()`
  - `EpistemicState` self-check module

#### 3. **Companion Profile Files** (`guardian/profiles/`)
- **Location**: Individual JSON files in `guardian/profiles/` directory
- **Format**: One JSON file per companion profile
- **Naming**: Sanitized companion names (e.g., `axis.json`, `vestige.json`)
- **Purpose**: Store detailed companion definitions and configurations
- **Managed By**: `CompanionProfileManager` class

### B. Agent Implementation Files (Code-Based)

Predefined agent implementations in Python:

1. **Core Orchestrator Agents** (`guardian/core/orchestrator/agents/`)
   - `foresight_agent.py` - Predictive insights and nudges
   - `health_agent.py` - Health metrics summaries
   - `memory_agent.py` - Memory querying and storage
   - `ritual_agent.py` - Ritual triggering and logging

2. **Main Agents** (`guardian/agents/`)
   - `axis.py` - Core decision-making and routing system
   - `vestige.py` - Companion agent (role: memory/continuity)
   - `echoform.py` - Companion agent (role: reflection)
   - `imprint_zero.py` - System initialization and onboarding

3. **Research Agents** (`guardian/core/research/Modules/agent/`)
   - `agent.py` - Base agent module
   - `search.py` - Search functionality
   - `planner.py` - Planning functionality
   - `looking_glass.py` - Observation/introspection

## 2. Synchronization Mechanisms for Agents

### A. Database-Level Synchronization

**Event Outbox Pattern**:
```
Location: events_outbox table (PostgreSQL)
Purpose: Durable event propagation across instances
Mechanism:
  - Events appended to events_outbox table
  - Events are replayed/consumed by subscribers
  - Soft-deleted on consumption (status update)
Methods:
  - append_event(topic, payload, tenant_id)
  - list_events_after(last_id, limit)
  - delete_events_through(last_id, tenant_id)
```

**Sync Jobs Table**:
```
Location: sync_jobs table (PostgreSQL)
Purpose: Track distributed synchronization jobs
Fields:
  - connector_id: External service identifier
  - status: pending/running/completed/failed
  - metadata: JSONB for job-specific data
  - created_at, started_at, finished_at
Methods:
  - create_sync_job(connector_id, status, metadata)
  - update_sync_job(job_id, status, metadata)
  - list_recent_sync_jobs(connector_id, limit)
```

### B. File-Based Synchronization

**Registry File Updates**:
- Mutual exclusion: File-based registry uses simple JSON read/write patterns
- **Risk**: Concurrent writes from multiple instances could cause data loss
- No explicit locking mechanism detected

**Profile Manager Synchronization**:
```python
# CompanionProfileManager (_save_registry)
def _save_registry(self, registry):
    with open(self.registry_path, "w") as f:
        json.dump(registry, f, indent=2)
```
- Atomic file operations (no explicit transaction safety)
- Deployments update registry in-place via `deploy_profile(name)`

### C. Memory System Integration

**MemoryOS Integration**:
- Agents interact with central `Memoryos` singleton instance
- Memory events propagate through memory system's persistence layer
- Agents call methods like:
  - `memory_client.add_memory(...)`
  - `memory_client.query(...)`
  - `memory_client.fetch_memory(...)`

### D. Metacognition Engine Synchronization

```python
# In MetacognitionEngine
def update_agent_status(self, agent_id, status, health_status):
    registry = self.load_agent_registry()
    registry[agent_id].update({
        "status": status,
        "health_status": health_status,
        "last_active": datetime.now(UTC).isoformat()
    })
    with open(self.registry_path, "w") as f:
        json.dump(registry, f, indent=2)
```
- Status updates written back to registry file
- No distributed locking; vulnerable to race conditions

## 3. Listing and Viewing Existing Agents

### A. Agent Discovery Methods

**Via CompanionProfileManager**:
```python
# List all companion profiles
def list_profiles(self) -> List[Dict]:
    registry = self._load_registry()
    return registry["companions"]
    # Returns: [{"name": "Axis", "path": "...", "active": bool}, ...]
```

**Via MetacognitionEngine**:
```python
# Load agent registry and filter
registry = self.load_agent_registry()
for agent_id, info in registry.items():
    if info.get("status") == "active":
        active_agents.append(agent_id)
```

**Via Database** (Agent Profiles):
```python
# Get single agent profile
profile = db.get_agent_profile(agent_id)
# Returns: {"agent_id": str, "profile": dict, "summarization_frequency": int, "last_summarized_at": str}
```

**Via Orchestrator** (Agent Actions):
```python
# Map of available agent actions
AGENT_ACTIONS = {
    "get_health_summary": get_health_summary,
    "trigger_ritual": trigger_ritual,
    "fetch_memory": fetch_memory,
    "run_foresight": run_foresight,
}
```

### B. Status Inspection

**Health Check via Metacognition**:
```python
def system_health_check(self) -> Dict:
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

**Via Database Queries**:
- Last summarization time
- Profile JSON data
- Summarization frequency constraints

## 4. Cross-Instance Agent Availability

### A. Shared Database - YES

**Database-stored agents** ARE available across instances:
- Multiple instances can query `agent_profiles` table
- Event outbox ensures eventual consistency across instances
- Sync jobs table tracks work distribution

**Implementation**:
```python
# In PgDB.__init__
def __init__(self, dsn: str):
    self.dsn = dsn  # PostgreSQL connection string
    # All queries go through psycopg2 connection pool

# Any instance with DATABASE_URL can access
db = PgDB(dsn)
profile = db.get_agent_profile("axis")  # Works from any instance
```

### B. File-Based Registry - LIMITED/PROBLEMATIC

**File Registry Access**:
- Shared filesystem required (not cloud-safe)
- No synchronization mechanism between instances
- Last-write-wins behavior (data loss risk)

**Deployment Flow**:
```
Instance A: Calls profile_manager.deploy_profile("axis")
  -> Reads agent_registry.json
  -> Updates registry with active = True
  -> Writes back to agent_registry.json

Instance B: Simultaneously reads same file
  -> May get stale data or corrupted JSON if writes collide
```

### C. Recommended Cross-Instance Pattern

**Current Best Practice**:
1. Use PostgreSQL `agent_profiles` table for persistent agent state
2. Use `events_outbox` for publishing agent status changes
3. Avoid relying on file-based registry for multi-instance deployments
4. Use MemoryOS singleton for agent communication (factory pattern)

**Unsafe Patterns**:
- Relying on `agent_registry.json` for multi-instance scenarios
- Deploying profiles only via file system
- Not checking database for canonical agent state

## 5. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Multi-Instance System                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Instance A              Instance B           Instance C     │
│  ┌─────────────┐        ┌─────────────┐      ┌─────────────┐│
│  │ Orchestrator│        │ Orchestrator│      │ Orchestrator││
│  │ + Agents    │        │ + Agents    │      │ + Agents    ││
│  └──────┬──────┘        └──────┬──────┘      └──────┬───────┘│
│         │                      │                     │        │
│         └──────────────────────┼─────────────────────┘        │
│                                │                              │
│          ┌─────────────────────┼─────────────────────┐        │
│          │                     │                     │        │
│    ┌─────▼─────┐    ┌──────────▼────────┐    ┌─────▼─────┐  │
│    │ PostgreSQL│    │  Shared Filesystem│    │  MemoryOS │  │
│    │           │    │                   │    │  (Cache)  │  │
│    │ Tables:   │    │ - agent_registry. │    │           │  │
│    │ - agent_  │    │   json            │    │  (Factory │  │
│    │   profiles│    │ - profiles/       │    │   pattern)│  │
│    │ - events_ │    │   *.json          │    │           │  │
│    │   outbox  │    │                   │    │           │  │
│    │ - sync_   │    │ [UNSAFE for       │    │           │  │
│    │   jobs    │    │  multi-instance]  │    │           │  │
│    └───────────┘    └───────────────────┘    └───────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 6. Key Findings Summary

| Aspect | Status | Details |
|--------|--------|---------|
| **Agent Storage** | Both DB + Files | `agent_profiles` table + JSON registry files |
| **Multi-Instance Access** | Partial | Database YES, File registry NO |
| **Synchronization** | Event-based | Via `events_outbox` table (eventual consistency) |
| **Agent Discovery** | Programmatic | Via registry loader + database queries |
| **Creation Pattern** | Static/Config | Agents defined in code, configs in DB/files |
| **Race Conditions** | Possible | File-based registry has write collision risks |
| **Transaction Safety** | Moderate | Database uses standard SQL transactions, files do not |

## 7. Recommendations

1. **For Multi-Instance Deployments**:
   - Use PostgreSQL `agent_profiles` as canonical source
   - Consume events from `events_outbox` for status synchronization
   - Avoid relying on shared file system for agent registry

2. **For Agent Deployment**:
   - Update agent profiles via database ORM/transactions
   - Publish deployment events to `events_outbox`
   - Subscribe to events for eventual consistency

3. **For Agent Discovery**:
   - Query database `agent_profiles` table directly
   - Cache in-process but invalidate via event notifications
   - Do not rely solely on file-based registry

4. **For Synchronization Safety**:
   - Implement explicit locking for profile updates (e.g., advisory locks in PostgreSQL)
   - Use batch upserts rather than read-modify-write cycles
   - Consider message queue (not implemented) for cross-instance communication

## Related Files Referenced

### Database/Storage Layer
- `/home/user/Codexify/guardian/core/pgdb.py` - PostgreSQL interface with agent profile methods
- `/home/user/Codexify/guardian/core/chat_db.py` - Abstract database interface
- `/home/user/Codexify/sql/complete_schema.sql` - SQL schema definition
- `/home/user/Codexify/guardian/db/models.py` - SQLAlchemy ORM models

### Agent Management
- `/home/user/Codexify/guardian/metacognition.py` - Agent registry loading and status updates
- `/home/user/Codexify/guardian/profiles/manager.py` - Companion profile manager
- `/home/user/Codexify/guardian/self_check.py` - Agent registry discovery

### Agent Implementations
- `/home/user/Codexify/guardian/core/orchestrator/agents/` - Core orchestrator agents
- `/home/user/Codexify/guardian/agents/` - Main agent implementations (Axis, Vestige, etc.)
- `/home/user/Codexify/guardian/core/research/Modules/agent/` - Research module agents

### Orchestration
- `/home/user/Codexify/guardian/core/orchestrator/pulse_orchestrator.py` - Agent routing and execution

## Investigation Date
November 7, 2025
