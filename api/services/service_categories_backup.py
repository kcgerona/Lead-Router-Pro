"""
Service Categories - Single Source of Truth (FIXED VERSION)
Multi-level service routing system with complete service hierarchy.

This module contains the definitive service hierarchy with Level 3 services
and is the ONLY source for service category and specific service definitions.

Updated to include:
- Complete service listings from dashboard
- Level 3 service definitions
- Service aliases for better matching
- Fuzzy matching capabilities
"""

import json
import logging
from typing import Dict, List, Optional, Set, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# SERVICE HIERARCHY - COMPLETE SINGLE SOURCE OF TRUTH
# This data structure now includes ALL services from the dashboard
# with proper subcategories and Level 3 services where applicable
SERVICE_CATEGORIES = {
    "Boat Maintenance": [
        "Ceramic Coating",
        "Boat Detailing", 
        "Bottom Cleaning",
        "Oil Change",
        "Boat Oil Change",  # Alias
        "Bilge Cleaning",
        "Boat Bilge Cleaning",  # Alias
        "Jet Ski Maintenance",
        "Barnacle Cleaning",
        "Fire Detection Systems",
        "Yacht Fire Detection Systems",  # Alias
        "Boat Wrapping or Marine Protection Film",
        "Boat Wrapping and Marine Protection Film",  # Alias
        "Boat Wrapping",  # Alias
        "Marine Protection Film",  # Alias
        "Boat and Yacht Maintenance",
        "Yacht Armor",
        "Other"
    ],
    "Boat and Yacht Repair": [
        "Fiberglass Repair",
        "Welding & Metal Fabrication",
        "Carpentry & Woodwork",
        "Riggers & Masts",
        "Jet Ski Repair",
        "Boat Canvas and Upholstery",
        "Boat Decking and Yacht Flooring"
    ],
    "Engines and Generators": [
        "Outboard Engine Service",
        "Outboard Engine Sales",
        "Inboard Engine Service", 
        "Inboard Engine Sales",
        "Diesel Engine Service",
        "Diesel Engine Sales",
        "Generator Service",
        "Generator Service and Repair",  # Alias
        "Generator Sales",
        "Engine Service",  # Generic aliases
        "Engine Sales",
        "Engine Service or Sales"
    ],
    "Marine Systems": [
        "Stabilizers or Seakeepers",
        "Yacht Stabilizers and Seakeepers",  # Alias
        "Yacht Stabilizers & Seakeepers",  # Alias
        "Instrument Panel and Dashboard",
        "Instrument Panel",  # Alias
        "Dashboard",  # Alias
        "AC Sales or Service",
        "Yacht AC Sales",
        "Yacht AC Service",
        "Electrical Service",
        "Boat Electrical Service",
        "Sound System",
        "Boat Sound Systems",
        "Plumbing",
        "Yacht Plumbing",
        "Lighting",
        "Boat Lighting",
        "Refrigeration or Watermakers",
        "Yacht Refrigeration and Watermakers",  # Alias
        "Yacht Refrigeration & Watermakers",  # Alias
        "Yacht Refrigeration",  # Alias
        "Watermakers",  # Alias
        "Marine Systems Install and Sales"  # Generic
    ],
    "Boat Charters and Rentals": [
        "Boat Clubs",
        "Fishing Charters", 
        "Yacht and Catamaran Charters",
        "Sailboat Charters",
        "eFoil, Kiteboarding & Wing Surfing",
        "Dive Equipment and Services",
        "Jet Ski Rental",
        "Kayak Rental",
        "Paddleboard Rental",
        "Pontoon Boat Charter or Rental",
        "Party Boat Charter",
        "Private Yacht Charter"
    ],
    "Docks, Seawalls and Lifts": [
        "Dock and Seawall Builders or Repair",
        "Dock Builders",  # Alias
        "Seawall Builders",  # Alias
        "Dock Repair",  # Alias
        "Seawall Repair",  # Alias
        "Boat Lift Installers",
        "Boat Lift",  # Alias
        "Floating Dock Sales",
        "Floating Docks",  # Alias
        "Davit and Hydraulic Platform",
        "Davit & Hydraulic Platform",  # Alias
        "Hull Dock Seawall or Piling Cleaning",  # Alias
        "Seawall or Piling Cleaning",  # Alias
        "Piling Cleaning"  # Alias
    ],
    "Boat Towing": [
        "Get Emergency Tow",
        "Emergency Tow",  # Alias
        "Emergency Towing",  # Alias
        "Get Towing Membership",
        "Towing Membership"  # Alias
    ],
    "Fuel Delivery": [
        "Dyed Diesel Fuel (For Boats)",
        "Regular Diesel Fuel (Landside Business)",
        "Rec 90 (Ethanol Free Gas)",
        "Fuel Delivery",  # Generic
        "Diesel Delivery",  # Alias
        "Gasoline Delivery"  # Alias
    ],
    "Dock and Slip Rental": [
        "Private Dock",
        "Boat Slip",
        "Marina",
        "Mooring Ball",
        "Dock and Slip Rental",  # Generic
        "Dock Rental",  # Alias
        "Slip Rental",  # Alias
        "Rent My Dock"
    ],
    "Yacht Management": [
        "Full Service Vessel Management",
        "Full Service Yacht Management",  # Alias
        "Technical Management",
        "Crew Management",
        "Accounting & Financial Management",
        "Accounting and Financial Management",  # Alias
        "Insurance & Risk Management",
        "Insurance and Risk Management",  # Alias
        "Regulatory Compliance",
        "Yacht Management"  # Generic
    ],
    "Boater Resources": [
        "Boat or Yacht Parts",
        "Boat and Yacht Parts",  # Alias
        "Boat Parts",  # Alias
        "Yacht Parts",  # Alias
        "Vessel WiFi or Communications",
        "Yacht Wi-Fi",  # Alias
        "Yacht WiFi",  # Alias
        "Vessel WiFi",  # Alias
        "Provisioning",
        "Boat Salvage",
        "Photography or Videography",
        "Yacht Photography",  # Alias
        "Yacht Videography",  # Alias
        "Crew Management",
        "Yacht Crew Placement",  # Alias
        "Account Management and Bookkeeping",
        "Yacht Account Management and Bookkeeping",  # Alias
        "Marketing or Web Design",
        "Maritime Advertising",  # Alias
        "Maritime PR",  # Alias
        "Maritime Web Design"  # Alias
    ],
    "Buying or Selling a Boat": [
        "Boat Insurance",
        "Yacht Insurance", 
        "Yacht Broker",
        "Yacht Brokers",  # Alias
        "Boat Broker",
        "Boat Brokers",  # Alias
        "Boat Financing",
        "Boat Surveyors",
        "Yacht Dealers",
        "Boat Dealers",
        "Boat Builders",
        "Yacht Builders",
        "Buying or Selling a Boat"  # Generic
    ],
    "Maritime Education and Training": [
        "Yacht, Sailboat or Catamaran On Water Training",
        "On Water Training",  # Alias
        "Interested In Buying a Boat/Insurance Signoff",
        "Insurance Signoff",  # Alias
        "Maritime Academy",
        "Sailing Schools",
        "Captains License",
        "Captain's License",  # Alias
        "Maritime Certification",
        "Yacht Training",
        "Maritime Education and Training"  # Generic
    ],
    "Waterfront Property": [
        "Buy a Waterfront Home or Condo",
        "Waterfront Homes for Sale",  # Alias
        "Waterfront Homes For Sale",  # Alias
        "Sell a Waterfront Home or Condo",
        "Sell Your Waterfront Home",  # Alias
        "Buy a Waterfront New Development",
        "Waterfront New Developments",  # Alias
        "New Waterfront Developments",  # Alias
        "Rent a Waterfront Property",
        "Waterfront Rentals"  # Alias
    ],
    "Wholesale or Dealer Product Pricing": [
        "Apparel",
        "Boat Accessories",
        "Boat Maintenance & Cleaning Products",
        "Boat Maintenance and Cleaning Products",  # Alias
        "Boat Safety Products",
        "Diving Equipment",
        "Dock Accessories",
        "Fishing Gear",
        "Personal Watercraft",
        "Marine Electronics",  # Additional from old version
        "Engine Parts",  # Additional
        "Navigation Equipment",  # Additional
        "Wholesale or Dealer Product Pricing",  # Generic
        "Other"
    ],
    "Boat Hauling and Yacht Delivery": [
        "Yacht Delivery",
        "Boat Hauling and Transport",
        "Boat Hauling",  # Alias
        "Boat Transport",  # Alias
        "Local Boat Hauling",  # Alias
        "Long Distance Transport",  # Alias
        "International Yacht Delivery"  # Alias
    ]
}

