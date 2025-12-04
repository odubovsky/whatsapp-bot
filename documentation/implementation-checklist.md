# WhatsApp Bot - Implementation Checklist

## Overview

This checklist tracks the implementation progress for the WhatsApp bot project. Each item should be checked off as completed.

---

## Phase 1: Project Setup ⬜

### File Structure
- [ ] Create project root directory
- [ ] Create `.claude/` directory with documentation
- [ ] Create `store/` directory for database
- [ ] Create `logs/` directory for log files
- [ ] Create `systemd/` directory for service files

### Configuration Templates
- [ ] Create `.env.example` template
- [ ] Create `app.json.example` template
- [ ] Add `.gitignore` for `.env`, `store/`, `logs/`, `venv/`
- [ ] Create `README.md` with setup instructions

### Python Environment
- [ ] Create `requirements.txt` with all dependencies
- [ ] Create `setup.sh` script with CLI options
- [ ] Create `run.sh` script
- [ ] Test virtual environment creation

---

## Phase 2: Core Infrastructure ⬜

### Configuration Management (config.py)
- [ ] Implement `MonitoredEntity` dataclass
- [ ] Implement `WhatsAppConfig` dataclass
- [ ] Implement `PollingConfig` dataclass
- [ ] Implement `RotationConfig` dataclass
- [ ] Implement `SessionMemoryConfig` dataclass with validation
- [ ] Implement `VitalityConfig` dataclass
- [ ] Implement `PerplexityConfig` dataclass
- [ ] Implement `Config` class with singleton pattern
- [ ] Implement `.env` file loading with validation
- [ ] Implement `app.json` loading with validation
- [ ] Implement entity lookup maps
- [ ] Add error handling for missing/invalid config
- [ ] Test configuration loading with various scenarios

### Database Layer (database.py)
- [ ] Implement `Database` class with connection management
- [ ] Implement table creation (messages, chat_sessions, whatsapp_device)
- [ ] Create indexes for performance
- [ ] Enable WAL mode for concurrency
- [ ] Implement message insertion
- [ ] Implement message querying (unprocessed, by chat, by date)
- [ ] Implement message rotation cleanup
- [ ] Implement session creation with expiry calculation
- [ ] Implement session context loading and updating
- [ ] Implement session expiry cleanup
- [ ] Implement WhatsApp session storage/loading
- [ ] Implement database statistics
- [ ] Add proper error handling and transactions
- [ ] Test all database operations

---

## Phase 3: WhatsApp Integration ⬜

### WhatsApp Client (whatsapp_client.py)
- [ ] Research and select Python WhatsApp library
- [ ] Implement `WhatsAppClient` class
- [ ] Implement QR code authentication flow
- [ ] Implement QR code display in terminal
- [ ] Implement session persistence to database
- [ ] Implement auto-reconnection logic
- [ ] Implement message event handler (on_message)
- [ ] Implement message filtering (monitored entities only)
- [ ] Implement message storage to database
- [ ] Implement message sending
- [ ] Implement connection status tracking
- [ ] Add error handling for disconnections
- [ ] Test QR authentication
- [ ] Test message receiving
- [ ] Test message sending
- [ ] Test reconnection logic

### Startup Validation
- [ ] Implement startup message sending to self
- [ ] Include timestamp and service info in message
- [ ] Handle errors if self-message fails
- [ ] Log validation status

---

## Phase 4: AI Integration ⬜

### Perplexity Client
- [ ] Implement `PerplexityClient` class
- [ ] Implement chat completion API call
- [ ] Implement error handling (rate limits, timeouts)
- [ ] Implement retry logic with exponential backoff
- [ ] Test API integration with sample queries

