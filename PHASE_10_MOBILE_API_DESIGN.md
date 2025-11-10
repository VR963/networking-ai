# Phase 10: Mobile API - Design Document

**Date**: 2025-11-08
**Status**: Design Phase
**Version**: 1.0

---

## Executive Summary

Phase 10 introduces mobile-optimized API endpoints for iOS and Android applications. The Mobile API provides:
- **Bandwidth-optimized responses** (compact payloads)
- **Cursor-based pagination** for efficient scrolling
- **Device management** for push notifications
- **Enhanced authentication** with token refresh
- **Offline-first considerations** with versioning
- **Real-time updates** via WebSocket optimization

---

## Design Principles

### 1. Mobile-First Optimization
- **Small Payloads**: Only essential fields in responses
- **Pagination**: All list endpoints support cursor-based pagination
- **Compression**: gzip compression for responses
- **Image Optimization**: Multiple resolutions for avatars/photos
- **Caching**: ETags and Last-Modified headers

### 2. Battery & Bandwidth Efficiency
- **Batch Operations**: Reduce number of API calls
- **Conditional Requests**: 304 Not Modified support
- **Efficient Polling**: Long-polling or WebSocket for real-time
- **Background Sync**: Queue operations for batch processing

### 3. Offline Support
- **Optimistic Updates**: Client-side state management
- **Conflict Resolution**: Version-based conflict detection
- **Sync Queue**: Queue operations when offline

### 4. Security
- **Short-lived Access Tokens**: 15-minute expiry
- **Refresh Tokens**: 30-day expiry, device-bound
- **Device Registration**: Track active devices per user
- **Rate Limiting**: Prevent abuse

---

## API Architecture

### Base URL
```
/api/v1/mobile/*
```

All mobile endpoints are namespaced under `/mobile` to:
- Separate mobile-specific logic from web API
- Enable different versioning strategies
- Allow mobile-specific middleware (auth, rate limiting)

### Response Format

**Standard Success Response:**
```json
{
  "data": { ... },
  "meta": {
    "version": "1.0",
    "timestamp": "2025-11-08T12:00:00Z"
  },
  "links": {
    "self": "/api/v1/mobile/jobs/123",
    "next": null
  }
}
```

**Paginated Response:**
```json
{
  "data": [ ... ],
  "meta": {
    "cursor": {
      "next": "eyJpZCI6MTAwfQ==",
      "has_more": true
    },
    "count": 20
  },
  "links": {
    "next": "/api/v1/mobile/jobs?cursor=eyJpZCI6MTAwfQ=="
  }
}
```

**Error Response:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid email format",
    "details": {
      "field": "email",
      "constraint": "format"
    }
  },
  "meta": {
    "request_id": "req_abc123"
  }
}
```

---

## Core Endpoints

### 1. Authentication (`/mobile/auth`)

#### POST `/mobile/auth/register`
**Purpose**: Register new user account
**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "full_name": "John Doe",
  "role": "jobseeker",
  "device": {
    "platform": "ios",
    "device_id": "device_abc123",
    "push_token": "fcm_token_xyz"
  }
}
```

**Response (201 Created):**
```json
{
  "data": {
    "user": {
      "id": 123,
      "email": "user@example.com",
      "full_name": "John Doe",
      "role": "jobseeker",
      "avatar_url": null
    },
    "tokens": {
      "access_token": "eyJhbGc...",
      "refresh_token": "eyJhbGc...",
      "expires_in": 900
    }
  }
}
```

#### POST `/mobile/auth/login`
**Purpose**: Authenticate user
**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "device": {
    "platform": "android",
    "device_id": "device_xyz789",
    "push_token": "fcm_token_abc"
  }
}
```

**Response (200 OK):**
```json
{
  "data": {
    "user": { ... },
    "tokens": { ... }
  }
}
```

#### POST `/mobile/auth/refresh`
**Purpose**: Refresh access token
**Request:**
```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Response (200 OK):**
```json
{
  "data": {
    "access_token": "eyJhbGc...",
    "expires_in": 900
  }
}
```

#### POST `/mobile/auth/logout`
**Purpose**: Logout and invalidate tokens
**Request:**
```json
{
  "device_id": "device_abc123"
}
```

**Response (204 No Content)**

---

### 2. Job Search (`/mobile/jobs`)

