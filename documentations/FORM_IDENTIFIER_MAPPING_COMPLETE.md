# Complete Form Identifier and Field Mapping Documentation

## Overview
The Lead Router Pro system uses form identifiers from WordPress Elementor forms to determine service types and map fields to the GoHighLevel CRM data dictionary.

## Webhook Endpoint Structure
All forms submit to: `/api/v1/webhooks/elementor/{form_identifier}`

## Complete Form Identifier Mapping with WordPress Form Validation

### Mapping Key
- **WordPress Form ID**: The form identifier from WordPress (with `#pro-` prefix removed)
- **System Form Identifier**: The identifier expected by the webhook system
- **Mapped Service**: The service category/name in GoHighLevel
- **Status**: ✅ = Mapped | ⚠️ = Needs Mapping | ❌ = Not Found

### Boat Maintenance Services
| WordPress Form ID | System Form Identifier | Mapped Service | Status |
|-------------------|------------------------|----------------|---------|
| `barnacle-cleaning` | `barnacle_cleaning` | Barnacle Cleaning | ✅ |
| `boat-yacht-maintenance` | `boat_yacht_maintenance` | Boat Maintenance | ⚠️ Not in FORM_TO_SPECIFIC_SERVICE |
| `bilge-cleaning` | `boat_bilge_cleaning` | Boat Bilge Cleaning | ✅ |
| `bottom-cleaning` | `bottom_cleaning` | Bottom Cleaning | ✅ |
| `boat-detailing` | `boat_detailing` | Boat Detailing | ✅ |
| `boat-oil-change` | `boat_oil_change` | Boat Oil Change | ✅ |
| `boat-wrapping-marine-protection-film` | `boat_wrapping_marine_protection` | Boat Wrapping and Marine Protection Film | ✅ |
| `ceramic-coating` | `ceramic_coating` | Ceramic Coating | ✅ |
| `jet-ski-maintenance` | `jet_ski_maintenance` | Jet Ski Maintenance | ✅ |
| `yacht-fire-detection-systems` | `yacht_fire_detection` | Yacht Fire Detection Systems | ✅ |
| `yacht-armor` | `yacht_armor` | Yacht Armor | ✅ |

### Boat Hauling and Yacht Delivery Services
| WordPress Form ID | System Form Identifier | Mapped Service | Status |
|-------------------|------------------------|----------------|---------|
| `yacht-delivery` | `yacht_delivery` | Yacht Delivery | ✅ |
| `boat-hauling-transport` | `boat_hauling` | Boat Hauling | ✅ |

### Boat and Yacht Repair Services
| WordPress Form ID | System Form Identifier | Mapped Service | Status |
|-------------------|------------------------|----------------|---------|
| `boat-yacht-repair` | `boat_yacht_repair` | Boat and Yacht Repair | ⚠️ Not in FORM_TO_SPECIFIC_SERVICE |
| `fiberglass-repair` | `fiberglass_repair` | Fiberglass Repair | ✅ |
| `welding-metal-fabrication` | `welding_metal_fabrication` | Welding & Metal Fabrication | ✅ |
| `boat-carpentry-woodwork` | `carpentry_woodwork` | Carpentry & Woodwork | ✅ |
| `riggers-masts` | - | Riggers & Masts | ❌ Not Mapped |
| `jet-ski-repair` | - | Jet Ski Repair | ❌ Not Mapped |
| `boat-canvas-upholstery` | `canvas_upholstery` | Canvas & Upholstery | ✅ |
| `boat-decking-yacht-flooring` | `decking_flooring` | Decking & Flooring | ✅ |

### Buying or Selling a Boat Services
| WordPress Form ID | System Form Identifier | Mapped Service | Status |
|-------------------|------------------------|----------------|---------|
| `buy-sell` | - | Buy/Sell | ❌ Not Mapped |
| `boat-dealers` | - | Boat Dealers | ❌ Not Mapped |
| `yacht-dealers` | - | Yacht Dealers | ❌ Not Mapped |
| `boat-surveyors` | `boat_surveyors` | Boat Surveyors | ✅ |
| `boat-financing` | - | Boat Financing | ❌ Not Mapped |
| `boat-builder` | - | Boat Builder | ❌ Not Mapped |
| `boat-broker` | `boat_brokers` | Boat Brokers | ✅ |
| `yacht-broker` | `yacht_brokers` | Yacht Brokers | ✅ |
| `yacht-builder` | `yacht_builders` | Yacht Builders | ✅ |

