# Market Trends Tab Fix - Specification

## Overview

This specification addresses critical functionality issues in the Market Trends tab of the Financial Dashboard.

## Current Issues

1. **Outdated News**: News section displays stale headlines, not refreshing properly
2. **Broken Buttons**: 7 buttons are non-functional or partially working
3. **Missing Prices**: Price data not displaying correctly in results table
4. **Cache Issues**: Memory and disk cache out of sync, data not persisting

## Solution Summary

### Architecture Changes

- **Cache Manager**: Centralized cache operations with disk/memory sync
- **News Manager**: Proper TTL-based caching with auto-refresh
- **Button Handlers**: All 7 buttons fixed with comprehensive error handling
- **Table Renderer**: Price enrichment with proper fallbacks

### Testing Strategy

- **7 Property-Based Tests**: Using Hypothesis for universal properties
- **Unit Tests**: For each component (Cache, News, Table, Buttons)
- **Integration Tests**: End-to-end flows for critical user journeys
- **Performance Tests**: Verify 2-second load time and other requirements

## Files

- `requirements.md` - User stories and acceptance criteria
- `design.md` - Architecture, components, and correctness properties
- `tasks.md` - Implementation plan with 18 main tasks

## Quick Start

To begin implementation:

1. Review the requirements document
2. Study the design document architecture
3. Open `tasks.md` and start with Task 1 (Cache Manager)
4. Each task includes requirements references and test specifications

## Key Requirements

- News must refresh within 5 minutes
- All 7 buttons must work correctly
- Price data must display all 5 fields
- Tab must load within 2 seconds
- Cache must persist across page reloads
- Errors must be handled gracefully

## Implementation Phases

1. **Phase 1-2**: Core infrastructure (Cache, News)
2. **Phase 3-9**: Fix all buttons
3. **Phase 10-12**: Table rendering and tab activation
4. **Phase 13-14**: Error handling and integration
5. **Phase 15-18**: Testing and optimization

## Success Criteria

✅ All 7 buttons functional
✅ News refreshes automatically
✅ Prices display correctly
✅ Cache persists across reloads
✅ All tests passing
✅ Tab loads within 2 seconds
