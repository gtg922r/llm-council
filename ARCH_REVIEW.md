# Architecture Review: LLM Council

This document provides an architecture review of the LLM Council application, focusing on data flow and data storage patterns. It includes recommendations for refactoring and guidelines for future development.

---

## 1. Current Architecture

### 1.1 High-Level Overview

LLM Council is a full-stack web application consisting of:

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | React 19 + Vite | Single-page application with real-time UI updates |
| **Backend** | FastAPI (Python) | REST API with Server-Sent Events (SSE) streaming |
| **Storage** | JSON files | File-based persistence in `data/conversations/` |
| **External API** | OpenRouter | Gateway to multiple LLM providers |

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                                │
│  ┌─────────────┐  ┌──────────────────────────────────────────────────────┐  │
│  │   Sidebar   │  │                  ChatInterface                       │  │
│  │             │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐             │  │
│  │  - List     │  │  │  Stage1  │ │  Stage2  │ │  Stage3  │             │  │
│  │  - Pin      │  │  │  Tabs    │ │  Rankings│ │  Final   │             │  │
│  │  - Archive  │  │  └──────────┘ └──────────┘ └──────────┘             │  │
│  └─────────────┘  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ REST API + SSE Streaming
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            BACKEND (FastAPI)                                 │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐            │
│  │    main.py     │───▶│   council.py   │───▶│  openrouter.py │───▶ LLMs  │
│  │   (Endpoints)  │    │  (3-Stage Orch)│    │  (API Client)  │            │
│  └────────────────┘    └────────────────┘    └────────────────┘            │
│           │                                                                  │
│           ▼                                                                  │
│  ┌────────────────┐                                                         │
│  │   storage.py   │ ───▶  data/conversations/{id}.json                     │
│  └────────────────┘                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow: Request/Message Processing

#### A. User Sends a New Message (Full Council Flow)

```
1. USER INPUT
   └─▶ ChatInput.jsx: User types message, optionally attaches files

2. FRONTEND PROCESSING (App.jsx)
   ├─▶ Optimistically add user message to UI
   ├─▶ Create placeholder assistant message with loading states
   ├─▶ Read file contents (if attached) and concatenate with message
   └─▶ Call api.sendMessageStream()

3. API CLIENT (api.js)
   └─▶ POST /api/conversations/{id}/message/stream
       └─▶ Body: { content: "...", target_model: null }

4. BACKEND ENDPOINT (main.py)
   ├─▶ Validate conversation exists via storage.get_conversation()
   ├─▶ Add user message: storage.add_user_message()
   ├─▶ If first message: spawn async task for title generation
   └─▶ Begin SSE event generator

5. STAGE 1: PARALLEL RESPONSES
   ├─▶ Emit SSE: { type: "stage1_start", total: 4 }
   ├─▶ Create asyncio tasks for each council model
   ├─▶ As each completes, emit: { type: "stage1_progress", completed: N }
   ├─▶ Query models via openrouter.query_model() in parallel
   └─▶ Emit SSE: { type: "stage1_complete", data: [...] }

6. STAGE 2: PEER RANKINGS
   ├─▶ Emit SSE: { type: "stage2_start", total: 4 }
   ├─▶ Anonymize responses (Response A, B, C, D)
   ├─▶ Each model evaluates and ranks all responses
   ├─▶ Parse rankings from "FINAL RANKING:" section via regex
   ├─▶ Calculate aggregate rankings
   └─▶ Emit SSE: { type: "stage2_complete", data: [...], metadata: {...} }

7. STAGE 3: CHAIRMAN SYNTHESIS
   ├─▶ Emit SSE: { type: "stage3_start" }
   ├─▶ Chairman model receives all responses + rankings
   ├─▶ Generates synthesized final answer
   └─▶ Emit SSE: { type: "stage3_complete", data: {...} }

8. PERSISTENCE
   ├─▶ Await title generation (if applicable)
   ├─▶ storage.add_assistant_message() - saves to JSON file
   └─▶ Emit SSE: { type: "complete" }

9. FRONTEND UI UPDATE (App.jsx)
   ├─▶ Parse SSE events in api.sendMessageStream()
   ├─▶ Update React state progressively for each stage
   ├─▶ Show progress bars during stage1/stage2
   └─▶ Render complete response with all three stages
```

