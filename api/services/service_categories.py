"""
Service categories and their hierarchical relationships
Based on docksidepros.com Services Data Dictionary
"""

# LEVEL 1 -> LEVEL 2 SERVICES
# Primary categories and their subcategories
SERVICE_CATEGORIES = {
    "Boat Maintenance": [
        "Ceramic Coating",
        "Boat Detailing",
        "Bottom Painting",
        "Boat Oil Change",
        "Bilge Cleaning",
        "Jet Ski Maintenance",
        "Barnacle Cleaning",
        "Fire and Safety Equipment and Services",
        "Boat Wrapping and Marine Protection Film",
        "Finsulate"
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
        "Engines and Generators Sales/Service",
        "Generator Sales or Service",
        "Generator Sales",
        "Generator Service",
        "Engine Service or Sales",
        "Engine Service",
        "Engine Sales",
        "Diesel Engine Sales",
        "Outboard Engine Sales",
        "Inboard Engine Sales",
        "Marine Exhaust Systems and Service"
    ],
    "Marine Systems": [
        "Marine Systems Install and Sales",
        "Yacht Stabilizers and Seakeepers",
        "Instrument Panel and Dashboard",
        "Yacht AC Sales",
        "Yacht AC Service",
        "Boat Electrical Service",
        "Boat Sound Systems",
        "Yacht Plumbing",
        "Boat Lighting",
        "Yacht Refrigeration and Watermakers",
        "Marine Batteries & Battery Installation",
        "Yacht Mechanical Systems"
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
        "Dock, Boat Lift or Seawall Builders or Repair",
        "Boat Lift Installers",
        "Floating Dock Sales",
        "Seawall Construction",
        "Dock, Seawall or Piling Cleaning"
    ],
    "Boat Towing": [
        "Get Emergency Tow",
        "Get Towing Membership"
    ],
    "Fuel Delivery": [
        "Fuel Delivery"
    ],
    "Dock and Slip Rental": [
        "Dock and Slip Rental",
        "Rent My Dock"
    ],
    "Yacht Management": [
        "Yacht Management"
    ],
    "Boater Resources": [
        "Boater Resources",
        "Yacht WiFi",
        "Provisioning",
        "Boat and Yacht Parts",
        "Yacht Photography",
        "Yacht Videography",
        "Maritime Advertising, PR and Web Design",
        "Yacht Crew Placement",
        "Yacht Account Management and Bookkeeping",
        "Boat Salvage",
        "Maritime Attorney"
    ],
    "Buying or Selling a Boat": [
        "Buying or Selling a Boat or Yacht",
        "Boat Insurance",
        "Yacht Insurance",
        "Yacht Builder",
        "Yacht Broker",
        "Boat Broker",
        "Boat Builder",
        "Boat Financing",
        "Boat Surveyors",
        "Yacht Dealers",
        "Boat Dealers"
    ],
    "Maritime Education and Training": [
        "Maritime Education and Training"
    ],
    "Waterfront Property": [
        "Waterfront Homes For Sale",
        "Sell Your Waterfront Home",
        "Waterfront New Developments"
    ],
    "Wholesale or Dealer Product Pricing": [
        "Wholesale or Dealer Product Pricing"
    ],
    "Boat Hauling and Yacht Delivery": [
        "Yacht Delivery",
        "Boat Hauling and Transport"
    ]
}