#### GET `/mobile/jobs`
**Purpose**: Search jobs with mobile-optimized filters
**Query Parameters:**
- `q` (string): Search query
- `location` (string): Location filter
- `job_type` (enum): full_time, part_time, contract
- `experience_level` (enum): entry, mid, senior
- `cursor` (string): Pagination cursor
- `limit` (int, default: 20, max: 50)

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": 123,
      "title": "Senior Software Engineer",
      "company": {
        "id": 456,
        "name": "TechCorp",
        "logo_url": "https://..."
      },
      "location": "San Francisco, CA",
      "job_type": "full_time",
      "experience_level": "senior",
      "salary_range": {
        "min": 150000,
        "max": 200000,
        "currency": "USD"
      },
      "posted_at": "2025-11-08T10:00:00Z",
      "is_saved": false,
      "is_applied": false,
      "match_score": 0.85
    }
  ],
  "meta": {
    "cursor": {
      "next": "eyJpZCI6MTIzfQ==",
      "has_more": true
    },
    "count": 20
  }
}
```

#### GET `/mobile/jobs/{job_id}`
**Purpose**: Get detailed job information
**Response (200 OK):**
```json
{
  "data": {
    "id": 123,
    "title": "Senior Software Engineer",
    "description": "Full job description...",
    "company": {
      "id": 456,
      "name": "TechCorp",
      "logo_url": "https://...",
      "description": "Company description...",
      "size": "100-500",
      "industry": "Technology"
    },
    "requirements": {
      "required_skills": ["Python", "FastAPI", "PostgreSQL"],
      "preferred_skills": ["Docker", "AWS"],
      "min_experience_years": 5
    },
    "benefits": ["Health Insurance", "401k", "Remote Work"],
    "application_count": 42,
    "is_saved": false,
    "is_applied": false,
    "match_score": 0.85,
    "match_reasons": [
      "Strong skills match (90%)",
      "Experience level matches",
      "Location preference matches"
    ]
  }
}
```

#### POST `/mobile/jobs/{job_id}/save`
**Purpose**: Save job for later
**Response (201 Created):**
```json
{
  "data": {
    "saved_at": "2025-11-08T12:00:00Z"
  }
}
```

#### DELETE `/mobile/jobs/{job_id}/save`
**Purpose**: Unsave job
**Response (204 No Content)**

---

### 3. Applications (`/mobile/applications`)

#### POST `/mobile/applications`
**Purpose**: Submit job application
**Request:**
```json
{
  "job_id": 123,
  "cover_letter": "I am excited to apply...",
  "resume_id": 456,
  "answers": [
    {
      "question_id": 1,
      "answer": "5 years"
    }
  ]
}
```

**Response (201 Created):**
```json
{
  "data": {
    "id": 789,
    "job_id": 123,
    "status": "submitted",
    "submitted_at": "2025-11-08T12:00:00Z",
    "job": {
      "title": "Senior Software Engineer",
      "company": { ... }
    }
  }
}
```

#### GET `/mobile/applications`
**Purpose**: Get user's applications
**Query Parameters:**
- `status` (enum): submitted, screening, interviewing, offered, rejected
- `cursor` (string)
- `limit` (int)

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": 789,
      "job": {
        "id": 123,
        "title": "Senior Software Engineer",
        "company": { ... }
      },
      "status": "interviewing",
      "submitted_at": "2025-11-08T12:00:00Z",
      "last_updated": "2025-11-10T15:30:00Z",
      "next_step": {
        "type": "interview",
        "scheduled_at": "2025-11-15T10:00:00Z",
        "interviewer": "Jane Smith"
      }
    }
  ],
  "meta": { ... }
}
```

#### GET `/mobile/applications/{application_id}`
**Purpose**: Get application details
**Response (200 OK):**
```json
{
  "data": {
    "id": 789,
    "job": { ... },
    "status": "interviewing",
    "timeline": [
      {
        "stage": "submitted",
        "timestamp": "2025-11-08T12:00:00Z",
        "note": "Application received"
      },
      {
        "stage": "screening",
        "timestamp": "2025-11-09T14:00:00Z",
        "note": "Passed initial screening"
      }
    ],
    "interviews": [
      {
        "id": 123,
        "stage": "technical",
        "scheduled_at": "2025-11-15T10:00:00Z",
        "interviewer": "Jane Smith",
        "location": "Video call",
        "status": "scheduled"
      }
    ],
    "messages": [
      {
        "id": 456,
        "from": "recruiter",
        "message": "Congratulations! We'd like to schedule...",
        "timestamp": "2025-11-09T14:00:00Z"
      }
    ]
  }
}
```

---

### 4. Profile (`/mobile/profile`)

