# Mobile API Error Code Reference

**Version**: 1.0.0
**Last Updated**: 2025-11-08
**API Version**: v1

---

## Overview

This document provides a comprehensive reference for all error codes, HTTP status codes, and error response formats used in the Networking AI Mobile API.

## Standard Error Response Format

All API errors follow this consistent JSON structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      // Optional additional context
    }
  }
}
```

---

## HTTP Status Codes

### 2xx Success

| Status | Code | Meaning | Usage |
|--------|------|---------|-------|
| 200 | OK | Request successful | GET requests, successful updates |
| 201 | CREATED | Resource created | POST requests creating new resources |
| 204 | NO_CONTENT | Success with no response body | DELETE requests, some POST requests |

### 4xx Client Errors

| Status | Code | Meaning | Usage |
|--------|------|---------|-------|
| 400 | BAD_REQUEST | Invalid request format | Malformed JSON, invalid parameters |
| 401 | UNAUTHORIZED | Authentication required | Missing or invalid token |
| 403 | FORBIDDEN | Access denied | Valid token but insufficient permissions |
| 404 | NOT_FOUND | Resource not found | Requested resource doesn't exist |
| 409 | CONFLICT | Resource conflict | Duplicate email, already applied to job |
| 422 | UNPROCESSABLE_ENTITY | Validation failed | Invalid field values |
| 429 | TOO_MANY_REQUESTS | Rate limit exceeded | Too many requests in time window |

### 5xx Server Errors

| Status | Code | Meaning | Usage |
|--------|------|---------|-------|
| 500 | INTERNAL_SERVER_ERROR | Server error | Unexpected server-side issues |
| 501 | NOT_IMPLEMENTED | Feature not implemented | Endpoint under development |
| 503 | SERVICE_UNAVAILABLE | Service temporarily unavailable | Maintenance mode, overload |

---

## Error Codes by Category

### Authentication Errors (AUTH_*)

| Error Code | HTTP Status | Message | Cause | Solution |
|------------|-------------|---------|-------|----------|
| `AUTH_INVALID_CREDENTIALS` | 401 | Invalid email or password | Wrong email/password combination | Check credentials and retry |
| `AUTH_TOKEN_MISSING` | 401 | Authorization token required | No Authorization header | Include Bearer token in header |
| `AUTH_TOKEN_INVALID` | 401 | Invalid or malformed token | Token corrupted or tampered | Obtain new token via login |
| `AUTH_TOKEN_EXPIRED` | 401 | Access token has expired | Token lifetime exceeded (15min) | Use refresh token to get new access token |
| `AUTH_REFRESH_TOKEN_INVALID` | 401 | Invalid refresh token | Refresh token corrupted, revoked, or expired | Login again to get new tokens |
| `AUTH_REFRESH_TOKEN_EXPIRED` | 401 | Refresh token has expired | Refresh token lifetime exceeded (30 days) | Login again |
| `AUTH_DEVICE_MISMATCH` | 401 | Token device mismatch | Refresh token used from different device | Use token from original device |
| `AUTH_USER_NOT_FOUND` | 401 | User account not found | User deleted or doesn't exist | Check email or create new account |
| `AUTH_ACCOUNT_DISABLED` | 403 | Account has been disabled | Account suspended or banned | Contact support |
| `AUTH_PASSWORD_TOO_WEAK` | 422 | Password does not meet requirements | Password too short or simple | Use 8+ chars with mix of letters/numbers |

### Registration Errors (REG_*)

| Error Code | HTTP Status | Message | Cause | Solution |
|------------|-------------|---------|-------|----------|
| `REG_EMAIL_ALREADY_EXISTS` | 409 | Email already registered | Duplicate email in database | Use different email or login |
| `REG_INVALID_EMAIL` | 422 | Invalid email format | Malformed email address | Check email format |
| `REG_INVALID_ROLE` | 422 | Invalid user role | Role not in [jobseeker, hiring_manager, recruiter] | Use valid role |
| `REG_DEVICE_REQUIRED` | 422 | Device information required | Missing device object in request | Include device info |
| `REG_INVALID_DEVICE_PLATFORM` | 422 | Invalid device platform | Platform not 'ios' or 'android' | Use 'ios' or 'android' |

### Job Errors (JOB_*)

| Error Code | HTTP Status | Message | Cause | Solution |
|------------|-------------|---------|-------|----------|
| `JOB_NOT_FOUND` | 404 | Job not found | Job ID doesn't exist or was deleted | Check job ID |
| `JOB_CLOSED` | 400 | Job posting is closed | Job no longer accepting applications | Find active jobs |
| `JOB_ALREADY_SAVED` | 409 | Job already saved | User already bookmarked this job | No action needed |
| `JOB_NOT_SAVED` | 404 | Job not in saved list | Attempting to unsave job that wasn't saved | No action needed |
| `JOB_INVALID_FILTER` | 422 | Invalid filter value | Job type, experience level, or salary invalid | Use valid filter values |

### Application Errors (APP_*)

| Error Code | HTTP Status | Message | Cause | Solution |
|------------|-------------|---------|-------|----------|
| `APP_NOT_FOUND` | 404 | Application not found | Application ID doesn't exist | Check application ID |
| `APP_ALREADY_EXISTS` | 409 | Already applied to this job | User already has application for this job | View existing application |
| `APP_JOB_CLOSED` | 400 | Cannot apply to closed job | Job posting is closed | Find active jobs |
| `APP_ACCESS_DENIED` | 403 | Cannot access this application | Application belongs to another user | Can only view own applications |
| `APP_INVALID_STATUS` | 422 | Invalid application status | Status not recognized | Use valid status value |
| `APP_COVER_LETTER_TOO_LONG` | 422 | Cover letter exceeds maximum length | Cover letter >10,000 characters | Shorten cover letter |

### Profile Errors (PROF_*)

| Error Code | HTTP Status | Message | Cause | Solution |
|------------|-------------|---------|-------|----------|
| `PROF_NOT_FOUND` | 404 | Profile not found | User has no profile | Profile should auto-create |
| `PROF_INVALID_EXPERIENCE_YEARS` | 422 | Invalid experience years | Negative or excessively large number | Use 0-50 range |
| `PROF_AVATAR_TOO_LARGE` | 400 | Avatar file too large | Image >5MB | Compress image |
| `PROF_AVATAR_INVALID_FORMAT` | 400 | Invalid avatar format | File not JPG, PNG, or WebP | Use supported format |
| `PROF_RESUME_TOO_LARGE` | 400 | Resume file too large | File >10MB | Compress PDF |
| `PROF_RESUME_INVALID_FORMAT` | 400 | Invalid resume format | File not PDF | Convert to PDF |
| `PROF_SKILLS_TOO_MANY` | 422 | Too many skills | More than 50 skills | Limit to top 50 skills |

### Notification Errors (NOTIF_*)

| Error Code | HTTP Status | Message | Cause | Solution |
|------------|-------------|---------|-------|----------|
| `NOTIF_NOT_FOUND` | 404 | Notification not found | Notification ID doesn't exist | Check notification ID |
| `NOTIF_ACCESS_DENIED` | 403 | Cannot access this notification | Notification belongs to another user | Can only access own notifications |
| `NOTIF_ALREADY_READ` | 409 | Notification already marked as read | Notification already read | No action needed |

### Message Errors (MSG_*)

| Error Code | HTTP Status | Message | Cause | Solution |
|------------|-------------|---------|-------|----------|
| `MSG_CONVERSATION_NOT_FOUND` | 404 | Conversation not found | Conversation ID doesn't exist | Check conversation ID |
| `MSG_NOT_PARTICIPANT` | 403 | Not a participant in this conversation | User not part of conversation | Can only access own conversations |
| `MSG_MESSAGE_TOO_LONG` | 422 | Message exceeds maximum length | Message >5,000 characters | Shorten message |
| `MSG_MESSAGE_EMPTY` | 422 | Message cannot be empty | Empty message text | Include message content |
| `MSG_BLOCKED_USER` | 403 | Cannot message blocked user | Recipient has blocked sender | Cannot send messages |

### Device Errors (DEV_*)

| Error Code | HTTP Status | Message | Cause | Solution |
|------------|-------------|---------|-------|----------|
| `DEV_NOT_FOUND` | 404 | Device not found | Device ID doesn't exist | Check device ID |
| `DEV_ACCESS_DENIED` | 403 | Cannot access this device | Device belongs to another user | Can only manage own devices |
| `DEV_ALREADY_REGISTERED` | 409 | Device already registered | Device ID already exists | Update existing device |
| `DEV_INVALID_PLATFORM` | 422 | Invalid device platform | Platform not 'ios' or 'android' | Use 'ios' or 'android' |
| `DEV_PUSH_TOKEN_INVALID` | 422 | Invalid push token format | Malformed FCM/APNS token | Check token format |

### Rate Limiting Errors (RATE_*)

| Error Code | HTTP Status | Message | Cause | Solution |
|------------|-------------|---------|-------|----------|
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests | Exceeded 100 requests/minute | Wait and retry after delay |
| `RATE_LIMIT_PER_RESOURCE` | 429 | Too many requests for this resource | Resource-specific rate limit | Wait before retrying |

### Validation Errors (VAL_*)

| Error Code | HTTP Status | Message | Cause | Solution |
|------------|-------------|---------|-------|----------|
| `VAL_REQUIRED_FIELD_MISSING` | 422 | Required field missing | Field marked as required not provided | Include required field |
| `VAL_INVALID_FORMAT` | 422 | Invalid field format | Field doesn't match expected format | Check field format |
| `VAL_OUT_OF_RANGE` | 422 | Value out of allowed range | Number too small or too large | Use value within range |
| `VAL_INVALID_ENUM` | 422 | Invalid enum value | Value not in allowed list | Use allowed value |
| `VAL_STRING_TOO_LONG` | 422 | String exceeds maximum length | Text too long | Shorten text |
| `VAL_STRING_TOO_SHORT` | 422 | String below minimum length | Text too short | Add more text |

### General Errors (ERR_*)

| Error Code | HTTP Status | Message | Cause | Solution |
|------------|-------------|---------|-------|----------|
| `ERR_INTERNAL_SERVER_ERROR` | 500 | Internal server error | Unexpected server-side issue | Retry or contact support |
| `ERR_NOT_IMPLEMENTED` | 501 | Feature not yet implemented | Endpoint under development | Feature coming soon |
| `ERR_SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable | Maintenance or overload | Retry after some time |
| `ERR_MALFORMED_JSON` | 400 | Invalid JSON in request body | JSON parsing failed | Check JSON syntax |
| `ERR_RESOURCE_NOT_FOUND` | 404 | Resource not found | Generic 404 error | Check resource ID |

