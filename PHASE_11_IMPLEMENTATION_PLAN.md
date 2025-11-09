# Phase 11: Real-time Features - Implementation Plan

## Current Status

### ✅ Already Implemented (Phase 3)

**WebSocket Infrastructure**:
- ✅ `websocket/connection_manager.py` - Connection pool, presence tracking
- ✅ `websocket/event_types.py` - Event schemas (Connected, Heartbeat, Typing, MessageRead, Presence, Error)
- ✅ `api/websocket.py` - WebSocket endpoint `/ws` with authentication
- ✅ Connection lifecycle: connect, disconnect, heartbeat
- ✅ Presence system: online/away/offline
- ✅ Typing indicators
- ✅ Message read receipts
- ✅ Broadcasting capabilities
- ✅ Connection statistics endpoint

**What Works**:
- JWT authentication on connection
- User/agent connection tracking
- Real-time presence updates
- Heartbeat monitoring with stale connection cleanup
- Personal and broadcast messaging

---

## Phase 11 Enhancements

### New Features to Add

#### 1. Real-time Memory Sync (NEW) ⭐
**Integration with Phase 10A Enhanced Memory System**

**Files to Create**:
- `websocket/memory_events.py` - Memory event types
- `services/realtime_memory_service.py` - Memory broadcast service

**Events**:
```python
class MemoryCreatedEvent:
    memory_id: int
    user_id: int
    content_preview: str  # First 100 chars
    importance: float
    tier: str

class MemoryUpdatedEvent:
    memory_id: int
    user_id: int
    changes: dict

class MemoryDeletedEvent:
    memory_id: int
    user_id: int

class MemoryTierChangedEvent:
    memory_id: int
    old_tier: str
    new_tier: str
    decay_score: float
```

**Use Cases**:
- Notify user when memory is promoted to hot tier
- Real-time memory sync across devices
- Alert when important memory is about to be demoted
- Show decay score changes in real-time

**Estimated**: 6 hours

---

#### 2. Real-time Notification Push (ENHANCE) ⭐⭐
**Enhance existing notification system with WebSocket delivery**

**Files to Modify**:
- `websocket/event_types.py` - Add NotificationEvent
- `services/notification_service.py` - Add WebSocket push

**Events**:
```python
class NotificationEvent:
    notification_id: int
    user_id: int
    type: str  # message, application, interview, etc.
    title: str
    body: str
    action_url: Optional[str]
    priority: str  # high, medium, low
    created_at: str
```

**Features**:
- Push notifications through WebSocket
- Fallback to polling for disconnected clients
- Notification grouping (combine similar notifications)
- Batch send for efficiency

**Estimated**: 6 hours

---

#### 3. Live Job Feed (NEW) ⭐⭐
**Real-time job posting updates**

**Files to Create**:
- `websocket/job_events.py` - Job event types
- `services/realtime_job_service.py` - Job broadcast service

**Events**:
```python
class NewJobEvent:
    job_id: int
    title: str
    company_name: str
    location: str
    salary_range: Optional[dict]
    match_score: Optional[float]  # If user has matching skills

class JobStatusChangedEvent:
    job_id: int
    old_status: str
    new_status: str  # open, closed, filled

class SavedJobUpdatedEvent:
    job_id: int
    user_id: int
    changes: dict  # salary_updated, description_updated, etc.
```

**Use Cases**:
- Show new jobs matching user's profile in real-time
- Alert when saved job is updated
- Notify when job is about to close

**Estimated**: 6 hours

---

#### 4. Application Status Updates (NEW) ⭐⭐
**Real-time application progress notifications**

**Files to Create**:
- `websocket/application_events.py` - Application event types

**Events**:
```python
class ApplicationStatusChangedEvent:
    application_id: int
    job_id: int
    old_status: str
    new_status: str  # submitted, reviewing, interview, rejected, accepted
    changed_by: str  # system, recruiter, ai_agent
    message: Optional[str]

class InterviewScheduledEvent:
    interview_id: int
    application_id: int
    scheduled_at: str
    interview_type: str  # phone, video, in-person
    location: Optional[str]

class OfferReceivedEvent:
    offer_id: int
    application_id: int
    salary: Optional[float]
    benefits: List[str]
    expires_at: str
```

**Use Cases**:
- Instant notification when application status changes
- Alert for interview scheduling
- Immediate offer notifications

**Estimated**: 6 hours

---

#### 5. Activity Feed (NEW) ⭐
**Real-time user activity stream**

**Files to Create**:
- `websocket/activity_events.py` - Activity event types

**Events**:
```python
class UserActivityEvent:
    user_id: int
    activity_type: str  # profile_viewed, application_submitted, message_sent
    timestamp: str
    metadata: dict

class ProfileViewedEvent:
    viewer_id: int
    viewed_user_id: int
    viewer_type: str  # recruiter, company, talent

class SkillEndorsedEvent:
    endorser_id: int
    endorsed_user_id: int
    skill: str
```

**Use Cases**:
- Show who viewed your profile in real-time
- Live feed of endorsements and recommendations
- Activity timeline updates

**Estimated**: 4 hours

---

#### 6. Enhanced Mobile Integration (NEW) ⭐
**Mobile-specific WebSocket optimizations**

**Files to Create**:
- `docs/MOBILE_WEBSOCKET_GUIDE.md` - Comprehensive guide
- `examples/ios_websocket.swift` - iOS example
- `examples/android_websocket.kt` - Android example