# LEVEL 3 SERVICES - For categories with additional detail levels
LEVEL_3_SERVICES = {
    "Boat and Yacht Repair": {
        "Fiberglass Repair": [
            "Hull Crack or Structural Repair",
            "Gelcoat Repair and Color Matching",
            "Transom Repair & Reinforcement",
            "Deck Delamination & Soft Spot Repair",
            "Stringer & Bulkhead Repair",
            "Other"
        ],
        "Welding & Metal Fabrication": [
            "Aluminum or Stainless Steel Hull Repairs",
            "Custom Railings",
            "Ladders or Boarding Equipment",
            "T-Tops, Hardtops or Bimini Frames",
            "Fuel or Water Tank Fabrication",
            "Exhaust, Engine Bed or Structural Reinforcement",
            "Other"
        ],
        "Carpentry & Woodwork": [
            "Interior Woodwork and Cabinetry",
            "Teak Deck Repair or Replacement",
            "Varnishing & Wood Finishing",
            "Structural Wood Repairs",
            "Custom Furniture or Fixtures",
            "Other"
        ],
        "Riggers & Masts": [
            "Standing Rigging Inspection or Replacement",
            "Running Rigging Replacement",
            "Mast Stepping & Unstepping",
            "Mast Repair or Replacement",
            "Rig Tuning & Load Testing",
            "Fitting & Hardware Inspection",
            "Other"
        ],
        "Jet Ski Repair": [
            "Engine Diagnostics & Repair",
            "Jet Pump Rebuild or Replacement",
            "Fuel Systems Cleaning or Repair",
            "Battery or Electrical Repairs",
            "Cooling System Flush or Repair",
            "General Maintenance",
            "Other"
        ],
        "Boat Canvas and Upholstery": [
            "Upholstery",
            "Canvas or Sunshade",
            "Trim and Finish",
            "Boat Cover or T-Top",
            "Acrylic or Strataglass Enclosures",
            "Other"
        ],
        "Boat Decking and Yacht Flooring": [
            "SeaDek",
            "Real Teak Wood",
            "Cork",
            "Synthetic Teak",
            "Vinyl Flooring",
            "Tile Flooring",
            "Other"
        ]
    },
    "Engines and Generators": {
        "Generator Service": [
            "Generator Installation",
            "Routine Generator Maintenance",
            "Electrical System Integration & Transfer Switches",
            "Diagnostics & Repairs",
            "Sound Shielding & Vibration Control"
        ],
        "Outboard Engine Service": [
            "New Engine Sales",
            "Engine Refit",
            "Routine Engine Maintenance",
            "Cooling System Service",
            "Fuel System Cleaning & Repair",
            "Engine Diagnostics & Troubleshooting"
        ]
    },
    "Marine Systems": {
        "AC Sales or Service": [
            "New AC Install or Replacement",
            "AC Maintenance & Servicing",
            "Refrigerant Charging & Leak Repair",
            "Pump & Water Flow Troubleshooting",
            "Thermostat & Control Panel Upgrades"
        ],
        "Electrical Service": [
            "Battery System Install or Maintenance",
            "Wiring & Rewiring",
            "Shore Power & Inverter Systems",
            "Lighting Systems",
            "Electrical Panel & Breaker",
            "Navigation & Communication",
            "Generator Electrical Integration",
            "Solar Power & Battery Charging"
        ],
        "Boat Electrical Service": [  # Alias
            "Battery System Install or Maintenance",
            "Wiring & Rewiring",
            "Shore Power & Inverter Systems",
            "Lighting Systems",
            "Electrical Panel & Breaker",
            "Navigation & Communication",
            "Generator Electrical Integration",
            "Solar Power & Battery Charging"
        ]
    },
    "Boat Charters and Rentals": {
        "Boat Clubs": [
            "Membership Boat Club",
            "Yacht Club",
            "Private Fractional Ownership Club",
            "Sailing Club",
            "Luxury Boat Membership Club"
        ],
        "Fishing Charters": [
            "Inshore Fishing Charter",
            "Offshore (Deep Sea) Fishing Charter",
            "Reef & Wreck Fishing Charter",
            "Drift Boat Charter",
            "Freshwater Fishing Charter",
            "Private Party Boat Charter",
            "Fishing Resort Vacation"
        ],
        "Yacht and Catamaran Charters": [
            "Day Yacht Charter",
            "Day Catamaran Charter",
            "Group Yacht or Catamaran Charter",
            "Weekly or Monthly Catamaran or Yacht Charter",
            "Other"
        ],
        "Sailboat Charters": [
            "Bareboat Charter (No Captain or Crew)",
            "Skippered Charter",
            "Crewed Charter",
            "Cabin Charter",
            "Sailing Charter (Learn to Sail)",
            "Weekly or Monthly Charter"
        ],
        "eFoil, Kiteboarding & Wing Surfing": [
            "eFoil Lessons",
            "eFoil Equipment",
            "Kiteboarding Lessons",
            "Kiteboarding Equipment",
            "Wing Surfing Lessons",
            "Wing Surfing Equipment"
        ],
        "Dive Equipment and Services": [
            "Private Scuba Diving Charter",
            "Shared Scuba Diving Charter",
            "Scuba Equipment Rental",
            "Snorkel and Free Diving Charter",
            "Night Diving",
            "Underwater Scooter Rental"
        ],
        "Jet Ski Rental": [
            "Hourly Jet Ski Rental",
            "Multiple Day Jet Ski Rental",
            "Jet Ski Tour"
        ],
        "Kayak Rental": [
            "Hourly Kayak Rental",
            "Multiple Day Kayak Rental",
            "Kayak Tour"
        ],
        "Paddleboard Rental": [
            "Hourly Paddleboard Rental",
            "Multiple Day Paddleboard Rental",
            "Paddleboard Tour"
        ],
        "Pontoon Boat Charter or Rental": [
            "Hourly Pontoon Rental",
            "Multiple Day Pontoon Rental",
            "Pontoon Charter"
        ],
        "Party Boat Charter": [
            "Pontoon Party Boat",
            "Catamaran Party Boat",
            "Yacht Party Boat",
            "50+ Person Party Boat"
        ],
        "Private Yacht Charter": [
            "Private Motoryacht Charter",
            "Private Sailing Catamaran Charter",
            "Private Fishing Yacht Charter",
            "Superyacht Private Charter"
        ]
    },
    "Docks, Seawalls and Lifts": {
        "Dock and Seawall Builders or Repair": [
            "Seawall Construction or Repair",
            "New Dock",
            "Dock Repair",
            "Pilings or Structural Support",
            "Floating Docks",
            "Boat Lift",
            "Seawall or Piling Cleaning"
        ]
    },
    "Boat Maintenance": {
        "Ceramic Coating": ["Ceramic Coating"],
        "Boat Detailing": ["Boat Detailing"],
        "Bottom Painting": ["Bottom Painting"],
        "Boat and Yacht Maintenance": [
            "Ceramic Coating",
            "Boat Detailing",
            "Bottom Painting",
            "Oil Change",
            "Bilge Cleaning",
            "Jet Ski Maintenance",
            "Barnacle Cleaning",
            "Fire and Safety Equipment and Services",
            "Boat Wrapping or Marine Protection Film",
            "Other"
        ],
        "Boat Oil Change": ["Oil Change"],
        "Bilge Cleaning": ["Bilge Cleaning"],
        "Jet Ski Maintenance": ["Jet Ski Maintenance"],
        "Barnacle Cleaning": ["Barnacle Cleaning"],
        "Fire and Safety Equipment and Services": ["Fire and Safety Equipment and Services"],
        "Boat Wrapping and Marine Protection Film": ["Boat Wrapping or Marine Protection Film"]
    },
    "Boat Towing": {
        "Get Emergency Tow": [],
        "Get Towing Membership": []
    },
    "Boater Resources": {
        "Boater Resources": [
            "Boat or Yacht Parts",
            "Vessel WiFi or Communications",
            "Provisioning",
            "Boat Salvage",
            "Photography or Videography",
            "Crew Management",
            "Account Management and Bookkeeping",
            "Marketing or Web Design",
            "Vessel Management",
            "Maritime Attorney",
            "Other"
        ],
        "Yacht WiFi": [
            "New WiFi",
            "WiFi Diagnostics or Troubleshooting",
            "Boat Network",
            "Satellite",
            "Cellular",
            "Marina Connections"
        ],
        "Provisioning": [
            "Food & Beverage Provisioning",
            "Galley & Kitchen Supplies",
            "Crew Provisioning",
            "Cabin & Guest Comfort Supplies",
            "Medical & First Aid Provisioning",
            "Cleaning & Maintenance Supplies",
            "Floral & Décor Provisioning",
            "Custom Orders & Luxury Concierge Items",
            "Fishing, Dive or Watersports Supplies"
        ],
        "Boat and Yacht Parts": [
            "Engine & Propulsion Parts",
            "Electrical & Battery Systems Parts",
            "Steering & Control Systems Parts",
            "Navigation & Electronics Parts",
            "Plumbing & Water Systems Parts",
            "Hull, Deck & Hardware Parts",
            "Safety Equipment and Emergency Gear",
            "AC, Refrigeration or Watermaker Parts",
            "Canvas, Covers or Upholstery Parts",
            "Paint, Maintenance or Cleaning Supplies",
            "Trailer or Towing Components",
            "Anchoring or Mooring Gear Parts",
            "Other"
        ],
        "Yacht Photography": [
            "Listing Photography or Videography (Brokerage & Sales)",
            "Lifestyle & Charter Photography or Videography",
            "Drone & Aerial Photography or Videography",
            "Virtual Tours/3D Walkthroughs",
            "Refit or Restoration Progress Documentation",
            "Underwater Photography or Videography",
            "Event Coverage",
            "Social Media Reels/Short-Form Content"
        ],
        "Yacht Videography": [
            "Listing Photography or Videography (Brokerage & Sales)",
            "Lifestyle & Charter Photography or Videography",
            "Drone & Aerial Photography or Videography",
            "Virtual Tours/3D Walkthroughs",
            "Refit or Restoration Progress Documentation",
            "Underwater Photography or Videography",
            "Event Coverage",
            "Social Media Reels/Short-Form Content"
        ],
        "Maritime Advertising, PR and Web Design": [
            "Search Engine Optimization (SEO)",
            "Web Design",
            "PR, Influencer or Affiliate Marketing",
            "Podcasts",
            "Sponsorships",
            "Paid Ads Management",
            "Social Media Marketing",
            "Email Marketing & Automation",
            "Content Marketing and Blogging",
            "Other"
        ],
        "Yacht Crew Placement": [
            "Captain Placement",
            "Chief Stew Placement",
            "Crew Placement (Rotational)",
            "Crew Placement (Freelance)",
            "Crew Placement (Permanent)",
            "Crew Training & Certification",
            "Other"
        ],
        "Yacht Account Management and Bookkeeping": [
            "Yacht Expense Tracking & Budget Management",
            "Yacht Bookkeeping & Financial Reporting",
            "Tax Preparation (Sales, Use, Cruising Permit)",
            "Payroll & Crew Expense Management",
            "Charter Revenue Management",
            "Refit & Project Financial Oversight",
            "Insurance Claim & Documentation Support",
            "Regulatory Compliance Reporting",
            "Other"
        ],
        "Boat Salvage": ["Boat Salvage"],
        "Maritime Attorney": ["Maritime Attorney"]
    },
    "Buying or Selling a Boat": {
        "Buying or Selling a Boat or Yacht": ["Buy", "Sell", "Trade"],
        "Boat Insurance": [
            "I Just Bought the Vessel",
            "New Vessel Policy",
            "Looking For Quotes Before Purchasing Vessel"
        ],
        "Yacht Insurance": [
            "I Just Bought the Vessel",
            "New Vessel Policy",
            "Looking For Quotes Before Purchasing Vessel"
        ],
        "Yacht Builder": [],
        "Yacht Broker": [
            "Buy a New Yacht",
            "Buy a Pre-Owned Yacht",
            "Sell a Pre-Owned Yacht",
            "Trade My Yacht",
            "Looking to Charter My Yacht",
            "Looking for Yacht Management"
        ],
        "Boat Broker": [
            "Buy a New Yacht",
            "Buy a Pre-Owned Yacht",
            "Sell a Pre-Owned Yacht",
            "Trade My Yacht",
            "Looking to Charter My Yacht",
            "Looking for Yacht Management"
        ],
        "Boat Builder": [],
        "Boat Financing": [
            "New Boat Financing",
            "Used Boat Financing",
            "Refinancing"
        ],
        "Boat Surveyors": [
            "Hull & Engine(s)",
            "Thermal Imaging",
            "Insurance/Damage",
            "Hull Only",
            "Engine(s) Only"
        ],
        "Yacht Dealers": [
            "Buy a New Yacht",
            "Buy a Pre-Owned Yacht",
            "Sell a Pre-Owned Yacht",
            "Trade My Yacht",
            "Looking to Charter My Yacht",
            "Looking for Yacht Management"
        ],
        "Boat Dealers": [
            "Buy a New Boat",
            "Buy a Pre-Owned Boat",
            "Sell a Pre-Owned Boat",
            "Trade My Boat",
            "Looking to Charter My Boat",
            "Looking for Boat Management"
        ]
    },
    "Dock and Slip Rental": {
        "Dock and Slip Rental": [
            "Private Dock",
            "Boat Slip",
            "Marina",
            "Mooring Ball"
        ],
        "Rent My Dock": [
            "Private Dock",
            "Boat Slip",
            "Marina",
            "Mooring Ball"
        ]
    },
    "Fuel Delivery": {
        "Fuel Delivery": [
            "Dyed Diesel Fuel (For Boats)",
            "Regular Diesel Fuel (Landside Business)",
            "Rec 90 (Ethanol Free Gas)"
        ]
    },
    "Boat Hauling and Yacht Delivery": {
        "Yacht Delivery": [],
        "Boat Hauling and Transport": []
    },
    "Maritime Education and Training": {
        "Maritime Education and Training": [
            "Yacht, Sailboat or Catamaran On Water Training",
            "Interested In Buying a Boat or Insurance Sign Off",
            "Maritime Academy",
            "Sailing Schools",
            "Captains License"
        ]
    },
    "Yacht Management": {
        "Yacht Management": [
            "Full Service Vessel Management",
            "Technical Management (Maintenance, Repairs, Upgrades, etc)",
            "Crew Management",
            "Accounting & Financial Management",
            "Insurance & Risk Management",
            "Regulatory Compliance",
            "Maintenance & Refit Management",
            "Logistical Support (Transportation, Provisioning, Fuel or Dockage)",
            "Wash Downs and Systems Checks"
        ]
    },
    "Waterfront Property": {
        "Waterfront Homes For Sale": [
            "Buy a Waterfront Home or Condo",
            "Sell a Waterfront Home or Condo",
            "Buy a Waterfront New Development",
            "Rent a Waterfront Property"
        ],
        "Sell Your Waterfront Home": [
            "Buy a Waterfront Home or Condo",
            "Sell a Waterfront Home or Condo",
            "Buy a Waterfront New Development",
            "Rent a Waterfront Property"
        ],
        "Waterfront New Developments": [
            "Buy a Waterfront Home or Condo",
            "Sell a Waterfront Home or Condo",
            "Buy a Waterfront New Development",
            "Rent a Waterfront Property"
        ]
    },
    "Wholesale or Dealer Product Pricing": {
        "Wholesale or Dealer Product Pricing": [
            "Apparel",
            "Boat Accessories",
            "Boat Maintenance & Cleaning Products",
            "Boat Safety Products",
            "Diving Equipment",
            "Dock Accessories",
            "Fishing Gear",
            "Personal Watercraft",
            "Other"
        ]
    }
}