### Insurance Services
| WordPress Form ID | System Form Identifier | Mapped Service | Status |
|-------------------|------------------------|----------------|---------|
| `boat-insurance` | `boat_insurance` | Boat Insurance | ✅ |
| `yacht-insurance` | - | Yacht Insurance | ❌ Not Mapped |

### Engines and Generators Services
| WordPress Form ID | System Form Identifier | Mapped Service | Status |
|-------------------|------------------------|----------------|---------|
| `engine-generators-sales-service` | - | Engine/Generator Sales & Service | ❌ Not Mapped |
| `generator-sales-service` | - | Generator Sales & Service | ❌ Not Mapped |
| `generator-sales` | - | Generator Sales | ❌ Not Mapped |
| `generator-service` | `generator_service` | Generator Service | ✅ |
| `engine-service-sales` | - | Engine Service & Sales | ❌ Not Mapped |
| `engine-service` | - | Engine Service | ❌ Not Mapped |
| `engine-sales` | - | Engine Sales | ❌ Not Mapped |
| `diesel-engine-sales` | `diesel_engine_service` | Diesel Engine Service | ⚠️ Partial Match |
| `outboard-engine-sales` | `outboard_engine_service` | Outboard Engine Service | ⚠️ Partial Match |
| `inboard-engine-sales` | `inboard_engine_service` | Inboard Engine Service | ⚠️ Partial Match |
| `marine-exhause-systems-service` | - | Marine Exhaust Systems Service | ❌ Not Mapped |

### Marine Systems Services
| WordPress Form ID | System Form Identifier | Mapped Service | Status |
|-------------------|------------------------|----------------|---------|
| `marine-systems-install-sales` | - | Marine Systems Install & Sales | ❌ Not Mapped |
| `yacht-stabilizers-seakeepers` | - | Yacht Stabilizers/Seakeepers | ❌ Not Mapped |
| `instrumental-panel-dashboard` | - | Instrument Panel/Dashboard | ❌ Not Mapped |
| `yacht-ac-sales` | - | Yacht AC Sales | ❌ Not Mapped |
| `yacht-ac-service` | `yacht_ac_service` | AC Service | ✅ |
| `boat-electrical-service` | - | Boat Electrical Service | ❌ Not Mapped |
| `boat-sound-systems` | - | Boat Sound Systems | ❌ Not Mapped |
| `yacht-plumbing` | - | Yacht Plumbing | ❌ Not Mapped |
| `boat-lighting` | - | Boat Lighting | ❌ Not Mapped |
| `yacht-refrigeration-watermakers` | - | Yacht Refrigeration/Watermakers | ❌ Not Mapped |
| `marine-batteries-installation` | - | Marine Batteries Installation | ❌ Not Mapped |
| `yacht-mechanical-systems` | - | Yacht Mechanical Systems | ❌ Not Mapped |

### Docks, Seawalls and Lifts Services
| WordPress Form ID | System Form Identifier | Mapped Service | Status |
|-------------------|------------------------|----------------|---------|
| `dock-boat-lift-seawall` | - | Dock/Boat Lift/Seawall | ❌ Not Mapped |
| `boat-lift` | `boat_lift_installers` | Boat Lift Installers | ✅ |
| `floating-dock-sales` | `floating_dock_sales` | Floating Dock Sales | ✅ |
| `seawall-construction` | `seawall_construction` | Seawall Construction | ✅ |
| `davit-hydraulic-platform` | `davit_hydraulic_platform` | Davit and Hydraulic Platform | ✅ |
| `dock-seawall-piling-cleaning` | `hull_dock_seawall_piling_cleaning` | Hull Dock Seawall or Piling Cleaning | ✅ |

### Boat Towing Services
| WordPress Form ID | System Form Identifier | Mapped Service | Status |
|-------------------|------------------------|----------------|---------|
| `emergency-towing` | `emergency_tow` | Emergency Towing | ✅ |
| `towing-membership` | `towing_membership` | Towing Membership | ✅ |

