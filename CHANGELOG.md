# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive documentation restructuring and organization
- Community health files (CODE_OF_CONDUCT.md, SECURITY.md)
- Issue and PR templates
- Automatic database initialization system
- Comprehensive testing suite for registration and agent interactions

### Fixed
- SQLAlchemy model relationship conflicts resolved
- PostgreSQL database initialization automation

## [0.2.0] - 2025-01-15

### Added
- AI Matching Service with background task processing
- Multi-factor scoring algorithm for job-candidate matching
- Background task manager with thread-based processing
- Automatic matching triggers on profile/job creation
- Match explanations powered by Claude AI
- Comprehensive matching pipeline tests

### Changed
- Platform backend completion increased to 95%
- Improved API response times with async processing

### Documentation
- MATCHING_SERVICE_INTEGRATION.md - Complete technical documentation
- API_COMPLETE.md - Updated with matching endpoints
- Performance benchmarks and optimization guides

## [0.1.0] - 2025-01-08

### Added
- Phase 2 multi-user architecture
- Dual seat pool management (Hiring Manager + Talent seats)
- Company Admin Agent system
- Hiring Manager interview flow and API
- Multi-function user accounts (Talent + HM + Recruiter)
- Agent portability with knowledge retention
- Subscription management system
- Dual RAG system (Personal + Company)
- Company knowledge base with ChromaDB
- Complete test suite with 1,500+ lines of test code

### Features
- User registration for multiple roles
- Hiring manager onboarding flow
- Company creation and management
- Seat allocation and licensing
- Data access enforcement ("No payment = No data")
- RESTful API with 37+ endpoints

### Documentation
- Comprehensive Phase 2 architecture documentation
- Testing guides and summaries
- API endpoint documentation
- Development session summaries

## [0.0.1] - 2024-12-15

### Added
- Initial project setup
- Basic database models
- Authentication system with JWT tokens
- Core API structure
- Docker and Docker Compose configuration
- PostgreSQL database integration
- Basic user management

### Infrastructure
- FastAPI application framework
- SQLAlchemy ORM with PostgreSQL
- Alembic for database migrations
- pytest testing framework
- Pre-commit hooks for code quality

---

## Version History Summary

- **0.2.0** - AI Matching Service Integration
- **0.1.0** - Multi-User Architecture & Company Management
- **0.0.1** - Initial Foundation

---

For detailed information about specific phases and features, see the documentation in `docs/phases/`.