#### B. Chairman Follow-up Flow

A simplified flow for follow-up questions that bypass the full council:

```
1. USER INPUT
   └─▶ FollowUpInput.jsx: User asks follow-up question

2. API CALL
   └─▶ POST /api/conversations/{id}/message
       └─▶ Body: { content: "...", target_model: "chairman" }

3. BACKEND PROCESSING
   ├─▶ Find last assistant message with stage1/2/3 data
   ├─▶ Extract original query from preceding user message
   └─▶ Call chairman_followup() with full context

4. RESPONSE
   └─▶ Returns immediately (no streaming for follow-ups currently)
```

#### C. Conversation Management Operations

```
CRUD Operations:
├─ GET  /api/conversations          → storage.list_conversations()
├─ POST /api/conversations          → storage.create_conversation()
├─ GET  /api/conversations/{id}     → storage.get_conversation()
├─ PATCH /api/conversations/{id}    → storage.save_conversation()
└─ DELETE /api/conversations/{id}   → storage.delete_conversation()

Special Operations:
└─ POST /api/conversations/{id}/duplicate → storage.duplicate_conversation()
```

### 1.3 Data Storage

#### A. Frontend State (In-Memory)

| State Variable | Location | Purpose |
|----------------|----------|---------|
| `conversations` | App.jsx | Array of conversation metadata for sidebar |
| `currentConversationId` | App.jsx | Currently selected conversation ID |
| `currentConversation` | App.jsx | Full conversation object with messages |
| `loadingConversationId` | App.jsx | ID of conversation currently processing |

**State Management Pattern:**
- Pure React hooks (`useState`, `useEffect`, `useCallback`)
- No external state library (Redux, Zustand, etc.)
- Optimistic updates for user messages
- Progressive updates via SSE callbacks for assistant messages

#### B. Backend Storage (JSON Files)

**Storage Location:** `data/conversations/{conversation_id}.json`

**Conversation Schema:**
```json
{
  "id": "uuid-string",
  "created_at": "2025-01-15T10:30:00Z",
  "title": "Conversation Title",
  "is_pinned": false,
  "is_archived": false,
  "messages": [
    {
      "role": "user",
      "content": "User's question text"
    },
    {
      "role": "assistant",
      "stage1": [
        {
          "model": "openai/gpt-5.2",
          "response": "Model's response text",
          "status": "success"
        }
      ],
      "stage2": [
        {
          "model": "openai/gpt-5.2",
          "ranking": "Full ranking text...",
          "parsed_ranking": ["Response C", "Response A", "Response B"],
          "status": "success"
        }
      ],
      "stage3": {
        "model": "google/gemini-3-pro-preview",
        "response": "Chairman's synthesized response"
      }
    }
  ]
}
```

**Storage Operations:**
| Operation | Implementation | I/O Pattern |
|-----------|----------------|-------------|
| Create | Write new JSON file | Sync write |
| Read | Load full JSON file | Sync read |
| Update | Load → Modify → Write | Read + Write |
| Delete | Remove file | Sync delete |
| List | Scan directory, load each file | N reads |

---

## 2. Proposed Refactoring

### 2.1 Backend: Eliminate Duplicate Council Logic

**Problem:** The streaming endpoint (`/message/stream`) in `main.py` duplicates the 3-stage orchestration logic from `council.py`. This creates maintenance burden and potential for divergence.

**Current State:**
- `council.py`: Contains `run_full_council()`, `stage1_collect_responses()`, `stage2_collect_rankings()`, `stage3_synthesize_final()`
- `main.py`: Re-implements Stage 1, 2, 3 inline within the streaming endpoint

**Proposed Solution:** Refactor to use an async generator pattern that yields events:

```python
# council.py
async def run_full_council_streaming(user_query: str):
    """Run council process, yielding events for streaming."""

    # Stage 1
    yield {"type": "stage1_start", "total": len(COUNCIL_MODELS)}

    async for model, response in query_models_with_progress(COUNCIL_MODELS, messages):
        yield {"type": "stage1_progress", "completed": count}

    yield {"type": "stage1_complete", "data": stage1_results}

    # Stage 2 (similar pattern)
    # Stage 3 (similar pattern)

    yield {"type": "complete", "data": {...}}
```

