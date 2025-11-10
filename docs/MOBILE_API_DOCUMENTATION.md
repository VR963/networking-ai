# Mobile API Documentation

**Version**: 1.0
**Base URL**: `https://api.yourdomain.com/api/v1/mobile`
**Protocol**: HTTPS only

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [Error Handling](#error-handling)
5. [Rate Limiting](#rate-limiting)
6. [Integration Guide](#integration-guide)

---

## Overview

The Mobile API provides mobile-optimized endpoints for iOS and Android applications. All responses are designed to minimize bandwidth usage while providing comprehensive functionality.

### Key Features
- **JWT Authentication** - Secure token-based auth
- **Cursor Pagination** - Efficient scrolling for mobile
- **Push Notifications** - FCM/APNS support
- **Offline Support** - Optimistic updates
- **Rate Limiting** - 100 requests/minute per user

###Response Format

All successful responses follow this structure:
```json
{
  "data": { ...  },
  "meta": {
    "version": "1.0",
    "timestamp": "2025-11-08T12:00:00Z"
  },
  "links": {
    "self": "/api/v1/mobile/resource"
  }
}
```

Error responses:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  },
  "meta": {
    "version": "1.0",
    "timestamp": "2025-11-08T12:00:00Z"
  }
}
```

---

## Authentication

### Register

**Endpoint**: `POST /auth/register`

Register a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe",
  "role": "jobseeker",
  "device": {
    "platform": "ios",
    "device_id": "unique_device_id",
    "push_token": "fcm_or_apns_token",
    "app_version": "1.0.0",
    "os_version": "iOS 17.0"
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
      "avatar_url": null,
      "created_at": "2025-11-08T12:00:00Z"
    },
    "tokens": {
      "access_token": "eyJhbGc...",
      "refresh_token": "eyJhbGc...",
      "token_type": "bearer",
      "expires_in": 900
    }
  }
}
```

### Login

**Endpoint**: `POST /auth/login`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "device": { ... }
}
```

**Response**: Same as registration

### Refresh Token

**Endpoint**: `POST /auth/refresh`

**Request:**
```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Response:**
```json
{
  "data": {
    "access_token": "new_token",
    "token_type": "bearer",
    "expires_in": 900
  }
}
```

### Logout

**Endpoint**: `POST /auth/logout`

**Headers**: `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "device_id": "unique_device_id"
}
```

**Response**: `204 No Content`

---

## API Endpoints

### Jobs

#### Search Jobs

**Endpoint**: `GET /jobs`

**Headers**: `Authorization: Bearer {access_token}`

**Query Parameters:**
- `q` (string): Search query
- `location` (string): Location filter
- `job_type` (string): full_time, part_time, contract, internship
- `experience_level` (string): entry, mid, senior, lead, executive
- `cursor` (string): Pagination cursor
- `limit` (int): Page size (1-50, default: 20)

**Response:**
```json
{
  "data": {
    "data": [
      {
        "id": 1,
        "title": "Senior Software Engineer",
        "company": {
          "id": 10,
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
        "next": "eyJpZCI6MTAwfQ==",
        "has_more": true
      },
      "count": 20
    }
  }
}
```

#### Get Job Details

**Endpoint**: `GET /jobs/{job_id}`

**Headers**: `Authorization: Bearer {access_token}`

**Response**: Full job details including description, requirements, benefits

#### Save Job

**Endpoint**: `POST /jobs/{job_id}/save`

**Headers**: `Authorization: Bearer {access_token}`

**Response (201 Created):**
```json
{
  "data": {
    "job_id": 1,
    "saved_at": "2025-11-08T12:00:00Z"
  }
}
```

#### Unsave Job

**Endpoint**: `DELETE /jobs/{job_id}/save`

**Headers**: `Authorization: Bearer {access_token}`

**Response**: `204 No Content`

---

### Applications

#### Submit Application

**Endpoint**: `POST /applications`

**Headers**: `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "job_id": 1,
  "cover_letter": "I am excited to apply...",
  "resume_id": 5,
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
    "id": 100,
    "job": { ... },
    "status": "submitted",
    "submitted_at": "2025-11-08T12:00:00Z"
  }
}
```

#### List Applications

**Endpoint**: `GET /applications`

**Headers**: `Authorization: Bearer {access_token}`

**Query Parameters:**
- `status` (string): Filter by status
- `cursor` (string): Pagination cursor
- `limit` (int): Page size

**Response**: Paginated list of applications

#### Get Application Details

**Endpoint**: `GET /applications/{application_id}`

**Headers**: `Authorization: Bearer {access_token}`