#### GET `/mobile/profile`
**Purpose**: Get user profile
**Response (200 OK):**
```json
{
  "data": {
    "id": 123,
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "jobseeker",
    "avatar_url": "https://...",
    "headline": "Senior Software Engineer",
    "location": "San Francisco, CA",
    "resume": {
      "id": 456,
      "filename": "resume.pdf",
      "uploaded_at": "2025-11-01T12:00:00Z"
    },
    "skills": ["Python", "FastAPI", "PostgreSQL"],
    "experience_years": 5,
    "profile_completeness": 0.85,
    "stats": {
      "applications_submitted": 15,
      "interviews_scheduled": 3,
      "profile_views": 42
    }
  }
}
```

#### PATCH `/mobile/profile`
**Purpose**: Update profile
**Request:**
```json
{
  "full_name": "John Doe",
  "headline": "Senior Software Engineer",
  "location": "San Francisco, CA",
  "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"]
}
```

**Response (200 OK):**
```json
{
  "data": { ... }
}
```

#### POST `/mobile/profile/avatar`
**Purpose**: Upload profile avatar
**Content-Type**: multipart/form-data
**Response (200 OK):**
```json
{
  "data": {
    "avatar_url": "https://..."
  }
}
```

#### POST `/mobile/profile/resume`
**Purpose**: Upload resume
**Content-Type**: multipart/form-data
**Response (201 Created):**
```json
{
  "data": {
    "id": 456,
    "filename": "resume.pdf",
    "uploaded_at": "2025-11-08T12:00:00Z",
    "parsed_data": {
      "skills": ["Python", "FastAPI"],
      "experience_years": 5
    }
  }
}
```

---

### 5. Notifications (`/mobile/notifications`)

#### GET `/mobile/notifications`
**Purpose**: Get user notifications
**Query Parameters:**
- `unread_only` (bool, default: false)
- `cursor` (string)
- `limit` (int)

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": 123,
      "type": "application_update",
      "title": "Application Update",
      "message": "Your application for Senior Software Engineer has been reviewed",
      "data": {
        "application_id": 789,
        "job_id": 123,
        "new_status": "interviewing"
      },
      "is_read": false,
      "created_at": "2025-11-08T12:00:00Z"
    }
  ],
  "meta": {
    "unread_count": 5
  }
}
```

#### POST `/mobile/notifications/{notification_id}/read`
**Purpose**: Mark notification as read
**Response (204 No Content)**

#### POST `/mobile/notifications/read-all`
**Purpose**: Mark all notifications as read
**Response (204 No Content)**

#### GET `/mobile/notifications/settings`
**Purpose**: Get notification preferences
**Response (200 OK):**
```json
{
  "data": {
    "email": {
      "application_updates": true,
      "interview_reminders": true,
      "new_matches": false
    },
    "push": {
      "application_updates": true,
      "interview_reminders": true,
      "new_matches": true
    }
  }
}
```

#### PATCH `/mobile/notifications/settings`
**Purpose**: Update notification preferences
**Request:**
```json
{
  "push": {
    "application_updates": true,
    "interview_reminders": true,
    "new_matches": false
  }
}
```

**Response (200 OK)**

---

### 6. Messaging (`/mobile/messages`)

#### GET `/mobile/messages/conversations`
**Purpose**: Get user's conversations
**Response (200 OK):**
```json
{
  "data": [
    {
      "id": 123,
      "participant": {
        "id": 456,
        "name": "Jane Smith",
        "role": "recruiter",
        "avatar_url": "https://...",
        "company": "TechCorp"
      },
      "last_message": {
        "text": "Looking forward to the interview!",
        "timestamp": "2025-11-08T12:00:00Z",
        "is_from_me": true
      },
      "unread_count": 2,
      "related_to": {
        "type": "application",
        "id": 789,
        "job_title": "Senior Software Engineer"
      }
    }
  ]
}
```

#### GET `/mobile/messages/conversations/{conversation_id}`
**Purpose**: Get conversation messages
**Response (200 OK):**
```json
{
  "data": {
    "id": 123,
    "participant": { ... },
    "messages": [
      {
        "id": 1,
        "from_user_id": 123,
        "text": "Thank you for the opportunity!",
        "timestamp": "2025-11-08T11:00:00Z",
        "is_read": true
      },
      {
        "id": 2,
        "from_user_id": 456,
        "text": "Looking forward to the interview!",
        "timestamp": "2025-11-08T12:00:00Z",
        "is_read": false
      }
    ]
  }
}
```

#### POST `/mobile/messages/conversations/{conversation_id}/messages`
**Purpose**: Send message
**Request:**
```json
{
  "text": "Thank you for the update!"
}
```

**Response (201 Created):**
```json
{
  "data": {
    "id": 3,
    "text": "Thank you for the update!",
    "timestamp": "2025-11-08T13:00:00Z"
  }
}
```

---

### 7. Devices (`/mobile/devices`)

#### POST `/mobile/devices`
**Purpose**: Register device for push notifications
**Request:**
```json
{
  "device_id": "device_abc123",
  "platform": "ios",
  "push_token": "fcm_token_xyz",
  "app_version": "1.0.0",
  "os_version": "iOS 17.0"
}
```

**Response (201 Created):**
```json
{
  "data": {
    "id": 789,
    "device_id": "device_abc123",
    "registered_at": "2025-11-08T12:00:00Z"
  }
}
```

#### DELETE `/mobile/devices/{device_id}`
**Purpose**: Unregister device
**Response (204 No Content)**

#### GET `/mobile/devices`
**Purpose**: List user's registered devices
**Response (200 OK):**
```json
{
  "data": [
    {
      "id": 789,
      "device_id": "device_abc123",
      "platform": "ios",
      "app_version": "1.0.0",
      "last_active": "2025-11-08T12:00:00Z"
    }
  ]
}
```

---

## Database Schema Changes

### New Tables

#### `mobile_devices`
```sql
CREATE TABLE mobile_devices (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id VARCHAR(255) NOT NULL UNIQUE,
    platform VARCHAR(20) NOT NULL, -- 'ios', 'android'
    push_token VARCHAR(500),
    app_version VARCHAR(50),
    os_version VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    last_active TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_devices (user_id),
    INDEX idx_device_id (device_id)
);
```

#### `refresh_tokens`
```sql
CREATE TABLE refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id VARCHAR(255) REFERENCES mobile_devices(device_id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    is_revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_tokens (user_id),
    INDEX idx_token_hash (token_hash)
);
```

#### `saved_jobs`
```sql
CREATE TABLE saved_jobs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    saved_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, job_id),
    INDEX idx_user_saved_jobs (user_id)
);
```

#### `push_notifications`
```sql
CREATE TABLE push_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id VARCHAR(255) REFERENCES mobile_devices(device_id),
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    data JSONB,
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    opened_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'sent', 'delivered', 'failed'
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_notifications (user_id)
);
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1)
- [ ] Create mobile API router structure
- [ ] Implement mobile response models (Pydantic schemas)
- [ ] Set up cursor-based pagination utility
- [ ] Create mobile authentication middleware
- [ ] Implement refresh token mechanism
- [ ] Add database tables (devices, refresh_tokens, saved_jobs)