# LEVEL 2 -> LEVEL 3 SERVICES (where applicable)
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
            "Video Marketing",
            "CRM Integration & Lead Nurturing"
        ],
        "Yacht Crew Placement": [
            "Captain",
            "First Mate",
            "Engineer",
            "Deckhand",
            "Chef or Cook",
            "Stew",
            "Bosun",
            "Purser for Provisioning, Accounting or Logistics",
            "Nanny, Masseuse or Personal Trainer",
            "Security Officer or Bodyguard"
        ],
        "Yacht Account Management and Bookkeeping": [
            "Operational Expense Tracking",
            "Crew Payroll & Expense Reconciliation",
            "Budget Planning & Forecasting",
            "Charter Income & Expense Reporting",
            "Vendor & Invoice Management",
            "Tax Compliance & VAT Management",
            "Insurance Premium & Policy Accounting",
            "Financial Reporting & Owner Statements"
        ],
        "Boat Salvage": [
            "Emergency Water Removal",
            "Emergency Boat Recovery",
            "Sell Boat for Parts",
            "Mold/Water Remediation"
        ],
        "Maritime Attorney": [
            "Maritime Personal Injury Case",
            "Marine Insurance Dispute",
            "Maritime Commercial and Contract Case",
            "Environmental & Regulatory Compliance",
            "Vessel Documentation and Transactions",
            "Maritime Criminal Defense",
            "Other"
        ]
    },
    "Buying or Selling a Boat": {
        "Buying or Selling a Boat or Yacht": [
            "Buy",
            "Sell",
            "Trade"
        ],
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
        "Yacht Broker": [
            "Buy a New Yacht",
            "Buy a Pre-Owned Yacht",
            "Sell a Pre-Owned Yacht",
            "Trade My Yacht",
            "Looking to Charter My Yacht",
            "Looking for Yacht Management"
        ],
        "Boat Broker": [
            "Buy a New Boat",
            "Buy a Pre-Owned Boat",
            "Sell a Pre-Owned Boat",
            "Trade My Boat",
            "Looking to Charter My Boat",
            "Looking for Boat Management"
        ],
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
    "Docks, Seawalls and Lifts": {
        "Dock, Boat Lift or Seawall Builders or Repair": [
            "Seawall Construction or Repair",
            "New Dock",
            "Dock Repair",
            "Pilings or Structural Support",
            "Floating Docks",
            "Boat Lift",
            "Seawall or Piling Cleaning"
        ],
        "Boat Lift Installers": [
            "New Boat Lift",
            "Boat Lift Installation",
            "Lift Motor & Gearbox Repair",
            "Cable & Pulley Replacement",
            "Annual Maintenance & Alignment"
        ],
        "Floating Dock Sales": [
            "New Floating Dock",
            "Floating Dock Installation",
            "Floating Dock Repair & Float Replacement",
            "Custom Modifications & Add-Ons",
            "Seasonal Maintenance & Dock Repositioning"
        ],
        "Seawall Construction": [
            "New Seawall Construction",
            "Seawall Repair & Reinforcement",
            "Cap Replacement & Restoration",
            "Erosion Control & Backfill Replacement",
            "Seawall Maintenance or Inspection"
        ],
        "Dock, Seawall or Piling Cleaning": [
            "Dock Cleaning",
            "Seawall Cleaning",
            "Piling Cleaning",
            "Commercial or Industrial Requests"
        ]
    },
    "Engines and Generators": {
        "Engines and Generators Sales/Service": [
            "Outboard Engine Service",
            "Outboard Engine Sales",
            "Inboard Engine Service",
            "Inboard Engine Sales",
            "Diesel Engine Service",
            "Diesel Engine Sales",
            "Generator Service",
            "Generator Sales",
            "Exhaust Systems & Service"
        ],
        "Generator Sales or Service": [
            "Generator Installation",
            "Routine Generator Maintenance",
            "Electrical System Integration & Transfer Switches",
            "Diagnostics & Repairs",
            "Sound Shielding & Vibration Control",
            "Generator Sales",
            "Exhaust Systems & Service"
        ],
        "Generator Sales": [
            "Cummins Onan",
            "Kohler",
            "Northern Lights",
            "Caterpillar",
            "Volvo Penta",
            "NextGen",
            "Phasor",
            "Fischer Panda",
            "Not Sure/Other"
        ],
        "Generator Service": [
            "Generator Installation",
            "Routine Generator Maintenance",
            "Electrical System Integration & Transfer Switches",
            "Diagnostics & Repairs",
            "Sound Shielding & Vibration Control",
            "Exhaust Systems & Service"
        ],
        "Engine Service or Sales": [
            "Diesel Engine Sales",
            "Inboard Engine Sales",
            "Outboard Engine Sales",
            "Diesel Engine Maintenance",
            "Outboard Engine Maintenance",
            "Inboard Engine Maintenance",
            "Diesel Engine Repair, Rebuild or Refit",
            "Outboard Engine Repair, Rebuild or Refit",
            "Inboard Engine Repair, Rebuild or Refit",
            "Exhaust Systems & Service"
        ],
        "Engine Service": [
            "Diesel Engine Maintenance",
            "Outboard Engine Maintenance",
            "Inboard Engine Maintenance",
            "Diesel Engine Repair, Rebuild or Refit",
            "Outboard Engine Repair, Rebuild or Refit",
            "Inboard Engine Repair, Rebuild or Refit",
            "Exhaust Systems & Service",
            "Sound Shielding & Vibration Control"
        ],
        "Engine Sales": [
            "Diesel Engine Sales",
            "Inboard Engine Sales",
            "Outboard Engine Sales",
            "Electric Engine Sales"
        ],
        "Diesel Engine Sales": [
            "Caterpillar",
            "MAN Engines",
            "MTU",
            "Volvo Penta",
            "Cummins Marine",
            "Yanmar Marine",
            "Perkins Marine",
            "John Deer Marine"
        ],
        "Outboard Engine Sales": [
            "Mercury",
            "Yamaha",
            "Suzuki",
            "Honda",
            "Seven Marine"
        ],
        "Inboard Engine Sales": [
            "Caterpillar",
            "MAN Engines",
            "MTU",
            "Volvo Penta",
            "Cummins Marine",
            "Yanmar Marine"
        ],
        "Marine Exhaust Systems and Service": [
            "Marine Exhaust Fabrication",
            "Exhaust System Repair & Overhaul",
            "Exhaust Insulation & Lagging",
            "Exhaust Filtration & Emissions Compliance",
            "Exhaust Leak Detection & Corrosion Prevention"
        ]
    },
    "Fuel Delivery": {
        "Fuel Delivery": [
            "Dyed Diesel Fuel (For Boats)",
            "Regular Diesel Fuel (Landside Business)",
            "Rec 90 (Ethanol Free Gas)"
        ]
    },
    "Marine Systems": {
        "Marine Systems Install and Sales": [
            "Stabilizers or Seakeepers",
            "Instrument Panel and Dashboard",
            "AC Sales or Service",
            "Electrical Service",
            "Sound System",
            "Plumbing",
            "Lighting",
            "Refrigeration or Watermakers",
            "Marine Batteries & Batteries Installation",
            "Yacht Mechanical Systems"
        ],
        "Yacht Stabilizers and Seakeepers": [
            "New Seakeeper Install",
            "Other Stabilizer Install",
            "Stabilizer Maintenance",
            "Stabilizer Retrofit or Upgrades"
        ],
        "Instrument Panel and Dashboard": [
            "Electronic Dashboard Install or Upgrades",
            "Instrument Panel Rewiring & Troubleshooting",
            "Custom Dashboard Fabrication & Refacing",
            "Gauge Replacement & Calibration",
            "Backlighting & Switch Panel Modernization"
        ],
        "Yacht AC Service": [
            "New AC Install or Replacement",
            "AC Maintenance & Servicing",
            "Refrigerant Charging & Leak Repair",
            "Pump & Water Flow Troubleshooting",
            "Thermostat & Control Panel Upgrades"
        ],
        "Boat Electrical Service": [
            "Battery System Install or Maintenance",
            "Wiring & Rewiring",
            "Shore Power & Inverter Systems",
            "Lighting Systems",
            "Electrical Panel & Breaker",
            "Navigation & Communication",
            "Generator Electrical Integration",
            "Solar Power & Battery Charging"
        ],
        "Boat Sound Systems": [
            "Marine Audio System Install",
            "Speaker & Subwoofer Upgrades",
            "Amplifier Setup & Tuning",
            "Multi-Zone Audio Configuration",
            "Troubleshooting & System Repairs"
        ],
        "Yacht Plumbing": [
            "Freshwater System Install or Repair",
            "Marine Head & Toilet Systems",
            "Greywater or Blackwater Tank Maintenance",
            "Bilge Pump Install or Drainage",
            "Watermaker (Desalinator) Service & Install"
        ],
        "Boat Lighting": [
            "Navigation & Anchor Light Install",
            "Underwater Lighting",
            "Interior Cabin Lighting",
            "Deck, Cockpit & Courtesy Lighting",
            "Electrical Troubleshooting & Wiring"
        ],
        "Yacht Refrigeration and Watermakers": [
            "Marine Refrigerator & Freezer Install",
            "Refrigeration System Repairs & Troubleshooting",
            "Watermaker (Desalinator) Install",
            "Watermaker Maintenance & Servicing",
            "Cold Plate & Evaporator Upgrades"
        ],
        "Marine Batteries & Battery Installation": [
            "Marine Battery Sales",
            "Marine Battery Installation",
            "Battery Bank Design & Upgrades",
            "Charging System Integration",
            "Battery Testing & Maintenance"
        ],
        "Yacht Mechanical Systems": [
            "Propulsion Systems",
            "Steering & Rudder Systems",
            "Hydraulic Systems",
            "Fuel Systems",
            "Bilge & Waste Systems"
        ]
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

# Service Manager class for backwards compatibility
class ServiceManager:
    """Manages service categories and their relationships"""
    
    def get_all_categories(self):
        """Get all primary service categories"""
        return list(SERVICE_CATEGORIES.keys())
    
    def get_subcategories(self, category):
        """Get subcategories for a primary category"""
        return SERVICE_CATEGORIES.get(category, [])
    
    def get_level3_services(self, category, subcategory):
        """Get level 3 services for a subcategory"""
        if category in LEVEL_3_SERVICES:
            return LEVEL_3_SERVICES[category].get(subcategory, [])
        return []
    
    def has_level3_services(self, category):
        """Check if a category has level 3 services"""
        return category in LEVEL_3_SERVICES

# Create singleton instance
service_manager = ServiceManager()


# Helper functions for service mapping
def get_direct_service_category(service_request):
    """Get the direct service category for a request"""
    service_lower = service_request.lower().strip()
    
    # Check if its a primary category
    for category in SERVICE_CATEGORIES:
        if category.lower() == service_lower:
            return category
    
    # Check if its a subcategory
    for category, subcategories in SERVICE_CATEGORIES.items():
        for subcat in subcategories:
            if subcat.lower() == service_lower:
                return category
    
    # Check Level 3 services
    for category, subcats in LEVEL_3_SERVICES.items():
        for subcat, services in subcats.items():
            for service in services:
                if service.lower() == service_lower:
                    return category
    
    return None

def get_specific_service(service_request):
    """Get the specific service for a request"""
    service_lower = service_request.lower().strip()
    
    # Check all Level 3 services first
    for category, subcats in LEVEL_3_SERVICES.items():
        for subcat, services in subcats.items():
            for service in services:
                if service.lower() == service_lower:
                    return service
    
    # Check Level 2 services
    for category, subcategories in SERVICE_CATEGORIES.items():
        for subcat in subcategories:
            if subcat.lower() == service_lower:
                return subcat
    
    # Check Level 1 categories
    for category in SERVICE_CATEGORIES:
        if category.lower() == service_lower:
            return category
    
    return service_request

def find_matching_service(service_request):
    """Find the best matching service for a request"""
    service_lower = service_request.lower().strip()
    
    # Try exact match first
    exact = get_specific_service(service_request)
    if exact != service_request:
        return exact
    
    # Try partial match
    for category, subcats in LEVEL_3_SERVICES.items():
        for subcat, services in subcats.items():
            for service in services:
                if service_lower in service.lower() or service.lower() in service_lower:
                    return service
    
    for category, subcategories in SERVICE_CATEGORIES.items():
        for subcat in subcategories:
            if service_lower in subcat.lower() or subcat.lower() in service_lower:
                return subcat
    
    return service_request

def normalize_service_name(service_name):
    """Normalize a service name for comparison"""
    if not service_name:
        return ""
    return service_name.strip().lower()


# Legacy support for DOCKSIDE_PROS_CATEGORIES
DOCKSIDE_PROS_CATEGORIES = SERVICE_CATEGORIES

# Legacy support for DOCKSIDE_PROS_SERVICES
DOCKSIDE_PROS_SERVICES = LEVEL_3_SERVICES