**Response**:
```json
{
  "data": {
    "id": 100,
    "job": { ... },
    "status": "interviewing",
    "submitted_at": "2025-11-08T12:00:00Z",
    "timeline": [
      {
        "stage": "submitted",
        "timestamp": "2025-11-08T12:00:00Z",
        "note": "Application received"
      }
    ],
    "interviews": [ ... ],
    "next_step": {
      "type": "interview",
      "scheduled_at": "2025-11-15T10:00:00Z",
      "description": "Technical interview scheduled"
    }
  }
}
```

---

### Profile

#### Get Profile

**Endpoint**: `GET /profile`

**Headers**: `Authorization: Bearer {access_token}`

**Response:**
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

#### Update Profile

**Endpoint**: `PATCH /profile`

**Headers**: `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "headline": "Senior Software Engineer",
  "location": "San Francisco, CA",
  "skills": ["Python", "FastAPI", "PostgreSQL"],
  "experience_years": 5
}
```

**Response**: Updated profile

#### Upload Avatar

**Endpoint**: `POST /profile/avatar`

**Headers**:
- `Authorization: Bearer {access_token}`
- `Content-Type: multipart/form-data`

**Request**: Form data with `file` field

**Response:**
```json
{
  "data": {
    "avatar_url": "https://..."
  }
}
```

#### Upload Resume

**Endpoint**: `POST /profile/resume`

**Headers**:
- `Authorization: Bearer {access_token}`
- `Content-Type: multipart/form-data`

**Request**: Form data with `file` field (PDF, DOC, DOCX)

**Response:**
```json
{
  "data": {
    "id": 1,
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

### Notifications

#### List Notifications

**Endpoint**: `GET /notifications`

**Headers**: `Authorization: Bearer {access_token}`

**Query Parameters:**
- `unread_only` (boolean): Show only unread
- `limit` (int): Page size (1-100)

**Response:**
```json
{
  "data": {
    "data": [
      {
        "id": 1,
        "type": "application_update",
        "title": "Application Update",
        "message": "Your application has been reviewed",
        "data": {
          "application_id": 100,
          "job_id": 1,
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
}
```

#### Mark as Read

**Endpoint**: `POST /notifications/{notification_id}/read`

**Headers**: `Authorization: Bearer {access_token}`

**Response**: `204 No Content`

#### Mark All as Read

**Endpoint**: `POST /notifications/read-all`

**Headers**: `Authorization: Bearer {access_token}`

**Response**: `204 No Content`

#### Get Notification Settings

**Endpoint**: `GET /notifications/settings`

**Headers**: `Authorization: Bearer {access_token}`

**Response:**
```json
{
  "data": {
    "email": {
      "application_updates": true,
      "interview_reminders": true,
      "new_matches": true,
      "messages": true
    },
    "push": {
      "application_updates": true,
      "interview_reminders": true,
      "new_matches": true,
      "messages": true
    }
  }
}
```

#### Update Settings

**Endpoint**: `PATCH /notifications/settings`

**Headers**: `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "push": {
    "application_updates": true,
    "interview_reminders": true,
    "new_matches": false,
    "messages": true
  }
}
```

**Response**: Updated settings

---

### Messages

#### List Conversations

**Endpoint**: `GET /messages/conversations`

**Headers**: `Authorization: Bearer {access_token}`

**Response:**
```json
{
  "data": {
    "data": [
      {
        "id": 1,
        "participant": {
          "id": 50,
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
        "unread_count": 2
      }
    ]
  }
}
```

#### Get Conversation Messages

**Endpoint**: `GET /messages/conversations/{conversation_id}`

**Headers**: `Authorization: Bearer {access_token}`

**Response:**
```json
{
  "data": {
    "id": 1,
    "participant": { ... },
    "messages": [
      {
        "id": 1,
        "from_user_id": 123,
        "text": "Thank you for the opportunity!",
        "timestamp": "2025-11-08T11:00:00Z",
        "is_read": true
      }
    ]
  }
}
```

#### Send Message

**Endpoint**: `POST /messages/conversations/{conversation_id}/messages`

**Headers**: `Authorization: Bearer {access_token}`

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
    "id": 2,
    "text": "Thank you for the update!",
    "timestamp": "2025-11-08T13:00:00Z"
  }
}
```

---

### Devices

#### Register Device

**Endpoint**: `POST /devices`

**Headers**: `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "device_id": "unique_device_id",
  "platform": "ios",
  "push_token": "fcm_or_apns_token",
  "app_version": "1.0.0",
  "os_version": "iOS 17.0"
}
```

**Response (201 Created):**
```json
{
  "data": {
    "id": 1,
    "device_id": "unique_device_id",
    "platform": "ios",
    "app_version": "1.0.0",
    "is_active": true,
    "created_at": "2025-11-08T12:00:00Z"
  }
}
```

#### List Devices

**Endpoint**: `GET /devices`

**Headers**: `Authorization: Bearer {access_token}`

**Response**: List of registered devices

#### Unregister Device

**Endpoint**: `DELETE /devices/{device_id}`

**Headers**: `Authorization: Bearer {access_token}`

**Response**: `204 No Content`

---

## Error Handling

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Missing or invalid auth token |
| `TOKEN_EXPIRED` | 401 | Access token has expired |
| `INVALID_TOKEN` | 401 | Token format is invalid |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `ALREADY_EXISTS` | 409 | Resource already exists |
| `VALIDATION_ERROR` | 400 | Invalid input data |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

### Error Response Example

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
    "version": "1.0",
    "timestamp": "2025-11-08T12:00:00Z",
    "request_id": "req_abc123"
  }
}
```

---

## Rate Limiting

**Limits:**
- **Authentication endpoints**: 5 requests/minute
- **General API**: 100 requests/minute per user
- **File uploads**: 10 requests/hour

**Rate limit headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1699459200
```

**429 Response:**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "details": {
      "limit": 100,
      "window_seconds": 60
    }
  }
}
```

---

## Integration Guide

### iOS Swift Example

```swift
import Foundation

