# Architecture Refactor Assessment Report

**Date:** Friday, January 2, 2026  
**Status:** 🟡 **Partially Compliant / In-Progress**  
**Primary Issue:** Significant logic duplication between the new `CouncilOrchestrator` and the legacy `council.py` module, violating the "Single Source of Truth" principle of Phase 4.

---

## 1. Phase-by-Phase Assessment

### Phase 1: Domain Modeling & Metadata Persistence
**Status:** ✅ **Compliant**
*   **Implementation:** Pydantic models in `backend/domain/models.py` are correctly implemented.
*   **Result:** The critical `AssistantMetadata` field (containing `label_to_model` and `aggregate_rankings`) is present, resolving the "amnesia" bug where rankings were lost on reload.

### Phase 2: The Blob-Store Split
**Status:** ✅ **Compliant**
*   **Implementation:** `BlobStore` is implemented in `backend/infrastructure/blob_store.py`.
*   **Result:** `UserMessage` correctly utilizes `Attachment` objects with `file_reference_id`s. Large file contents are stored in `data/blobs/`, keeping the conversation JSON files lightweight and performant.

### Phase 3: Infrastructure Abstraction (Repository Pattern)
**Status:** ✅ **Compliant**
*   **Ports:** `ConversationRepository` and `LLMProvider` interfaces are clearly defined in `backend/ports.py`.
*   **Adapters:** `JsonConversationRepository` and `OpenRouterAdapter` correctly implement these interfaces, isolating the filesystem and external API logic.
*   **Injection:** `main.py` correctly instantiates these adapters and injects them into the `CouncilOrchestrator`.

### Phase 4: Service Layer Unification
**Status:** ❌ **Non-Compliant / Technical Debt**
The intention was to **move** orchestration logic to the `CouncilOrchestrator`. Instead, logic was **copied and modified**, creating parallel code paths.

*   **Logic Duplication:** Both `CouncilOrchestrator` and `backend/council.py` contain parallel execution logic for Stage 1 and Stage 2.
*   **Legacy Dependencies:** `backend/council.py` still relies on the old `backend/openrouter.py` logic in some functions, bypassing the new Adapter pattern.
*   **Bypassed Orchestration:** The `chairman_followup` logic is imported directly from the legacy `council.py` into `main.py`, completely bypassing the Service layer.

---

## 2. Identified Straying from Refactor Plan

| Issue | Severity | Description |
| :--- | :--- | :--- |
| **Orchestration Fragmentation** | High | The "while loop" of the council process exists in both `CouncilOrchestrator` and `council.py`. |
| **Zombie Logic** | Medium | `chairman_followup` remains in `council.py` and still performs its own network calls rather than using the `LLMProvider` adapter. |
| **Leakage in Interface** | Medium | `main.py` route handlers contain logic for message history inspection that should be encapsulated within the `CouncilOrchestrator`. |

---

## 3. Corrective Action Plan

To align the codebase with the original refactor goal of a clean Hexagonal Architecture:

1.  **Purify `council.py`:** Strip all `async/await` and network-related code. Transform it into a pure utility module for prompt building and text parsing (e.g., `parse_ranking_from_text`).
2.  **Centralize Orchestration:** Move the `chairman_followup` logic into the `CouncilOrchestrator` class.
3.  **Encapsulate State in Service:** Ensure `main.py` only calls the Orchestrator, passing minimal IDs. The Orchestrator should handle message history lookup via the Repository.
4.  **Eliminate Legacy Modules:** Delete `backend/openrouter.py` once all calls are routed through the `OpenRouterAdapter`.
