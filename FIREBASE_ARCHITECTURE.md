# Firebase Auth & Sync - Architecture & Implementation Plan

## Architecture Overview

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                         │
├─────────────────────────────────────────────────────────────────┤
│  AuthContext ──► Firebase Auth SDK ──► Google OAuth             │
│       │                                                         │
│       ▼                                                         │
│  App (protected) ──► api.js (with auth headers)                 │
│       │                                                         │
│  SettingsContext ◄──► Firestore SDK (direct for settings)      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP + Bearer Token
┌─────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                        │
├─────────────────────────────────────────────────────────────────┤
│  Auth Middleware ──► Firebase Admin SDK (verify token)          │
│       │                                                         │
│       ▼                                                         │
│  Endpoints ──► FirestoreRepository ──► Firestore                │
└─────────────────────────────────────────────────────────────────┘
```

### Key Decisions

1. **Settings sync via Frontend Firestore SDK** - Direct client access for low-latency settings
2. **Conversations via Backend** - All conversation CRUD goes through backend for consistency
3. **Firebase Admin SDK on Backend** - Token verification and Firestore writes
4. **No localStorage for user data** - All persisted via Firestore

## Implementation Plan (TDD)

### Phase 1: Firebase Setup
- [ ] Create Firestore database in pyronic-apps
- [ ] Configure security rules
- [ ] Get Firebase config for frontend
- [ ] Get service account for backend

### Phase 2: Backend Auth (Test First)
- [ ] Write tests for auth middleware
- [ ] Implement Firebase Admin SDK integration
- [ ] Add auth dependency to all endpoints
- [ ] Write tests for Firestore repository
- [ ] Implement FirestoreConversationRepository

### Phase 3: Frontend Auth (Test First)
- [ ] Write tests for AuthContext
- [ ] Implement Firebase Auth setup
- [ ] Implement LoginScreen component
- [ ] Implement UserMenu component
- [ ] Update api.js to include auth headers

### Phase 4: Settings Sync
- [ ] Write tests for settings sync
- [ ] Update ThemeContext to use Firestore
- [ ] Update ModelModeContext to use Firestore

### Phase 5: Integration & Cleanup
- [ ] Remove JSON repository usage
- [ ] Remove localStorage usage
- [ ] End-to-end testing
- [ ] Update all existing tests with auth mocks

## Firebase Project Setup

Project: `pyronic-apps`
Database: `llm-council` (to be created)
Auth: Google provider (already configured)