```python
# main.py - simplified endpoint
@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    async def event_generator():
        async for event in run_full_council_streaming(request.content):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Benefits:**
- Single source of truth for council logic
- Easier to test orchestration independently
- Cleaner separation of concerns

### 2.2 Backend: Optimize Storage for Listing

**Problem:** `list_conversations()` reads every JSON file to extract metadata, which scales poorly.

**Current Implementation:**
```python
def list_conversations():
    for filename in os.listdir(DATA_DIR):
        with open(path, 'r') as f:
            data = json.load(f)  # Loads entire file including all messages
            conversations.append({...})  # Extracts only metadata
```

**Proposed Solution:** Maintain a lightweight index file:

```python
# data/index.json
{
  "conversations": [
    {
      "id": "uuid-1",
      "created_at": "...",
      "title": "...",
      "is_pinned": false,
      "is_archived": false,
      "message_count": 5
    }
  ]
}
```

**Implementation:**
- Update index on create/update/delete operations
- List operation reads only the index file (O(1) file reads)
- Rebuild index on startup if missing or corrupted
- Keep backward compatibility: fall back to scanning if index missing

**Benefits:**
- Constant-time listing regardless of conversation count
- Reduced I/O for the most common operation

### 2.3 Backend: Async Storage Operations

**Problem:** File I/O operations are synchronous, blocking the event loop.

**Current State:**
```python
def get_conversation(conversation_id: str):
    with open(path, 'r') as f:  # Blocking I/O
        return json.load(f)
```

**Proposed Solution:** Use `aiofiles` for async file operations:

```python
import aiofiles
import json

async def get_conversation(conversation_id: str):
    path = get_conversation_path(conversation_id)
    async with aiofiles.open(path, 'r') as f:
        content = await f.read()
        return json.loads(content)
```

**Benefits:**
- Non-blocking I/O improves concurrency
- Better utilization of async runtime
- More scalable under concurrent load

### 2.4 Frontend: Normalize Conversation State

**Problem:** The current state structure stores the full conversation object separately from the list, leading to synchronization challenges.

**Current State:**
```javascript
const [conversations, setConversations] = useState([]);  // Metadata list
const [currentConversation, setCurrentConversation] = useState(null);  // Full object
```

**Issue:** When a conversation is updated, both states must be synchronized manually.

**Proposed Solution:** Normalize state with a conversations map:

```javascript
const [conversationsById, setConversationsById] = useState({});
const [conversationOrder, setConversationOrder] = useState([]);
const [currentConversationId, setCurrentConversationId] = useState(null);

// Derived state
const currentConversation = conversationsById[currentConversationId];
const conversations = conversationOrder.map(id => conversationsById[id]);
```

**Benefits:**
- Single source of truth for each conversation
- Updates automatically reflected everywhere
- Easier to implement optimistic updates
- Foundation for future caching strategy

### 2.5 Frontend: Add Client-Side Caching

**Problem:** Every conversation switch triggers an API call, even for recently viewed conversations.

**Proposed Solution:** Implement a simple LRU cache:

```javascript
// Simple in-memory cache with TTL
const conversationCache = new Map();
const CACHE_TTL = 5 * 60 * 1000;  // 5 minutes