**Features**:
- Connection recovery strategies
- Background connection handling
- Battery optimization tips
- Reconnection exponential backoff
- Message queueing during disconnection

**Content**:
```markdown
# Mobile WebSocket Integration Guide

## iOS (Swift)
- URLSessionWebSocketTask usage
- Background modes configuration
- Connection state management
- Exponential backoff implementation

## Android (Kotlin)
- OkHttp WebSocket client
- WorkManager for reconnection
- Foreground service for persistent connection
- Network change handling

## React Native
- Socket.io-client integration
- AsyncStorage for offline queue
- NetInfo for connectivity detection
```

**Estimated**: 6 hours

---

#### 7. Load Testing & Performance (NEW) ⭐⭐
**Ensure system can handle 1000+ concurrent connections**

**Files to Create**:
- `tests/load_tests/test_websocket_load.py` - Load testing script
- `tests/test_websocket_integration.py` - Integration tests

**Tests**:
```python
# Load Tests
- test_1000_concurrent_connections()
- test_message_broadcast_performance()
- test_connection_recovery()
- test_memory_usage_under_load()

# Integration Tests
- test_memory_event_delivery()
- test_notification_push()
- test_job_feed_updates()
- test_application_status_sync()
- test_presence_tracking()
```

**Tools**:
- Locust for load testing
- pytest-asyncio for async tests
- WebSocket test client

**Targets**:
- ✅ Support 1000+ concurrent connections
- ✅ <100ms message delivery latency
- ✅ <1MB memory per connection
- ✅ 99.9% uptime

**Estimated**: 8 hours

---

## Implementation Priority

### Week 1: Core Enhancements

**Day 1-2** (Tasks 11.1-11.3): ✅ Already Done (Phase 3)
- WebSocket dependencies ✅
- Connection manager ✅
- Authentication ✅

**Day 3-4** (Tasks 11.4-11.5): Notifications
- [x] Task 11.1: Enhance notification push system
- [x] Task 11.2: Add NotificationEvent types
- [x] Task 11.3: Integrate with existing notification service

**Day 5** (Tasks 11.6-11.7): ✅ Partially Done (Phase 3)
- Messaging ✅
- Typing indicators ✅
- Read receipts ✅

### Week 2: New Features & Testing

**Day 6-7** (Tasks 11.8-11.9): Applications & Jobs
- [ ] Task 11.4: Application status events
- [ ] Task 11.5: Live job feed
- [ ] Task 11.6: Memory sync events

**Day 8-9** (Tasks 11.10-11.11): Presence & Activity
- [x] Task 11.7: Presence system ✅ (already done)
- [ ] Task 11.8: Activity feed events

**Day 10** (Tasks 11.12-11.13): Testing & Docs
- [ ] Task 11.9: WebSocket load tests
- [ ] Task 11.10: Integration tests
- [ ] Task 11.11: Mobile integration guide

---

## Files to Create/Modify

### New Files (10)
1. `websocket/memory_events.py` - Memory sync events
2. `websocket/job_events.py` - Job feed events
3. `websocket/application_events.py` - Application status events
4. `websocket/activity_events.py` - Activity feed events
5. `services/realtime_memory_service.py` - Memory broadcast service
6. `services/realtime_job_service.py` - Job broadcast service
7. `tests/test_websocket_integration.py` - Integration tests
8. `tests/load_tests/test_websocket_load.py` - Load tests
9. `docs/MOBILE_WEBSOCKET_GUIDE.md` - Mobile guide
10. `examples/websocket_clients/` - iOS/Android examples

### Files to Enhance (3)
1. `websocket/event_types.py` - Add new event types
2. `services/notification_service.py` - Add WebSocket push
3. `api/websocket.py` - Add new event handlers

---

## Success Criteria

### Functional Requirements
- ✅ Real-time memory sync across devices
- ✅ Instant notification delivery via WebSocket
- ✅ Live job feed updates
- ✅ Application status change alerts
- ✅ User activity stream
- ✅ Presence tracking (already done)
- ✅ Mobile reconnection handling

### Performance Requirements
- ✅ Support 1000+ concurrent connections
- ✅ <100ms event delivery latency
- ✅ <1MB memory per connection
- ✅ 99.9% message delivery success rate
- ✅ Graceful degradation under load

### Testing Requirements
- ✅ 100% test coverage for new events
- ✅ Load tested with 1000+ connections
- ✅ Integration tests for all event types
- ✅ Mobile client examples working

---

## Timeline

**Week 1**: Core enhancements (Notifications, Memory Sync)
- Days 1-2: ✅ Already complete
- Days 3-4: Notification push (6 hours)
- Day 5: Memory sync events (6 hours)

**Week 2**: New features & Testing
- Days 6-7: Jobs & Applications (12 hours)
- Days 8-9: Activity & Polish (8 hours)
- Day 10: Testing & Docs (14 hours)

**Total**: ~46 hours of new work (existing infrastructure saves ~14 hours)

---

## Next Steps

1. **Start with Memory Sync** (highest value)
   - Create `websocket/memory_events.py`
   - Integrate with Phase 10A memory system
   - Test real-time sync

2. **Enhance Notifications**
   - Add WebSocket push to existing notification service
   - Test with mobile clients

3. **Add Job & Application Events**
   - Real-time job feed
   - Application status updates

4. **Testing & Documentation**
   - Load tests
   - Mobile integration guide
   - API documentation

---

**Status**: Ready to implement
**Dependencies**: Phase 10A complete ✅, Phase 3 WebSocket ✅
**Risk**: Low (building on existing, tested infrastructure)