### Phase 2: Authentication & Profile (Week 2)
- [ ] Implement `/mobile/auth/*` endpoints
- [ ] Implement device registration
- [ ] Implement `/mobile/profile/*` endpoints
- [ ] Add avatar upload handling
- [ ] Add resume upload with mobile optimization

### Phase 3: Job Search & Applications (Week 3)
- [ ] Implement `/mobile/jobs/*` endpoints
- [ ] Add mobile-optimized job search
- [ ] Implement saved jobs functionality
- [ ] Implement `/mobile/applications/*` endpoints
- [ ] Add application submission flow

### Phase 4: Notifications & Messaging (Week 4)
- [ ] Implement `/mobile/notifications/*` endpoints
- [ ] Set up push notification infrastructure
- [ ] Implement `/mobile/messages/*` endpoints
- [ ] Add real-time messaging optimization

### Phase 5: Testing & Documentation (Week 5)
- [ ] Write comprehensive unit tests
- [ ] Write integration tests
- [ ] Create API documentation
- [ ] Performance testing
- [ ] Security audit

---

## Performance Targets

- **Response Time**: < 200ms for 95th percentile
- **Payload Size**: < 50KB for list endpoints
- **Pagination**: Support 1000+ items efficiently
- **Concurrent Users**: Support 10,000+ simultaneous connections
- **Battery Impact**: Minimal (use push instead of polling)

---

## Security Considerations

1. **Token Management**
   - Access tokens: 15-minute expiry
   - Refresh tokens: 30-day expiry
   - Automatic token rotation
   - Device-bound refresh tokens

2. **Rate Limiting**
   - Authentication: 5 requests/minute
   - API calls: 100 requests/minute per user
   - File uploads: 10 requests/hour

3. **Data Protection**
   - HTTPS only
   - Sensitive fields excluded from mobile responses
   - PII encryption at rest

---

## Success Metrics

1. **Performance**
   - 95% of API calls complete in < 200ms
   - 99.9% uptime

2. **User Experience**
   - < 100ms perceived latency with optimistic updates
   - < 1% error rate

3. **Adoption**
   - 80% of new users use mobile app
   - 60% of daily active users on mobile

---

## Next Steps

1. Review and approve design
2. Create database migrations
3. Implement Phase 1 infrastructure
4. Begin endpoint implementation
5. Write tests alongside development

---

**Status**: Ready for implementation ✅