### Boat Charters and Rentals Services
| WordPress Form ID | System Form Identifier | Mapped Service | Status |
|-------------------|------------------------|----------------|---------|
| `boat-charters-rentals` | - | Boat Charters & Rentals | ❌ Not Mapped |
| `boat-clubs` | - | Boat Clubs | ❌ Not Mapped |
| `yacht-catamaran-charters` | - | Yacht/Catamaran Charters | ❌ Not Mapped |
| `dive-equipment-services` | - | Dive Equipment Services | ❌ Not Mapped |
| `efoil-kiteboarding-wing-surfing` | - | eFoil/Kiteboarding/Wing Surfing | ❌ Not Mapped |
| `fishing-charters` | - | Fishing Charters | ❌ Not Mapped |
| `sailboat-charters` | - | Sailboat Charters | ❌ Not Mapped |
| `jetski-rental` | - | Jet Ski Rental | ❌ Not Mapped |
| `kayak-rental` | - | Kayak Rental | ❌ Not Mapped |
| `paddleboard-rental` | - | Paddleboard Rental | ❌ Not Mapped |
| `party-boat-charters` | - | Party Boat Charters | ❌ Not Mapped |
| `pontoon-boat-charter-rentals` | - | Pontoon Boat Charter/Rentals | ❌ Not Mapped |
| `private-yacht-charters` | - | Private Yacht Charters | ❌ Not Mapped |

### Boater Resources Services
| WordPress Form ID | System Form Identifier | Mapped Service | Status |
|-------------------|------------------------|----------------|---------|
| `boat-resources` | - | Boat Resources | ❌ Not Mapped |
| `yacht-wifi` | - | Yacht WiFi | ❌ Not Mapped |
| `provisioning` | - | Provisioning | ❌ Not Mapped |
| `boat-yacht-parts` | - | Boat/Yacht Parts | ❌ Not Mapped |
| `boat-salvage` | - | Boat Salvage | ❌ Not Mapped |
| `yacht-photography` | - | Yacht Photography | ❌ Not Mapped |
| `yacht-videography` | - | Yacht Videography | ❌ Not Mapped |
| `yacht-crew-placement` | - | Yacht Crew Placement | ❌ Not Mapped |
| `yacht-management-bookkeeping` | - | Yacht Management/Bookkeeping | ❌ Not Mapped |
| `advertising-pr-webdesign` | - | Advertising/PR/Web Design | ❌ Not Mapped |
| `maritime-attorney` | - | Maritime Attorney | ❌ Not Mapped |

### Other Services
| WordPress Form ID | System Form Identifier | Mapped Service | Status |
|-------------------|------------------------|----------------|---------|
| `fuel-delivery` | `fuel_delivery` | Fuel Delivery | ✅ |
| `waterfront-homes-for-sale` | `waterfront_homes_sale` | Waterfront Homes for Sale | ✅ |
| `sell-waterfront-home` | `sell_waterfront_home` | Sell My Waterfront Home | ✅ |
| `waterfront-new-developments` | `new_waterfront_developments` | New Waterfront Developments | ✅ |
| `maritime-education-training` | - | Maritime Education & Training | ❌ Not Mapped |
| `dock-slip-rental` | `dock_slip_rental` | Dock and Slip Rental | ✅ |
| `rent-my-dock` | `rent_my_dock` | Rent My Dock | ✅ |
| `yacht-management` | `yacht_management` | Yacht Management | ✅ |
| `wholesale-dealer-product-pricing` | `wholesale_dealer_pricing` | Wholesale or Dealer Product Pricing | ✅ |

## Summary Statistics

### Mapping Status Overview
- ✅ **Fully Mapped**: 34 forms (39%)
- ⚠️ **Partial/Needs Update**: 5 forms (6%)
- ❌ **Not Mapped**: 48 forms (55%)

### Forms Requiring Immediate Attention
The following WordPress forms do not have corresponding mappings in the system:

1. **High Priority (Common Services)**:
   - `boat-yacht-repair`
   - `riggers-masts`
   - `jet-ski-repair`
   - `boat-dealers`
   - `yacht-dealers`
   - `boat-financing`
   - `yacht-insurance`
   - `boat-electrical-service`

2. **Charter/Rental Services** (13 forms unmapped):
   - All charter and rental variants need mapping

3. **Boater Resources** (10 forms unmapped):
   - Complete category needs mapping

4. **Marine Systems** (8 forms unmapped):
   - Most marine systems services need mapping

## Recommendations

1. **Add Missing Mappings**: Update `FORM_TO_SPECIFIC_SERVICE` dictionary in `/api/routes/webhook_routes.py` to include the 48 unmapped forms

2. **Standardize Naming**: WordPress uses hyphens (`-`) while the system uses underscores (`_`). Consider adding automatic conversion

3. **Category Fallbacks**: For unmapped forms, implement category-level fallbacks based on form ID patterns

4. **Update Partial Matches**: Forms like `diesel-engine-sales` map to service variants - these need exact matching

## Field Name Mappings (Form Fields to GHL Custom Fields)

### Default Field Mappings
These mappings apply to all forms regardless of industry:

| Form Field Name | Maps to GHL Field |
|-----------------|-------------------|
| `ServiceNeeded` | `specific_service_requested` |
| `serviceNeeded` | `specific_service_requested` |
| `service_needed` | `specific_service_requested` |
| `zipCode` | `zip_code_of_service` |
| `zip_code` | `zip_code_of_service` |
| `serviceZipCode` | `zip_code_of_service` |
| `vesselMake` | `vessel_make` |
| `vessel_make` | `vessel_make` |
| `boatMake` | `vessel_make` |
| `vesselModel` | `vessel_model` |
| `vessel_model` | `vessel_model` |
| `boatModel` | `vessel_model` |
| `vesselYear` | `vessel_year` |
| `vessel_year` | `vessel_year` |
| `boatYear` | `vessel_year` |
| `vesselLength` | `vessel_length_ft` |
| `vessel_length` | `vessel_length_ft` |
| `boatLength` | `vessel_length_ft` |
| `vesselLocation` | `vessel_location__slip` |
| `vessel_location` | `vessel_location__slip` |
| `boatLocation` | `vessel_location__slip` |
| `specialRequests` | `special_requests__notes` |
| `special_requests` | `special_requests__notes` |
| `notes` | `special_requests__notes` |
| `preferredContact` | `preferred_contact_method` |
| `preferred_contact` | `preferred_contact_method` |
| `contactMethod` | `preferred_contact_method` |
| `desiredTimeline` | `desired_timeline` |
| `desired_timeline` | `desired_timeline` |
| `timeline` | `desired_timeline` |
| `budgetRange` | `budget_range` |
| `budget_range` | `budget_range` |
| `budget` | `budget_range` |

### Marine Industry Specific Mappings
Additional mappings specific to marine services:

| Form Field Name | Maps to GHL Field |
|-----------------|-------------------|
| `boatType` | `vessel_make` |
| `yachtMake` | `vessel_make` |
| `marineMake` | `vessel_make` |
| `dockLocation` | `vessel_location__slip` |
| `marinaName` | `vessel_location__slip` |
| `emergencyTow` | `need_emergency_tow` |
| `towService` | `need_emergency_tow` |
| `marineService` | `specific_service_requested` |

## Form Type Detection Logic

The system automatically detects form types based on keywords in the form identifier:

### Vendor Application Forms
Triggered by keywords: `vendor`, `network`, `join`, `application`
- Form Type: `vendor_application`
- Priority: `normal`
- Immediate Routing: `false`

### Emergency Service Forms
Triggered by keywords: `emergency`, `tow`, `breakdown`, `urgent`
- Form Type: `emergency_service`
- Priority: `high`
- Immediate Routing: `true`
- Additional Tags: `Emergency`, `High Priority`, `Urgent`

### General Inquiry Forms
Triggered by keywords: `subscribe`, `email`, `contact`, `inquiry`
- Form Type: `general_inquiry`
- Priority: `low`
- Immediate Routing: `false`

### Client Lead Forms (Default)
All other forms default to:
- Form Type: `client_lead`
- Priority: `normal`
- Immediate Routing: `true`

## Usage Examples

### Example 1: Bottom Cleaning Service Form
- WordPress Form: `#pro-bottom-cleaning`
- Form Identifier: `bottom-cleaning` → converts to `bottom_cleaning`
- Webhook URL: `/api/v1/webhooks/elementor/bottom-cleaning`
- Service Mapped To: `Bottom Cleaning`
- Status: ✅ Fully Mapped

### Example 2: Emergency Towing Form
- WordPress Form: `#pro-emergency-towing`
- Form Identifier: `emergency-towing` → converts to `emergency_tow`
- Webhook URL: `/api/v1/webhooks/elementor/emergency-towing`
- Service Mapped To: `Emergency Towing`
- Priority: `high`
- Tags Added: `Emergency`, `High Priority`, `Urgent`
- Status: ✅ Fully Mapped

### Example 3: Boat Electrical Service (Unmapped)
- WordPress Form: `#pro-boat-electrical-service`
- Form Identifier: `boat-electrical-service`
- Webhook URL: `/api/v1/webhooks/elementor/boat-electrical-service`
- Service Mapped To: **NOT MAPPED** - Will use form identifier as service name
- Status: ❌ Needs Mapping

## Action Items

1. **Critical**: Add the 48 missing form identifier mappings to `FORM_TO_SPECIFIC_SERVICE`
2. **Important**: Implement hyphen-to-underscore conversion for WordPress form IDs
3. **Consider**: Adding validation endpoint to test form mappings before deployment
4. **Document**: Update WordPress developer on expected form identifier format