struct AuthTokens: Codable {
    let accessToken: String
    let refreshToken: String
    let tokenType: String
    let expiresIn: Int
}

class APIClient {
    let baseURL = "https://api.yourdomain.com/api/v1/mobile"
    var accessToken: String?

    func register(email: String, password: String, completion: @escaping (Result<AuthTokens, Error>) -> Void) {
        let url = URL(string: "\(baseURL)/auth/register")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body: [String: Any] = [
            "email": email,
            "password": password,
            "full_name": "User Name",
            "role": "jobseeker",
            "device": [
                "platform": "ios",
                "device_id": UIDevice.current.identifierForVendor!.uuidString,
                "push_token": "fcm_token",
                "app_version": Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0",
                "os_version": "iOS \(UIDevice.current.systemVersion)"
            ]
        ]

        request.httpBody = try? JSONSerialization.data(withJSONObject: body)

        URLSession.shared.dataTask(with: request) { data, response, error in
            // Handle response
        }.resume()
    }

    func searchJobs(query: String, completion: @escaping (Result<[Job], Error>) -> Void) {
        guard let token = accessToken else { return }

        let url = URL(string: "\(baseURL)/jobs?q=\(query)")!
        var request = URLRequest(url: url)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        URLSession.shared.dataTask(with: request) { data, response, error in
            // Handle response
        }.resume()
    }
}
```

### Android Kotlin Example

```kotlin
import okhttp3.*
import org.json.JSONObject

class APIClient {
    private val baseURL = "https://api.yourdomain.com/api/v1/mobile"
    private var accessToken: String? = null
    private val client = OkHttpClient()

    fun register(email: String, password: String, callback: Callback) {
        val json = JSONObject().apply {
            put("email", email)
            put("password", password)
            put("full_name", "User Name")
            put("role", "jobseeker")
            put("device", JSONObject().apply {
                put("platform", "android")
                put("device_id", "unique_device_id")
                put("push_token", "fcm_token")
                put("app_version", BuildConfig.VERSION_NAME)
                put("os_version", "Android ${Build.VERSION.RELEASE}")
            })
        }

        val body = RequestBody.create(
            MediaType.parse("application/json"),
            json.toString()
        )

        val request = Request.Builder()
            .url("$baseURL/auth/register")
            .post(body)
            .build()

        client.newCall(request).enqueue(callback)
    }

    fun searchJobs(query: String, callback: Callback) {
        val token = accessToken ?: return

        val request = Request.Builder()
            .url("$baseURL/jobs?q=$query")
            .header("Authorization", "Bearer $token")
            .build()

        client.newCall(request).enqueue(callback)
    }
}
```

---

## Best Practices

### Token Management
1. **Store securely** - Use Keychain (iOS) or KeyStore (Android)
2. **Auto-refresh** - Refresh tokens before expiration
3. **Handle expiration** - Implement token refresh flow
4. **Logout cleanup** - Clear tokens on logout

### Error Handling
1. **Network errors** - Retry with exponential backoff
2. **401 errors** - Trigger re-authentication
3. **Validation errors** - Show field-specific messages
4. **Server errors** - Show generic error message

### Performance
1. **Cache responses** - Reduce API calls
2. **Paginate** - Use cursor pagination
3. **Compress** - Enable gzip
4. **Batch** - Combine related requests

### Security
1. **HTTPS only** - Never use HTTP
2. **Certificate pinning** - Prevent MITM
3. **Input validation** - Validate on client too
4. **Sensitive data** - Don't log tokens

---

## Support

**API Status**: https://status.yourdomain.com
**Issues**: support@yourdomain.com
**Documentation**: https://docs.yourdomain.com

---

**Last Updated**: 2025-11-08
**Version**: 1.0
