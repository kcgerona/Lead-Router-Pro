#!/usr/bin/env python3
"""
Fix service_categories.py based on the services data dictionary
"""

# Define the proper structure based on the data dictionary

SERVICE_CATEGORIES = {
    "Boat Maintenance": [
        "Ceramic Coating",
        "Boat Detailing", 
        "Bottom Painting",
        "Boat and Yacht Maintenance",
        "Boat Oil Change",
        "Bilge Cleaning",
        "Jet Ski Maintenance",
        "Barnacle Cleaning",
        "Fire and Safety Equipment and Services",
        "Boat Wrapping and Marine Protection Film"
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
        "Boat Charters and Rentals",  # Generic subcategory with its own Level 3
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
        "Boat Charters and Rentals": [
            "Weekly or Monthly Yacht or Catamaran Charter",
            "Daily Yacht or Catamaran Charter",
            "Sailboat Charter",
            "Fishing Charter",
            "Party Boat Charter",
            "Pontoon Boat Charter or Rental",
            "Jet Ski Rental",
            "Paddleboard Rental",
            "Kayak Rental",
            "eFoil, Kiteboarding or Wing Surfing Lessons",
            "Boat Club",
            "Boat Rental"
        ],
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
    # Continue with remaining categories that have Level 3 services...
}

print("Service structure defined based on data dictionary")
print(f"Total Level 1 categories: {len(SERVICE_CATEGORIES)}")
print(f"Categories with Level 3 services: {len(LEVEL_3_SERVICES)}")