# Firebase Authentication & Cloud Sync - Product Specification

## Overview

Add Google Account authentication via Firebase to Symposia, replacing local storage with cloud-based Firestore for all user data. This enables users to access their conversations from any device while securing the application to authorized users only.

## Goals

1. **Secure Access**: Only authenticated users with existing Firebase accounts can use the app
2. **Cloud Sync**: All user data (conversations, settings) stored in Firestore
3. **Cross-Device Access**: Users can access their data from any browser
4. **Clean Architecture**: Remove all localStorage usage for user data

## User Experience

### Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    User visits app                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Is user authenticated?                         │
└─────────────────────────────────────────────────────────────┘
                    │                    │
                   No                   Yes
                    │                    │
                    ▼                    ▼
┌──────────────────────────┐  ┌──────────────────────────────┐
│   Show Login Screen      │  │   Load App with User Data    │
│   - Google Sign-In btn   │  │   - Fetch conversations      │
│   - App branding         │  │   - Apply user settings      │
└──────────────────────────┘  └──────────────────────────────┘
                    │
                    ▼
┌──────────────────────────┐
│  Google OAuth Popup      │
│  (Firebase handles)      │
└──────────────────────────┘
                    │
                    ▼
┌──────────────────────────┐
│  Account exists in       │
│  Firebase?               │
└──────────────────────────┘
          │           │
         Yes          No
          │           │
          ▼           ▼
┌─────────────┐  ┌─────────────────────────────┐
│ Login OK    │  │ Show "Access Denied"        │
│ → Load App  │  │ "Contact admin for access"  │
└─────────────┘  └─────────────────────────────┘
```

### Login Screen Design

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                                                             │
│                    [Symposia Logo]                          │
│                                                             │
│                      "Symposia"                             │
│           "Collaborative AI Deliberation"                   │
│                                                             │
│              ┌─────────────────────────┐                    │
│              │  🔵 Sign in with Google │                    │
│              └─────────────────────────┘                    │
│                                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Authenticated App Header

Add user indicator to the app header area:

```
┌─────────────────────────────────────────────────────────────┐
│ [Sidebar]  │  Conversation Title            [User Avatar ▼] │
│            │                                 - user@email   │
│            │                                 - Sign Out     │
└─────────────────────────────────────────────────────────────┘
```

## Data Model

### Firestore Collections

```
users/
  {userId}/
    settings: {
      theme: "light" | "dark" | "system",
      modelMode: "fast" | "smart"
    }
    
    conversations/
      {conversationId}/
        id: string
        created_at: timestamp
        title: string
        is_pinned: boolean
        is_archived: boolean
        has_unread: boolean
        messages: [
          {
            role: "user" | "assistant",
            content: string,  // for user messages
            files: [...],     // for user messages
            stage1: [...],    // for assistant messages
            stage2: [...],
            stage3: {...},
            metadata: {...}
          }
        ]
```

### Security Rules

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can only access their own data
    match /users/{userId}/{document=**} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Deny all other access
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

## Backend Changes

### Authentication Middleware

All API endpoints must verify Firebase ID tokens:

1. Frontend includes `Authorization: Bearer <idToken>` header
2. Backend validates token with Firebase Admin SDK
3. Extract `userId` from validated token
4. Use `userId` to scope all data operations

### Endpoint Changes

| Endpoint | Change |
|----------|--------|
| `GET /api/conversations` | Requires auth, scoped to user |
| `POST /api/conversations` | Requires auth, creates under user |
| `GET /api/conversations/{id}` | Requires auth, verifies ownership |
| `PATCH /api/conversations/{id}` | Requires auth, verifies ownership |
| `DELETE /api/conversations/{id}` | Requires auth, verifies ownership |
| `POST /api/conversations/{id}/message` | Requires auth, verifies ownership |
| `POST /api/conversations/{id}/message/stream` | Requires auth, verifies ownership |
| `GET /api/user/settings` | **NEW** - Get user settings |
| `PATCH /api/user/settings` | **NEW** - Update user settings |

## Frontend Changes

### New Components

1. **`AuthProvider`** - Context for authentication state
2. **`LoginScreen`** - Full-page login UI
3. **`UserMenu`** - Avatar dropdown with sign-out
4. **`ProtectedRoute`** - Wrapper ensuring authentication

### Modified Components

1. **`App.jsx`** - Wrap with AuthProvider, show LoginScreen or main app
2. **`api.js`** - Add auth token to all requests
3. **`ThemeContext.jsx`** - Sync with Firestore instead of localStorage
4. **`ModelModeContext.jsx`** - Sync with Firestore instead of localStorage

### Removed localStorage Usage

| Key | Replacement |
|-----|-------------|
| `symposia-theme` | Firestore `/users/{uid}/settings.theme` |
| `symposia-model-mode` | Firestore `/users/{uid}/settings.modelMode` |

## Error Handling

### Authentication Errors

| Scenario | User-Facing Message |
|----------|--------------------|
| Google sign-in cancelled | (Silent, return to login screen) |
| Account not authorized | "Access denied. Please contact the administrator." |
| Network error during auth | "Unable to connect. Please check your internet." |
| Token expired mid-session | Auto-refresh, or redirect to login |

### API Errors

| HTTP Status | Handling |
|-------------|----------|
| 401 Unauthorized | Redirect to login screen |
| 403 Forbidden | Show "Access denied" error |
| 5xx Server Error | Show retry option |

## Session Behavior

- Firebase handles session persistence automatically
- Default: `browserLocalPersistence` (survives browser close)
- Token auto-refresh handled by Firebase SDK
- No explicit timeout

## Migration Strategy

1. **No migration** - existing local data is discarded
2. On first load, check for auth state
3. If not authenticated, show login screen
4. New users start with empty conversation list

## Success Criteria

1. ✅ Unauthenticated users cannot access any app functionality
2. ✅ Unauthenticated users cannot call any API endpoints
3. ✅ Users see their own conversations only
4. ✅ Settings (theme, model mode) persist across devices
5. ✅ No user data in localStorage (except Firebase internals)
6. ✅ Smooth login/logout experience
7. ✅ All existing tests pass (with auth mocked)
8. ✅ New tests cover auth flows

## Out of Scope

- Offline support
- Account creation flow (handled by Firebase console)
- Password reset (Google handles this)
- Multi-factor authentication
- Shared conversations between users