---

## Validation Error Details

For validation errors (422 status), the response includes detailed field-level errors:

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    },
    {
      "loc": ["body", "password"],
      "msg": "ensure this value has at least 8 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

### Common Validation Types

| Type | Meaning | Example |
|------|---------|---------|
| `value_error.email` | Invalid email format | "notanemail" |
| `value_error.any_str.min_length` | String too short | Password <8 chars |
| `value_error.any_str.max_length` | String too long | Name >255 chars |
| `value_error.number.not_ge` | Number not greater than/equal | Negative experience years |
| `value_error.missing` | Required field missing | Email not provided |
| `value_error.const` | Value must be constant | Invalid enum value |

---

## Error Handling Best Practices

### 1. Always Check Status Codes

```swift
// iOS Example
if response.statusCode == 401 {
    // Token expired - refresh or re-login
    await refreshToken()
} else if response.statusCode >= 500 {
    // Server error - retry with exponential backoff
    await retryWithBackoff(request)
}
```

### 2. Handle Token Expiration

```kotlin
// Android Example
when (errorCode) {
    "AUTH_TOKEN_EXPIRED" -> {
        // Use refresh token to get new access token
        val newToken = refreshAccessToken()
        // Retry original request with new token
        retryRequest(newToken)
    }
}
```

### 3. Display User-Friendly Messages

```swift
// Map error codes to user-friendly messages
func getUserMessage(errorCode: String) -> String {
    switch errorCode {
    case "AUTH_INVALID_CREDENTIALS":
        return "Email or password is incorrect. Please try again."
    case "APP_ALREADY_EXISTS":
        return "You've already applied to this job."
    case "RATE_LIMIT_EXCEEDED":
        return "Too many requests. Please wait a moment and try again."
    default:
        return "Something went wrong. Please try again."
    }
}
```

### 4. Implement Retry Logic

```kotlin
// Retry for transient errors
suspend fun<T> retryableRequest(
    maxRetries: Int = 3,
    request: suspend () -> Result<T>
): Result<T> {
    var lastError: Throwable? = null

    repeat(maxRetries) { attempt ->
        try {
            return request()
        } catch (e: Exception) {
            lastError = e
            if (e is ServerErrorException && e.status == 503) {
                delay(2000L * (attempt + 1)) // Exponential backoff
            } else {
                throw e // Don't retry non-retryable errors
            }
        }
    }

    throw lastError!!
}
```

### 5. Log Errors for Debugging

Always log errors with context:
- Error code
- HTTP status
- Request ID (if available)
- User ID (for server-side logs)
- Timestamp

---

## Troubleshooting Guide

### "Token Expired" Errors

**Problem**: Getting `AUTH_TOKEN_EXPIRED` repeatedly
**Cause**: Access tokens expire after 15 minutes
**Solution**: Implement automatic token refresh using refresh token

### "Not Found" Errors on Valid Resources

**Problem**: Getting 404 for resource that should exist
**Cause**: May be accessing another user's resource
**Solution**: Check ownership and permissions

### Rate Limiting

**Problem**: Getting 429 errors
**Cause**: Exceeded 100 requests/minute
**Solution**:
- Implement request queuing
- Add delays between requests
- Cache responses locally

### Server Errors (500, 503)

**Problem**: Getting 5xx errors
**Cause**: Server-side issues
**Solution**:
- Retry with exponential backoff
- Contact support if persists
- Check system status page

---

## Support

If you encounter errors not documented here or need assistance:

- **Email**: support@networking-ai.com
- **Documentation**: https://docs.networking-ai.com
- **Status Page**: https://status.networking-ai.com
- **Developer Portal**: https://developers.networking-ai.com

---

## Changelog

### Version 1.0.0 (2025-11-08)
- Initial error code reference
- Documented all mobile API v1 error codes
- Added troubleshooting guide
- Included code examples for iOS and Android