### Message Agent (message_agent.py)
- [ ] Implement `MessageAgent` class
- [ ] Implement polling loop with configurable interval
- [ ] Implement unprocessed message detection
- [ ] Implement session memory loading
- [ ] Implement prompt building with entity-specific prompt
- [ ] Implement context injection (session memory)
- [ ] Implement LLM query with Perplexity
- [ ] Implement response sending via WhatsApp
- [ ] Implement session memory updating
- [ ] Implement message marking as processed
- [ ] Add error handling for LLM failures
- [ ] Test end-to-end message processing
- [ ] Test session memory persistence

---

## Phase 5: Background Services ⬜

### Vitality Checker (vitality_checker.py)
- [ ] Implement `VitalityChecker` class
- [ ] Implement APScheduler integration
- [ ] Implement cron-based scheduling
- [ ] Implement timezone-aware scheduling
- [ ] Implement vitality message sending
- [ ] Add enable/disable logic
- [ ] Test daily scheduling
- [ ] Test timezone handling

### Rotation Cleanup Task
- [ ] Implement periodic cleanup scheduler
- [ ] Use configurable interval from config
- [ ] Call database cleanup methods
- [ ] Log cleanup statistics
- [ ] Test rotation with various retention periods

### Session Expiry Task
- [ ] Implement periodic session cleanup
- [ ] Run every hour (or configurable)
- [ ] Call database session cleanup
- [ ] Log expired session count
- [ ] Test session expiry modes (time, duration, same_day)

---

## Phase 6: Main Orchestration ⬜

### Main Entry Point (main.py)
- [ ] Implement argument parser with all CLI options
- [ ] Implement configuration loading
- [ ] Implement database initialization
- [ ] Implement logging setup
- [ ] Implement WhatsApp client initialization
- [ ] Implement startup validation message
- [ ] Implement async task orchestration
- [ ] Create concurrent tasks (listener, agent, cleanup, vitality)
- [ ] Implement graceful shutdown handler (SIGINT, SIGTERM)
- [ ] Implement special modes (--qr-only, --reset-session, etc.)
- [ ] Add comprehensive error handling
- [ ] Test main service loop
- [ ] Test graceful shutdown

---

## Phase 7: Utility Scripts ⬜

### Database Manager (db_manager.py)
- [ ] Implement argument parser with subcommands
- [ ] Implement `stats` command
- [ ] Implement `cleanup` command with --dry-run
- [ ] Implement `export` command (JSON and CSV formats)
- [ ] Implement `sessions` command (list and clear)
- [ ] Implement `vacuum` command
- [ ] Add help text for all commands
- [ ] Test all database operations

### Configuration Validator (test_config.py)
- [ ] Implement argument parser
- [ ] Implement basic validation
- [ ] Implement --show-entities option
- [ ] Implement --test-perplexity option
- [ ] Implement --check-timezones option
- [ ] Implement --verbose output
- [ ] Add detailed error messages
- [ ] Test with valid and invalid configs

### Message Sender (send_message.py)
- [ ] Implement argument parser
- [ ] Implement recipient resolution (phone/JID/name)
- [ ] Implement text message sending
- [ ] Implement file sending
- [ ] Implement --self option
- [ ] Add error handling
- [ ] Test message sending

---

## Phase 8: Deployment ⬜

### Systemd Service
- [ ] Create `whatsapp-bot.service` file
- [ ] Configure service user and paths
- [ ] Configure restart policy
- [ ] Configure logging
- [ ] Test service installation
- [ ] Test service start/stop/restart
- [ ] Test auto-start on reboot

### Documentation
- [ ] Write comprehensive README.md
- [ ] Document installation steps
- [ ] Document configuration
- [ ] Document common workflows
- [ ] Document troubleshooting
- [ ] Add examples and screenshots
- [ ] Document cloud deployment steps

### Setup Scripts
- [ ] Enhance setup.sh with all options
- [ ] Add system dependency installation
- [ ] Add validation checks
- [ ] Add error handling
- [ ] Test on fresh system

---

## Phase 9: Testing & Validation ⬜

### Unit Tests (Optional but Recommended)
- [ ] Write tests for config.py
- [ ] Write tests for database.py
- [ ] Write tests for session expiry calculation
- [ ] Write tests for message filtering
- [ ] Write tests for utilities

