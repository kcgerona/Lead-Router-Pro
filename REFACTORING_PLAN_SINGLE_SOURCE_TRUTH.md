# Single Source of Truth Refactoring Plan

## Executive Summary
Refactor the Lead Router Pro codebase to eliminate duplicate data sources and establish `dockside_pros_service_dictionary.py` as the single source of truth for all service categories and hierarchies.

## Current Architecture Issues
1. **Three Separate Data Sources**:
   - `dockside_pros_service_dictionary.py` (main dictionary)
   - `service_categories.py` (duplicate for vendor-matching)
   - Hardcoded data in `vendor_application_final.html`

2. **Multiple Vendor Application Versions**:
   - `vendor_application_final.html` (hardcoded, currently used)
   - `vendor_application_api.html` (uses API, not linked)
   - `vendor_application_api_v2.html` (improved, not used)
   - `vendor_application_working.html` (another version, not used)

## Refactoring Sprints

### SPRINT 1: Create Unified API Layer (Low Risk)
**Goal**: Ensure all APIs use the single source dictionary

#### Tasks:
1. **Audit Current API Endpoints**
   - [ ] Document which endpoints use which data source
   - [ ] Identify all consumers of each endpoint
   - [ ] Map data flow from source to consumer

2. **Create Adapter Layer**
   - [ ] Create `api/services/unified_service_dictionary.py`
   - [ ] Import from `dockside_pros_service_dictionary.py` only
   - [ ] Create adapter functions for different format needs
   - [ ] Add caching layer for performance

3. **Create Comprehensive Test Suite**
   - [ ] Test all service category retrievals
   - [ ] Test Level 2 and Level 3 service mappings
   - [ ] Test special cases (single subcategory with L3)
   - [ ] Create test file: `test_unified_services.py`

**Deliverable**: Unified service module that all endpoints can use
**Risk**: Low - Adding new code without changing existing
**Testing**: Run in parallel with existing system

---

### SPRINT 2: Refactor Vendor Application Widget (Medium Risk)
**Goal**: Create API-driven vendor application widget as test version

#### Tasks:
1. **Create New API-Driven Widget**
   - [ ] Copy `vendor_application_final.html` to `vendor_application_unified.html`
   - [ ] Remove all hardcoded SERVICE_CATEGORIES data
   - [ ] Implement async fetch from `/api/v1/services/dictionary`
   - [ ] Preserve ALL existing form behavior and logic

2. **Implement Smart Caching**
   ```javascript
   // Cache service data in localStorage with TTL
   const CACHE_KEY = 'service_categories_cache';
   const CACHE_TTL = 3600000; // 1 hour
   
   async function getServiceCategories() {
       const cached = getCachedData(CACHE_KEY);
       if (cached && !isExpired(cached)) {
           return cached.data;
       }
       const fresh = await fetchFromAPI();
       setCachedData(CACHE_KEY, fresh);
       return fresh;
   }
   ```

3. **Preserve Complex Behaviors**
   - [ ] Multi-step category selection
   - [ ] Level 3 service handling
   - [ ] Auto-selection logic
   - [ ] Skip logic for certain categories
   - [ ] Additional categories handling

4. **Create Side-by-Side Testing Page**
   - [ ] Create test page with both widgets
   - [ ] Add comparison logging
   - [ ] Verify identical behavior

**Deliverable**: `vendor_application_unified.html` that fetches from API
**Risk**: Medium - Complex form logic must be preserved
**Testing**: A/B test against current version

---

### SPRINT 3: Update Vendor-Matching to Use Main Dictionary (Low Risk)
**Goal**: Eliminate `service_categories.py` dependency

#### Tasks:
1. **Update Vendor-Matching Routes**
   - [ ] Modify `vendor_matching_enhanced.py`
   - [ ] Import from unified service module
   - [ ] Transform data format as needed
   - [ ] Remove import of `service_categories.py`

2. **Create Format Transformer**
   ```python
   def transform_for_vendor_matching(main_dict):
       """Transform main dictionary format to vendor-matching format"""
       result = {}
       for cat_id, cat_data in main_dict.items():
           category_name = cat_data["name"]
           # Extract Level 2 services
           level2_services = []
           for subcat_name in cat_data["subcategories"].keys():
               level2_services.append(subcat_name)
           result[category_name] = level2_services
       return result
   ```

3. **Update Dashboard Integration**
   - [ ] Test dashboard vendor matching tool
   - [ ] Verify all dropdowns populate correctly
   - [ ] Test Level 3 service selection

**Deliverable**: Vendor-matching using main dictionary
**Risk**: Low - Backend change only
**Testing**: API response comparison

---

### SPRINT 4: Integration Testing & Cleanup (Low Risk)
**Goal**: Validate everything works, remove old code

#### Tasks:
1. **Comprehensive Integration Testing**
   - [ ] Test all form submissions
   - [ ] Test vendor application flow
   - [ ] Test vendor matching flow
   - [ ] Test dashboard functionality
   - [ ] Load testing for API performance

2. **Deploy New Version**
   - [ ] Replace `vendor_application_final.html` link
   - [ ] Point to `vendor_application_unified.html`
   - [ ] Monitor for issues

3. **Clean Up Old Code**
   - [ ] Archive unused vendor application versions
   - [ ] Remove `service_categories.py`
   - [ ] Remove duplicate API endpoints
   - [ ] Update documentation

**Deliverable**: Clean, single-source architecture
**Risk**: Low - Only removing unused code
**Testing**: Full regression suite

---

## Implementation Strategy

### Phase 1: Preparation (Sprint 1)
- No breaking changes
- Add new unified layer
- Comprehensive testing

### Phase 2: Parallel Testing (Sprint 2)
- New widget runs alongside old
- A/B testing capability
- Rollback ability

### Phase 3: Migration (Sprint 3)
- Backend services updated
- Old APIs deprecated (but not removed)
- Monitoring in place

### Phase 4: Cleanup (Sprint 4)
- Remove technical debt
- Documentation updates
- Final validation

## Success Criteria
1. **Single Source**: Only `dockside_pros_service_dictionary.py` contains service data
2. **No Duplication**: No hardcoded service lists anywhere
3. **API Driven**: All UIs fetch data from APIs
4. **No Breaking Changes**: All existing functionality preserved
5. **Performance**: No degradation in load times

## Risk Mitigation
1. **Parallel Running**: New code runs alongside old
2. **Feature Flags**: Toggle between old/new implementations
3. **Comprehensive Testing**: Each sprint has test requirements
4. **Incremental Changes**: Small, reversible steps
5. **Monitoring**: Track errors and performance

## Timeline Estimate
- Sprint 1: 2-3 hours
- Sprint 2: 3-4 hours (most complex)
- Sprint 3: 2 hours
- Sprint 4: 1-2 hours

Total: 8-11 hours of focused work

## Next Steps
1. Review and approve this plan
2. Start with Sprint 1 (lowest risk)
3. Validate each sprint before proceeding
4. Maintain ability to rollback at any stage

## Notes
- Each sprint is designed to be completed in one session
- No sprint depends on incomplete work from previous sprint
- All changes are backwards compatible
- Production can continue running during refactoring