# Enhanced Database Sync V3 — Documentation

This document describes how **Enhanced Database Sync V3** (`api/services/enhanced_db_sync_v3.py`) synchronizes local vendors and leads with GoHighLevel (GHL) contacts.

---

## Overview

Sync V3 performs a **single unified fetch** of GHL contacts for both vendors and leads, then classifies each contact and runs vendor/lead-specific sync logic. Compared to V2, it reduces API calls by:

- Fetching each contact at most once (deduplicated by contact ID)
- Using one paginated list pass for both vendors and leads when needed
- Using a small concurrent worker pool for fetch-by-ID with rate limiting

---

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│  sync_all()                                                             │
├─────────────────────────────────────────────────────────────────────────┤
│  1. Collect identifiers (vendors + leads) from local DB                  │
│  2. Unified GHL contact fetch (by ID → by email → optional list)        │
│  3. Classify contacts into vendor_contacts vs lead_contacts               │
│  4. Process vendor sync (update/create, mark missing)                    │
│  5. Process lead sync (update/create, mark missing)                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Step 1: Collect Identifiers

**Method:** `_collect_all_identifiers()`

- Reads from local DB in minimal queries.
- **Vendors:** all `ghl_contact_id` and `email` from `vendors`.
- **Leads:** all `ghl_contact_id`, `customer_email`, `ghl_opportunity_id`, and `id` from `leads`.
- Builds:
  - `vendor_contact_ids`, `vendor_emails`
  - `lead_contact_ids`, `lead_emails`, `lead_opportunity_ids`, `lead_id_by_contact_id`
  - `all_contact_ids` = union of vendor and lead contact IDs (for deduplication).

If no identifiers are found, sync exits successfully without calling GHL.

---

## Step 2: Unified GHL Contact Fetch

**Method:** `_unified_fetch_contacts(identifiers)`

Builds a single `contact_map[contact_id] = contact` in three phases.

### Phase 2a — Fetch by ID

- For each ID in `all_contact_ids`, calls `get_contact_by_id` (with rate limiting).
- Uses a thread pool (`FETCH_BY_ID_WORKERS = 3`) and a lock to enforce `GHL_RATE_LIMIT_DELAY` (0.12s) between requests.
- If a **lead** contact ID fails to fetch, that ID is added to `_lead_contact_ids_fetch_failed` so the lead is not later marked as “missing” (avoids false positives when the API fails).

### Phase 2b — Search by Email

- Computes emails that are in `vendor_emails` or `lead_emails` but not present in any contact in `contact_map`.
- For each missing email, calls `search_contacts_by_email` and adds the first result to `contact_map` if found.

### Phase 2c — Paginated List Fallback

- **When it runs:** Only if there are still **missing emails** or **lead opportunity IDs** to match after Phase 2a and 2b. If every contact was found by ID or email search, this phase is **skipped** and there are **zero** POST /contacts/search calls.
- **How it works:** Calls `search_contacts_paginated` (POST /contacts/search) with `limit=500` per page. Each response returns up to 500 contacts and a `search_after` cursor for the next page. The loop continues until there are no more pages, or `missing_emails` and matches for `lead_opp_ids` are satisfied, or `LIST_SCAN_CAP` (15,000) contacts have been scanned.
- **Number of contact/search calls:** One call per page. So if GHL has **800 contacts** and the fallback runs (e.g. some emails still missing), you get **2 calls**: first page returns 500, second page returns the remaining 300. In general: `ceil(total_ghl_contacts / 500)` calls, up to the point where the sync stops (no more pages or nothing left to match).
- **Implementation:** The sync calls `ghl_api.search_contacts_paginated()` in a loop; the client lives in `api/services/ghl_api_v2_optimized.py` and uses POST `/contacts/search` with `limit` and `searchAfter` (cursor from the previous response) for proper pagination.

**Result:** One `contact_map` used for both vendor and lead classification.

---

## Step 3: Classify Contacts

Contacts in `contact_map` are split into **vendor** vs **lead**. Staff contacts are excluded from both.

### Vendor Classification

**Method:** `_classify_vendor_contacts(contact_map, identifiers)`

A contact is treated as a **vendor** if:

- Its ID is in `vendor_contact_ids`, or  
- Its email is in `vendor_emails`, or  
- **GHL signals** say vendor:
  - Source contains `"Vendor Application"`, or  
  - Tags contain any of: `"new vendor"`, `"new vendor application"`, `"manually approved"`.

### Lead Classification

**Method:** `_classify_lead_contacts(contact_map, identifiers)`

A contact is treated as a **lead** only if:

- Its ID is in `lead_contact_ids` or its email is in `lead_emails`, **and**
- It is **not** classified as a vendor by GHL signals (vendor takes precedence).

---

## Step 4: Vendor Sync

**Method:** `_process_vendor_sync(ghl_vendors, local_vendors_tuple)`

- **Local data:** `local_by_ghl_id` and `local_by_email` from `_get_local_vendors()`.
- For each GHL vendor contact:
  - Match to local vendor by `ghl_contact_id` or email.
  - If **matched:** `_update_local_vendor` (extract updates from GHL, apply status from tags, update DB). Optionally backfill `ghl_contact_id` if it was missing.
  - If **not matched:** `_create_local_vendor` (create new vendor in DB from GHL contact).