async function getConversation(id) {
    const cached = conversationCache.get(id);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
        return cached.data;
    }

    const data = await api.getConversation(id);
    conversationCache.set(id, { data, timestamp: Date.now() });
    return data;
}
```

**Benefits:**
- Faster conversation switching
- Reduced backend load
- Better offline-first behavior potential

### 2.6 Summary: Refactoring Priority Matrix

| Refactoring | Impact | Effort | Priority |
|-------------|--------|--------|----------|
| Eliminate duplicate council logic | High | Medium | **High** |
| Optimize storage listing (index) | Medium | Low | **High** |
| Async storage operations | Medium | Low | **Medium** |
| Normalize frontend state | Medium | Medium | **Medium** |
| Client-side caching | Low | Low | **Low** |

---

## 3. Architecture Guidelines and Principles

The following guidelines should govern future development of LLM Council.

### 3.1 Data Flow Principles

#### Principle 1: Unidirectional Data Flow

```
User Action → API Call → Backend Processing → Storage → SSE Event → State Update → UI Render
```

- State flows in one direction: from user actions through the system
- UI is a function of state; never mutate state directly in event handlers
- All state changes should be traceable through the event stream

#### Principle 2: Optimistic Updates with Reconciliation

```javascript
// Pattern for optimistic updates
async function handleAction(data) {
    // 1. Apply optimistic update immediately
    setState(optimisticNewState);

    try {
        // 2. Perform actual operation
        const result = await api.performAction(data);

        // 3. Reconcile with server state
        setState(serverState);
    } catch (error) {
        // 4. Rollback on failure
        setState(previousState);
        showError(error);
    }
}
```

- Apply UI updates immediately for responsiveness
- Reconcile with server state after confirmation
- Provide clear rollback on failure

#### Principle 3: Stream-First for Long Operations

For any operation that may take more than 1-2 seconds:
- Use Server-Sent Events (SSE) for progress updates
- Provide granular progress indicators (not just spinner)
- Design for partial failure (some models may fail)

```python
# Good: Streaming with progress
async def long_operation():
    yield {"type": "start", "total": n}
    for i, item in enumerate(items):
        result = await process(item)
        yield {"type": "progress", "completed": i+1}
    yield {"type": "complete"}
```

### 3.2 Data Storage Principles

#### Principle 4: Backend is Source of Truth

```
┌─────────────────┐         ┌─────────────────┐
│    Frontend     │ ──API──▶│    Backend      │
│  (Cache/View)   │◀──SSE── │ (Source of Truth)│
└─────────────────┘         └─────────────────┘
```

- Backend storage is the canonical source of all data
- Frontend state is a cached view of backend state
- Never persist frontend-only state that should survive refresh
- All mutations go through the API

#### Principle 5: Immutable Message History

Once a message is saved:
- User messages are immutable
- Assistant messages (with all stages) are immutable
- Only conversation metadata (title, pinned, archived) can be modified

This ensures:
- Audit trail integrity
- Simpler state management
- Easier debugging and reproduction

#### Principle 6: Graceful Degradation

Design storage to handle failures:
```python
async def get_conversation(id):
    try:
        return await load_from_storage(id)
    except FileNotFoundError:
        return None  # Graceful handling
    except json.JSONDecodeError:
        log_error(f"Corrupted file: {id}")
        return None  # Don't crash, log and continue
```

### 3.3 API Design Principles

#### Principle 7: RESTful Resources with Action Endpoints

```
Standard CRUD:
GET    /api/conversations           # List
POST   /api/conversations           # Create
GET    /api/conversations/{id}      # Read
PATCH  /api/conversations/{id}      # Update
DELETE /api/conversations/{id}      # Delete

Action Endpoints (for complex operations):
POST   /api/conversations/{id}/message         # Send message
POST   /api/conversations/{id}/message/stream  # Send message (streaming)
POST   /api/conversations/{id}/duplicate       # Duplicate conversation
```

- Use standard REST verbs for CRUD operations
- Use POST with action verb for complex operations
- Streaming endpoints should be explicit (`/stream` suffix)

#### Principle 8: Consistent Response Shapes

```python
# Success response
{
    "id": "...",
    "data": {...}
}

# Error response
{
    "detail": "Error message"
}

# Streaming event
{
    "type": "event_type",
    "data": {...}
}
```

### 3.4 Frontend Architecture Principles

#### Principle 9: Component Hierarchy Mirrors Data Flow

```
App (orchestration & state)
├── Sidebar (conversation list state)
│   └── ConversationItem (single conversation metadata)
└── ChatInterface (current conversation state)
    ├── MessageList
    │   ├── UserMessage
    │   └── AssistantMessage
    │       ├── Stage1 (individual responses)
    │       ├── Stage2 (rankings)
    │       └── Stage3 (synthesis)
    └── ChatInput (input state)