# SERVICE ALIASES - Maps common variations to canonical service names
# This helps with fuzzy matching and handles different naming conventions
SERVICE_ALIASES = {
    # Boat Maintenance aliases
    "boat oil change": "Oil Change",
    "oil change": "Oil Change",
    "boat bilge cleaning": "Bilge Cleaning",
    "bilge cleaning": "Bilge Cleaning",
    "yacht fire detection": "Fire Detection Systems",
    "fire detection": "Fire Detection Systems",
    "boat wrapping": "Boat Wrapping or Marine Protection Film",
    "marine protection film": "Boat Wrapping or Marine Protection Film",
    
    # Repair aliases
    "fiberglass": "Fiberglass Repair",
    "welding": "Welding & Metal Fabrication",
    "metal fabrication": "Welding & Metal Fabrication",
    "carpentry": "Carpentry & Woodwork",
    "woodwork": "Carpentry & Woodwork",
    "teak": "Teak or Woodwork",
    "canvas": "Canvas or Upholstery",
    "upholstery": "Canvas or Upholstery",
    "decking": "Boat Decking",
    "flooring": "Boat Decking",
    
    # Engine/Generator aliases
    "generator repair": "Generator Service",
    "generator maintenance": "Generator Service",
    "outboard service": "Outboard Engine Service",
    "outboard sales": "Outboard Engine Sales",
    "inboard service": "Inboard Engine Service",
    "inboard sales": "Inboard Engine Sales",
    "diesel service": "Diesel Engine Service",
    "diesel sales": "Diesel Engine Sales",
    
    # Marine Systems aliases
    "ac repair": "AC Sales or Service",
    "ac service": "AC Sales or Service",
    "air conditioning": "AC Sales or Service",
    "electrical": "Electrical Service",
    "sound system": "Sound System",
    "audio": "Sound System",
    "plumbing": "Plumbing",
    "lighting": "Lighting",
    "refrigeration": "Refrigeration or Watermakers",
    "watermaker": "Refrigeration or Watermakers",
    "stabilizers": "Stabilizers or Seakeepers",
    "seakeepers": "Stabilizers or Seekeepers",
    
    # Charter/Rental aliases
    "fishing charter": "Fishing Charter",
    "fishing charters": "Fishing Charter",
    "yacht charter": "Daily Yacht or Catamaran Charter",
    "catamaran charter": "Daily Yacht or Catamaran Charter",
    "sailboat charter": "Sailboat Charter",
    "jet ski": "Jet Ski Rental",
    "paddleboard": "Paddleboard Rental",
    "kayak": "Kayak Rental",
    "boat club": "Boat Club",
    
    # Towing aliases
    "emergency tow": "Get Emergency Tow",
    "towing": "Get Emergency Tow",
    "tow membership": "Get Towing Membership",
    
    # Other aliases
    "dock rental": "Dock and Slip Rental",
    "slip rental": "Dock and Slip Rental",
    "marina": "Marina",
    "fuel": "Fuel Delivery",
    "diesel fuel": "Dyed Diesel Fuel (For Boats)",
    "rec 90": "Rec 90 (Ethanol Free Gas)"
}