### Integration Tests
- [ ] Test full message flow (receive → process → respond)
- [ ] Test session memory across multiple messages
- [ ] Test rotation cleanup
- [ ] Test session expiry
- [ ] Test vitality checker
- [ ] Test reconnection logic
- [ ] Test with multiple monitored entities

### Manual Testing
- [ ] Test QR code authentication
- [ ] Test message receiving from group
- [ ] Test message receiving from individual
- [ ] Test AI response generation
- [ ] Test session memory context
- [ ] Test session expiry at configured time
- [ ] Test startup validation message
- [ ] Test daily vitality check
- [ ] Test message rotation
- [ ] Test all CLI options
- [ ] Test all utility scripts

---

## Phase 10: Production Deployment ⬜

### Pre-Deployment
- [ ] Review all code for security issues
- [ ] Review configuration templates
- [ ] Test on staging environment
- [ ] Prepare backup strategy
- [ ] Document rollback procedure

### Cloud Deployment
- [ ] Provision VPS (AWS/GCP/DigitalOcean)
- [ ] Configure firewall/security groups
- [ ] Install Python and dependencies
- [ ] Clone repository
- [ ] Run setup.sh
- [ ] Configure .env and app.json
- [ ] Authenticate WhatsApp (QR code)
- [ ] Install systemd service
- [ ] Start service
- [ ] Verify startup validation message
- [ ] Monitor logs for errors
- [ ] Test message flow end-to-end

### Monitoring
- [ ] Set up log rotation
- [ ] Set up database backups
- [ ] Monitor disk usage
- [ ] Monitor service status
- [ ] Test vitality checks
- [ ] Document monitoring procedures

---

## Known Issues / Future Enhancements

### To Be Resolved
- [ ] WhatsApp library selection (research best Python option)
- [ ] Media message support (images, videos, documents)
- [ ] Message processing tracking (avoid duplicate processing)
- [ ] Rate limiting for Perplexity API
- [ ] Conversation context size limits

### Future Features
- [ ] Web dashboard for monitoring
- [ ] Multi-language support
- [ ] Custom plugin system
- [ ] Analytics and reporting
- [ ] Automatic config reload (no restart)
- [ ] Multiple LLM providers (not just Perplexity)
- [ ] Group admin commands
- [ ] Scheduled messages
- [ ] Message templates

---

## Progress Summary

**Total Tasks:** ~150+
**Completed:** 0
**In Progress:** 0
**Remaining:** 150+

**Current Phase:** Pre-Implementation (Documentation Complete)

---

## Notes

- Each checkbox represents a discrete, testable unit of work
- Items should be completed in order within each phase
- Phases can be worked on somewhat in parallel
- Test after completing each major component
- Document any deviations from plan
- Update this checklist as implementation progresses

---

## Sign-Off

### Phase Completion

- [ ] Phase 1: Project Setup - Completed by: _____ Date: _____
- [ ] Phase 2: Core Infrastructure - Completed by: _____ Date: _____
- [ ] Phase 3: WhatsApp Integration - Completed by: _____ Date: _____
- [ ] Phase 4: AI Integration - Completed by: _____ Date: _____
- [ ] Phase 5: Background Services - Completed by: _____ Date: _____
- [ ] Phase 6: Main Orchestration - Completed by: _____ Date: _____
- [ ] Phase 7: Utility Scripts - Completed by: _____ Date: _____
- [ ] Phase 8: Deployment - Completed by: _____ Date: _____
- [ ] Phase 9: Testing & Validation - Completed by: _____ Date: _____
- [ ] Phase 10: Production Deployment - Completed by: _____ Date: _____

### Final Review

- [ ] All features implemented
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Production deployment successful
- [ ] Monitoring in place
- [ ] Backup strategy verified

**Project Status:** 🔴 Not Started

**Last Updated:** 2024-01-15