```

- Parent components own and pass down state
- Children receive props and emit events upward
- Avoid prop drilling more than 2-3 levels (consider context)

#### Principle 10: Colocation of Concerns

Keep related code together:
```
components/
├── Stage1/
│   ├── Stage1.jsx          # Component
│   ├── Stage1.css          # Styles
│   └── Stage1.test.jsx     # Tests
```

### 3.5 Error Handling Principles

#### Principle 11: Fail Gracefully, Log Completely

```python
# Backend pattern
try:
    result = await external_operation()
except ExternalServiceError as e:
    logger.error(f"External service failed: {e}", exc_info=True)
    return {"status": "error", "message": "Service temporarily unavailable"}
```

```javascript
// Frontend pattern
try {
    await api.sendMessage(content);
} catch (error) {
    console.error('Failed to send message:', error);
    showUserFriendlyError("Couldn't send your message. Please try again.");
    rollbackOptimisticUpdate();
}
```

#### Principle 12: Model Failure Resilience

The council process should continue even if individual models fail:
```python
# Good: Continue with remaining models
results = []
for model in models:
    try:
        result = await query_model(model)
        results.append({"model": model, "status": "success", ...})
    except Exception:
        results.append({"model": model, "status": "error", ...})

# Process continues with successful results
```

### 3.6 Security Principles

#### Principle 13: Validate at Boundaries

```python
# API boundary validation
@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    # Validate input
    if not request.content.strip():
        raise HTTPException(400, "Message content required")

    # Validate resource exists
    conversation = storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(404, "Conversation not found")
```

#### Principle 14: Secrets Stay on Backend

- API keys (OPENROUTER_API_KEY) are never exposed to frontend
- All LLM communication goes through backend
- Frontend never directly calls external APIs

### 3.7 Testing Principles

#### Principle 15: Test at Appropriate Levels

```
Unit Tests:
├── Backend: council.py functions, storage.py functions
└── Frontend: Individual component rendering

Integration Tests:
├── Backend: API endpoints with mock LLM responses
└── Frontend: User flows with mock API

E2E Tests (optional):
└── Full user journeys with real or mocked services
```

#### Principle 16: Mock External Dependencies

```python
# Test council logic without actual LLM calls
@pytest.fixture
def mock_openrouter(monkeypatch):
    async def mock_query(model, messages):
        return {"content": f"Mock response from {model}"}
    monkeypatch.setattr("backend.openrouter.query_model", mock_query)
```

### 3.8 Performance Principles

#### Principle 17: Parallel When Possible

```python
# Good: Parallel model queries
tasks = [query_model(m) for m in models]
results = await asyncio.gather(*tasks, return_exceptions=True)

# Bad: Sequential queries
results = []
for model in models:
    result = await query_model(model)  # Wastes time
    results.append(result)
```

#### Principle 18: Minimize Re-renders

```javascript
// Good: Stable callback references
const handleClick = useCallback(() => {...}, [dependencies]);

// Good: Memoize expensive computations
const sortedConversations = useMemo(() =>
    conversations.sort(...), [conversations]
);
```

---

## 4. Quick Reference

### Data Flow Checklist

When implementing a new feature:

- [ ] Does user input trigger an API call?
- [ ] Is the API endpoint RESTful?
- [ ] For long operations (>2s), is streaming implemented?
- [ ] Is optimistic update appropriate for this action?
- [ ] Is state updated through proper channels (setState, not direct mutation)?
- [ ] Is the backend storage updated?
- [ ] Are errors handled gracefully?

### Storage Checklist

When modifying data persistence:

- [ ] Is the data structure documented?
- [ ] Is backward compatibility maintained?
- [ ] Are file operations async (or planned to be)?
- [ ] Is the index updated (when implemented)?
- [ ] Are edge cases handled (missing files, corruption)?

### New Endpoint Checklist

When adding a new API endpoint:

- [ ] Is it following REST conventions?
- [ ] Are request/response models defined (Pydantic)?
- [ ] Is input validated?
- [ ] Are errors returned with appropriate HTTP status codes?
- [ ] Is the endpoint tested?

---

*Document Version: 1.0*
*Last Updated: 2025-12-29*