- **Missing in GHL:** Any local vendor that was not in `ghl_vendors` (i.e. not in GHL contact set) is passed to `_handle_missing_ghl_vendor`: status is set to **`inactive_ghl_deleted`**.

### Vendor Status from Tags

**Method:** `_get_vendor_status_from_tags(ghl_contact)`

Status is derived from **tag levels**. The **highest-level tag present** on the contact wins:

| Level | Tag                    | Status                 |
|-------|------------------------|------------------------|
| 0     | new vendor application | new application        |
| 1     | onboarding in process  | onboarding in process  |
| 2     | manual approval        | pending                |
| 3     | manually approved      | active                 |
| 4     | deactivated            | deactivated            |
| 5     | reactivated            | active                 |

If no tag matches, status is **pending**.

### Vendor Fields Synced

- From GHL: name, email, phone, company_name, service_categories, services_offered, service_zip_codes, taking_new_work, last_lead_assigned, lead_close_percentage, primary_service_category, ghl_user_id.
- Coverage (coverage_type, coverage_states, coverage_counties) is parsed from the service_zip_codes custom field (global, national, state, county).

---

## Step 5: Lead Sync

**Method:** `_process_lead_sync(ghl_leads, local_leads)`

- **Local data:** Combined map by `ghl_contact_id` and email from `_get_local_leads()`.
- For each GHL lead contact:
  - Match to local lead by `ghl_contact_id` or email.
  - If **matched:** `_update_local_lead` (extract updates, apply status from tags).
  - If **not matched:** `_create_local_lead` (create new lead in DB from GHL contact).
- **Missing in GHL:** Local leads that were not in `ghl_leads` are normally passed to `_handle_missing_lead` and status set to **`inactive_ghl_deleted`**. **Exception:** if the lead’s `ghl_contact_id` is in `_lead_contact_ids_fetch_failed` (fetch by ID failed), the lead is **not** marked missing (avoids marking as deleted when the failure was due to API/network).

### Lead Status from Tags

**Method:** `_get_lead_status_from_tags(ghl_contact)`

- If the contact has the tag **`"new lead"`** → status **`"new lead"`**.
- Otherwise → no change from tags (returns `None`; existing status is kept on update; on create, default is `"unassigned"`).

### Lead Fields Synced

- From GHL: customer_name, customer_email, customer_phone, primary_service_category, specific_service_requested.
- Zip from `postalCode` or extracted from `address1`; then `location_service.zip_to_location` is used to fill `service_county` and `service_state` when possible.

---

## Status Summary

| Scenario                         | Entity  | Status set                |
|----------------------------------|---------|---------------------------|
| In GHL, tags applied             | Vendor  | By highest tag level (see table above) |
| In GHL, tag "new lead"           | Lead    | `new lead`                |
| Not found in GHL contacts        | Vendor  | `inactive_ghl_deleted`    |
| Not found in GHL contacts        | Lead    | `inactive_ghl_deleted`    |
| Lead fetch-by-ID failed for ID   | Lead    | Not marked missing (skipped) |

The constant **`missing_in_ghl`** is defined in code for reference; the status actually written when a record is not found in GHL is **`inactive_ghl_deleted`** for both leads and vendors.

---

## Configuration Constants

| Constant                 | Default / value        | Purpose                                      |
|--------------------------|------------------------|----------------------------------------------|
| `GHL_RATE_LIMIT_DELAY`   | 0.12 (seconds)         | Min delay between GHL API calls               |
| `FETCH_BY_ID_WORKERS`    | 3                      | Concurrent workers for fetch-by-ID            |
| `SEARCH_PAGE_LIMIT`      | 500                    | Page size for POST /contacts/search           |
| `LIST_SCAN_CAP`          | 15000                  | Max contacts scanned in list fallback         |
| `VENDOR_SOURCE_KEYWORD`  | "Vendor Application"   | Source string that implies vendor             |
| `VENDOR_TAGS`            | new vendor, …          | Tags that imply vendor                       |
| `VENDOR_TAG_LEVELS`      | (level, tag, status)   | Vendor status by tag; higher level wins       |
| `DEFAULT_VENDOR_STATUS`  | pending                | Vendor status when no tag matches             |
| `INACTIVE_GHL_DELETED_STATUS` | inactive_ghl_deleted | Status when not found in GHL (lead & vendor) |

---

## Return Value and Stats

`sync_all()` returns a dict with:

- `success`: boolean
- `message`: short summary
- `duration`: seconds
- `stats`: e.g. `vendors_updated`, `vendors_created`, `vendors_missing_in_ghl`, `leads_updated`, `leads_created`, `leads_deleted`, `ghl_contacts_fetched`, `errors`
- `error`: present only on failure

---

## Running Sync V3

- **Programmatic:** Instantiate `EnhancedDatabaseSyncV3()` and call `sync_all()`.
- **CLI:** Run the module (e.g. `python -m api.services.enhanced_db_sync_v3`); it will prompt to confirm and then run the sync and print stats.

GHL credentials are taken from environment or `AppConfig` (e.g. `GHL_PRIVATE_TOKEN`, `GHL_LOCATION_ID`, etc.).