class ServiceCategoryManager:
    """
    Enhanced manager class for service category operations.
    Now includes fuzzy matching, aliases, and Level 3 services.
    """
    
    def __init__(self):
        self.categories = SERVICE_CATEGORIES
        self.level3_services = LEVEL_3_SERVICES
        self.aliases = SERVICE_ALIASES
        self.SERVICE_CATEGORIES = SERVICE_CATEGORIES  # Backward compatibility
        self._build_service_lookup_maps()
        logger.info(f"✅ ServiceCategoryManager initialized with {len(self.categories)} categories and {len(self.aliases)} aliases")
    
    def _build_service_lookup_maps(self):
        """Build reverse lookup maps for efficient searching"""
        # Service -> Category mapping
        self.service_to_category = {}
        
        # Lowercase service -> Category mapping for fuzzy matching
        self.service_fuzzy_map = {}
        
        # Keyword -> Category mapping for fallback matching
        self.keyword_to_category = {}
        
        for category, services in self.categories.items():
            # Build exact service mappings
            for service in services:
                self.service_to_category[service] = category
                self.service_fuzzy_map[service.lower()] = category
                
                # Extract keywords from service names for fuzzy matching
                keywords = self._extract_keywords(service)
                for keyword in keywords:
                    if keyword not in self.keyword_to_category:
                        self.keyword_to_category[keyword] = []
                    if category not in self.keyword_to_category[keyword]:
                        self.keyword_to_category[keyword].append(category)
        
        logger.debug(f"Built lookup maps: {len(self.service_to_category)} services, {len(self.keyword_to_category)} keywords")
    
    def _extract_keywords(self, service_name: str) -> List[str]:
        """Extract meaningful keywords from service names"""
        # Remove common words and extract meaningful terms
        common_words = {'and', 'or', 'the', 'of', 'for', 'in', 'on', 'at', 'to', 'a', 'an', '&', 'your', 'my'}
        words = service_name.lower().replace('&', ' ').replace('/', ' ').split()
        keywords = [word.strip('().,') for word in words if word.strip('().,') not in common_words and len(word.strip('().,')) > 2]
        return keywords
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings (0-1 scale)"""
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    def _services_are_related(self, service1: str, service2: str) -> bool:
        """Check if two services are actually related (not just in same category)"""
        # Extract key words from both services
        keywords1 = set(self._extract_keywords(service1))
        keywords2 = set(self._extract_keywords(service2))
        
        # Services are related if they share key terms
        common_keywords = keywords1.intersection(keywords2)
        
        # Need at least one common keyword or high similarity
        return len(common_keywords) > 0 or self._calculate_similarity(service1, service2) > 0.8
    
    # ====================
    # PRIMARY LOOKUP METHODS
    # ====================
    
    def get_all_categories(self) -> List[str]:
        """Get all service categories"""
        return list(self.categories.keys())
    
    def get_services_for_category(self, category: str) -> List[str]:
        """Get all specific services for a category (excluding aliases)"""
        services = []
        for service in self.categories.get(category, []):
            # Filter out obvious aliases (those that are variations)
            if not any(alias in service.lower() for alias in ['alias', '# alias']):
                services.append(service)
        return services
    
    def get_all_services_including_aliases(self, category: str) -> List[str]:
        """Get all services including aliases for maximum matching"""
        return self.categories.get(category, [])
    
    def get_category_for_service(self, service: str) -> Optional[str]:
        """Get the category for a specific service with fuzzy matching"""
        # Try exact match first
        if service in self.service_to_category:
            return self.service_to_category[service]
        
        # Try alias lookup
        service_lower = service.lower()
        if service_lower in self.aliases:
            canonical = self.aliases[service_lower]
            if canonical in self.service_to_category:
                return self.service_to_category[canonical]
        
        # Try fuzzy match
        if service_lower in self.service_fuzzy_map:
            return self.service_fuzzy_map[service_lower]
        
        # Try similarity matching (threshold: 0.85)
        best_match = None
        best_score = 0
        for known_service, category in self.service_to_category.items():
            score = self._calculate_similarity(service, known_service)
            if score > 0.85 and score > best_score:
                best_score = score
                best_match = category
        
        return best_match
    
    def get_level3_services(self, category: str, subcategory: str) -> List[str]:
        """Get Level 3 services for a specific subcategory"""
        if category in self.level3_services:
            # Try exact match
            if subcategory in self.level3_services[category]:
                return self.level3_services[category][subcategory]
            # Try with variations (handle & vs and)
            for key in self.level3_services[category]:
                if self._calculate_similarity(subcategory, key) > 0.9:
                    return self.level3_services[category][key]
        return []
    
    def is_valid_category(self, category: str) -> bool:
        """Check if a category is valid"""
        return category in self.categories
    
    def is_valid_service(self, service: str) -> bool:
        """Check if a service is valid (including aliases)"""
        return self.get_category_for_service(service) is not None
    
    def is_service_in_category(self, service: str, category: str) -> bool:
        """Check if a service belongs to a specific category"""
        found_category = self.get_category_for_service(service)
        return found_category == category
    
    # ====================
    # MULTI-LEVEL MATCHING METHODS
    # ====================
    
    def find_matching_services(self, search_text: str, category: str = None) -> List[str]:
        """
        Find specific services that match the search text with fuzzy matching.
        If category is provided, only search within that category.
        """
        if not search_text:
            return []
        
        search_lower = search_text.lower().strip()
        matches = []
        scores = {}
        
        # Check aliases first
        if search_lower in self.aliases:
            canonical = self.aliases[search_lower]
            if self.is_valid_service(canonical):
                matches.append(canonical)
                scores[canonical] = 1.0
        
        # Search scope
        search_categories = [category] if category and category in self.categories else self.categories.keys()
        
        for cat in search_categories:
            for service in self.get_all_services_including_aliases(cat):
                service_lower = service.lower()
                
                # Skip if already added
                if service in matches:
                    continue
                
                # Calculate similarity score
                score = 0
                
                # Exact match
                if search_lower == service_lower:
                    score = 1.0
                # Contains match
                elif search_lower in service_lower or service_lower in search_lower:
                    score = 0.9
                # Similarity match
                else:
                    score = self._calculate_similarity(search_text, service)
                
                # Add if score is high enough
                if score > 0.7:
                    matches.append(service)
                    scores[service] = score
        
        # Sort by score
        matches.sort(key=lambda x: scores.get(x, 0), reverse=True)
        return matches[:10]  # Return top 10 matches
    
    def find_best_category_match(self, search_text: str) -> Optional[str]:
        """
        Find the best category match for search text using enhanced matching.
        """
        if not search_text:
            return None
        
        search_lower = search_text.lower().strip()
        
        # Direct category name match
        for category in self.categories.keys():
            if search_lower == category.lower():
                return category
            if self._calculate_similarity(search_text, category) > 0.85:
                return category
        
        # Check if it's a known service
        category = self.get_category_for_service(search_text)
        if category:
            return category
        
        # Service-based category match
        matching_services = self.find_matching_services(search_text)
        if matching_services:
            # Return category of best matching service
            return self.get_category_for_service(matching_services[0])
        
        # Keyword-based fallback with scoring
        search_keywords = self._extract_keywords(search_text)
        category_scores = {}
        
        for keyword in search_keywords:
            if keyword in self.keyword_to_category:
                for category in self.keyword_to_category[keyword]:
                    category_scores[category] = category_scores.get(category, 0) + 1
        
        if category_scores:
            # Return category with highest score
            return max(category_scores, key=category_scores.get)
        
        # Last resort - check for any partial matches
        for category, services in self.categories.items():
            for service in services:
                if self._calculate_similarity(search_text, service) > 0.7:
                    return category
        
        return None
    
    # ====================
    # VENDOR MATCHING METHODS (ENHANCED)
    # ====================
    
    def vendor_matches_service_fuzzy(self, vendor_services: List[str], 
                                    service_requested: str, 
                                    threshold: float = 0.85) -> bool:
        """
        Check if vendor matches service with fuzzy matching.
        This addresses the exact match problem in the original code.
        """
        if not vendor_services or not service_requested:
            return False
        
        # Normalize the requested service
        service_lower = service_requested.lower()
        
        # Check aliases
        if service_lower in self.aliases:
            service_requested = self.aliases[service_lower]
        
        # Check each vendor service
        for vendor_service in vendor_services:
            # Exact match
            if vendor_service.lower() == service_lower:
                return True
            
            # Alias match
            vendor_lower = vendor_service.lower()
            if vendor_lower in self.aliases:
                if self.aliases[vendor_lower].lower() == service_lower:
                    return True
            
            # Fuzzy match
            similarity = self._calculate_similarity(vendor_service, service_requested)
            if similarity >= threshold:
                return True
            
            # Check if they're in the same category and similar enough
            vendor_category = self.get_category_for_service(vendor_service)
            requested_category = self.get_category_for_service(service_requested)
            
            if vendor_category and vendor_category == requested_category:
                # Only match if they're actually similar services, not just same category
                if similarity >= 0.75 and self._services_are_related(vendor_service, service_requested):
                    return True
        
        return False
    
    def vendor_matches_service_exact(self, vendor_services: List[str], 
                                   primary_category: str, specific_service: str) -> bool:
        """
        Enhanced vendor matching with fuzzy logic.
        Fixes the original exact match problem.
        """
        # Filter 1: Primary category match (with fuzzy matching)
        vendor_has_category = False
        for vs in vendor_services:
            vs_category = self.get_category_for_service(vs)
            if vs_category == primary_category:
                vendor_has_category = True
                break
        
        if not vendor_has_category:
            return False
        
        # Filter 2: Specific service match (with fuzzy matching)
        return self.vendor_matches_service_fuzzy(vendor_services, specific_service)
    
    def vendor_matches_category_only(self, vendor_services: List[str], 
                                   primary_category: str) -> bool:
        """
        Check if vendor matches primary category (enhanced with fuzzy logic).
        """
        for vs in vendor_services:
            vs_category = self.get_category_for_service(vs)
            if vs_category == primary_category:
                return True
        return False
    
    def vendor_matches_level3_service(self, vendor_level3_services: Dict[str, List[str]], 
                                     category: str, subcategory: str, 
                                     level3_service: str) -> bool:
        """
        Check if vendor offers a specific Level 3 service.
        """
        if not vendor_level3_services:
            return False
        
        # Check if vendor has this subcategory
        if subcategory in vendor_level3_services:
            vendor_l3_list = vendor_level3_services[subcategory]
            
            # Exact match
            if level3_service in vendor_l3_list:
                return True
            
            # Fuzzy match
            for vendor_l3 in vendor_l3_list:
                if self._calculate_similarity(vendor_l3, level3_service) > 0.85:
                    return True
        
        return False
    
    # ====================
    # UTILITY METHODS
    # ====================
    
    def get_stats(self) -> Dict:
        """Get statistics about the service hierarchy"""
        total_services = sum(len(services) for services in self.categories.values())
        total_level3 = sum(
            sum(len(l3_list) for l3_list in cat_l3.values()) 
            for cat_l3 in self.level3_services.values()
        )
        
        category_stats = {}
        for category, services in self.categories.items():
            # Count non-alias services
            non_alias_count = len([s for s in services if '# Alias' not in s])
            category_stats[category] = non_alias_count
        
        return {
            "total_categories": len(self.categories),
            "total_services": total_services,
            "total_aliases": len(self.aliases),
            "total_level3_services": total_level3,
            "average_services_per_category": round(total_services / len(self.categories), 1),
            "category_breakdown": category_stats,
            "largest_category": max(category_stats, key=category_stats.get),
            "smallest_category": min(category_stats, key=category_stats.get)
        }
    
    def validate_vendor_services(self, vendor_services: List[str]) -> Dict:
        """
        Validate vendor services with fuzzy matching and provide corrections.
        """
        valid_services = []
        invalid_services = []
        corrections = {}
        suggestions = {}
        
        for service in vendor_services:
            # Check if valid (including fuzzy match)
            category = self.get_category_for_service(service)
            
            if category:
                valid_services.append(service)
                # Check if there's a canonical version
                service_lower = service.lower()
                if service_lower in self.aliases:
                    canonical = self.aliases[service_lower]
                    if canonical != service:
                        corrections[service] = canonical
            else:
                invalid_services.append(service)
                # Find closest matches
                matches = self.find_matching_services(service)
                if matches:
                    suggestions[service] = matches[:3]  # Top 3 suggestions
        
        return {
            "valid_services": valid_services,
            "invalid_services": invalid_services,
            "corrections": corrections,
            "suggestions": suggestions,
            "validation_rate": len(valid_services) / len(vendor_services) if vendor_services else 0
        }
    
    def normalize_service_name(self, service: str) -> str:
        """
        Normalize a service name to its canonical form.
        """
        service_lower = service.lower()
        
        # Check aliases
        if service_lower in self.aliases:
            return self.aliases[service_lower]
        
        # Check if it's already valid
        if service in self.service_to_category:
            return service
        
        # Try to find best match
        matches = self.find_matching_services(service)
        if matches:
            return matches[0]
        
        return service
    
    def export_for_forms(self) -> Dict:
        """
        Export service hierarchy in format suitable for form dropdowns.
        """
        # Filter out aliases for cleaner form display
        clean_categories = {}
        for category, services in self.categories.items():
            clean_services = [s for s in services if '# Alias' not in s and 'Alias' not in s]
            clean_categories[category] = clean_services
        
        return {
            "categories": self.get_all_categories(),
            "service_hierarchy": clean_categories,
            "level3_services": self.level3_services,
            "total_categories": len(self.categories),
            "total_services": sum(len(services) for services in clean_categories.values()),
            "has_level3": list(self.level3_services.keys())
        }
    
    def classify_form_identifier(self, form_identifier: str) -> Tuple[str, Optional[str]]:
        """
        Classify form identifier to determine service category and specific service.
        Returns tuple of (category, specific_service).
        Enhanced to handle both category and service identification.
        """
        if not form_identifier:
            return ("Boater Resources", None)
        
        # Clean the identifier
        clean_id = form_identifier.replace('_', ' ').replace('-', ' ').strip()
        
        # Check if it's a direct service match
        service_category = self.get_category_for_service(clean_id)
        if service_category:
            return (service_category, self.normalize_service_name(clean_id))
        
        # Try to match as category
        best_category = self.find_best_category_match(clean_id)
        if best_category:
            # Try to extract specific service from identifier
            services = self.find_matching_services(clean_id, best_category)
            specific_service = services[0] if services else None
            return (best_category, specific_service)
        
        # Fallback
        return ("Boater Resources", None)

# Global instance for use throughout the application
service_manager = ServiceCategoryManager()

# Convenience functions for backward compatibility
def get_all_categories() -> List[str]:
    """Get all service categories"""
    return service_manager.get_all_categories()

def get_services_for_category(category: str) -> List[str]:
    """Get all specific services for a category"""
    return service_manager.get_services_for_category(category)

def find_best_category_match(search_text: str) -> Optional[str]:
    """Find the best category match for search text"""
    return service_manager.find_best_category_match(search_text)

def vendor_matches_service_exact(vendor_services: List[str], 
                               primary_category: str, specific_service: str) -> bool:
    """Check if vendor matches both category and specific service (with fuzzy matching)"""
    return service_manager.vendor_matches_service_exact(vendor_services, primary_category, specific_service)

def vendor_matches_service_fuzzy(vendor_services: List[str], 
                                service_requested: str, 
                                threshold: float = 0.85) -> bool:
    """Check if vendor matches service with fuzzy matching"""
    return service_manager.vendor_matches_service_fuzzy(vendor_services, service_requested, threshold)

def normalize_service_name(service: str) -> str:
    """Normalize a service name to its canonical form"""
    return service_manager.normalize_service_name(service)

def get_level3_services(category: str, subcategory: str) -> List[str]:
    """Get Level 3 services for a specific subcategory"""
    return service_manager.get_level3_services(category, subcategory)

# ============================================================================
# BACKWARD COMPATIBILITY FUNCTIONS
# These functions provide compatibility with the old service_mapper.py module
# ============================================================================

# Create form identifier mappings (same as service_mapper.py DOCKSIDE_PROS_SERVICES)
FORM_TO_CATEGORY_MAPPINGS = {}

# Build mappings from SERVICE_CATEGORIES
for category, services in SERVICE_CATEGORIES.items():
    # Map category name to itself (with underscores)
    category_key = category.lower().replace(' ', '_').replace(',', '').replace('&', 'and')
    FORM_TO_CATEGORY_MAPPINGS[category_key] = category
    
    # Map each service to its parent category
    for service in services:
        if isinstance(service, str):
            service_key = service.lower().replace(' ', '_').replace(',', '').replace('&', 'and')
            # Don't override if already exists (some services appear in multiple categories)
            if service_key not in FORM_TO_CATEGORY_MAPPINGS:
                FORM_TO_CATEGORY_MAPPINGS[service_key] = category

# Add specific form endpoint mappings (from service_mapper.py)
FORM_TO_CATEGORY_MAPPINGS.update({
    "engines_generators": "Engines and Generators",
    "boat_and_yacht_repair": "Boat and Yacht Repair",
    "boat_yacht_repair": "Boat and Yacht Repair",
    "fiberglass_repair": "Boat and Yacht Repair",
    "welding_metal_fabrication": "Boat and Yacht Repair",
    "welding_fabrication": "Boat and Yacht Repair",
    "carpentry_woodwork": "Boat and Yacht Repair",
    "riggers_masts": "Boat and Yacht Repair",
    "jet_ski_repair": "Boat and Yacht Repair",
    "boat_canvas_upholstery": "Boat and Yacht Repair",
    "boat_decking_yacht_flooring": "Boat and Yacht Repair",
    "boat_maintenance": "Boat Maintenance",
    "boat_detailing": "Boat Maintenance",
    "bottom_painting": "Boat Maintenance",
    "ceramic_coating": "Boat Maintenance",
    "boat_oil_change": "Boat Maintenance",
    "oil_change": "Boat Maintenance",
    "bilge_cleaning": "Boat Maintenance",
    "barnacle_cleaning": "Boat Maintenance",
    "yacht_fire_detection": "Boat Maintenance",
    "boat_wrapping_marine_protection": "Boat Maintenance",
    "boat_towing": "Boat Towing",
    "boat_towing_service": "Boat Towing",
    "emergency_towing": "Boat Towing",
    "salvage_services": "Boat Towing",
})

def get_direct_service_category(form_identifier: str) -> str:
    """
    Backward compatibility function matching service_mapper.get_service_category()
    Maps form identifiers to service categories.
    
    Args:
        form_identifier: The form identifier from the webhook
        
    Returns:
        The mapped service category
    """
    form_lower = form_identifier.lower()
    
    # Direct exact matches first
    if form_lower in FORM_TO_CATEGORY_MAPPINGS:
        category = FORM_TO_CATEGORY_MAPPINGS[form_lower]
        logger.info(f"🎯 Direct service mapping: {form_identifier} → {category}")
        return category
    
    # Keyword matching for partial matches
    for service_key, category in FORM_TO_CATEGORY_MAPPINGS.items():
        if service_key.replace("_", "") in form_lower.replace("_", ""):
            logger.info(f"🎯 Keyword service mapping: {form_identifier} → {category} (matched: {service_key})")
            return category
    
    # No fallback - return "Uncategorized" to highlight data issues
    default_category = "Uncategorized"
    logger.warning(f"⚠️ No service mapping found for: {form_identifier} → {default_category}")
    return default_category

# Alias for compatibility
get_service_category = get_direct_service_category

def get_specific_service(form_identifier: str) -> str:
    """
    Backward compatibility function matching service_mapper.get_specific_service()
    Returns the specific service name from a form identifier.
    """
    # Try to find in Level 2 services
    form_lower = form_identifier.lower().replace('_', ' ')
    
    for category, services in SERVICE_CATEGORIES.items():
        for service in services:
            if service.lower() == form_lower:
                return service
    
    # Try Level 3 services
    for category, subcategories in LEVEL_3_SERVICES.items():
        for subcategory, level3_list in subcategories.items():
            for level3 in level3_list:
                if level3.lower() == form_lower:
                    return level3
    
    # Return the form identifier with proper capitalization
    return form_identifier.replace('_', ' ').title()

def find_matching_service(text: str, category: str = None) -> Optional[str]:
    """
    Backward compatibility function matching service_mapper.find_matching_service()
    Finds a matching service in the given category or all categories.
    """
    text_lower = text.lower()
    
    if category:
        # Search within specific category
        if category in SERVICE_CATEGORIES:
            for service in SERVICE_CATEGORIES[category]:
                if service.lower() in text_lower or text_lower in service.lower():
                    return service
    else:
        # Search all categories
        for cat, services in SERVICE_CATEGORIES.items():
            for service in services:
                if service.lower() in text_lower or text_lower in service.lower():
                    return service
    
    return None

# Export backward compatibility constants
DOCKSIDE_PROS_CATEGORIES = list(SERVICE_CATEGORIES.keys())
DOCKSIDE_PROS_SERVICES = FORM_TO_CATEGORY_MAPPINGS

# Export key data structures for external use
__all__ = [
    'SERVICE_CATEGORIES',
    'LEVEL_3_SERVICES', 
    'SERVICE_ALIASES',
    'ServiceCategoryManager',
    'service_manager',
    'get_all_categories',
    'get_services_for_category',
    'find_best_category_match',
    'vendor_matches_service_exact',
    'vendor_matches_service_fuzzy',
    'normalize_service_name',
    'get_level3_services',
    # Backward compatibility exports
    'get_direct_service_category',
    'get_service_category',
    'get_specific_service',
    'find_matching_service',
    'DOCKSIDE_PROS_CATEGORIES',
    'DOCKSIDE_PROS_SERVICES'
]