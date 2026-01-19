"""
DockSidePros.com Comprehensive Services Data Dictionary
This is the SINGLE SOURCE OF TRUTH for all service categories, subcategories, and specific services.
Based on the official DockSidePros.com service hierarchy.

ALL files in the codebase should import and use this dictionary.
"""

# Complete service hierarchy with categories, subcategories, and Level 3 specific services
DOCKSIDE_PROS_SERVICES = {
    "1": {
        "name": "Boat and Yacht Repair",
        "subcategories": {
            "Fiberglass Repair": {
                "request_a_pro": True,
                "specific_services": [
                    "Hull Crack or Structural Repair",
                    "Gelcoat Repair and Color Matching",
                    "Transom Repair & Reinforcement",
                    "Deck Delamination & Soft Spot Repair",
                    "Stringer & Bulkhead Repair",
                    "Other"
                ]
            },
            "Welding & Metal Fabrication": {
                "request_a_pro": True,
                "specific_services": [
                    "Aluminum or Stainless Steel Hull Repairs",
                    "Custom Railings",
                    "Ladders or Boarding Equipment",
                    "T-Tops, Hardtops or Bimini Frames",
                    "Fuel or Water Tank Fabrication",
                    "Exhaust, Engine Bed or Structural Reinforcement",
                    "Other"
                ]
            },
            "Carpentry & Woodwork": {
                "request_a_pro": True,
                "specific_services": [
                    "Interior Woodwork and Cabinetry",
                    "Teak Deck Repair or Replacement",
                    "Varnishing & Wood Finishing",
                    "Structural Wood Repairs",
                    "Custom Furniture or Fixtures",
                    "Other"
                ]
            },
            "Riggers & Masts": {
                "request_a_pro": True,
                "specific_services": [
                    "Standing Rigging Inspection or Replacement",
                    "Running Rigging Replacement",
                    "Mast Stepping & Unstepping",
                    "Mast Repair or Replacement",
                    "Rig Tuning & Load Testing",
                    "Fitting & Hardware Inspection",
                    "Other"
                ]
            },
            "Jet Ski Repair": {
                "request_a_pro": True,
                "specific_services": [
                    "Engine Diagnostics & Repair",
                    "Jet Pump Rebuild or Replacement",
                    "Fuel Systems Cleaning or Repair",
                    "Battery or Electrical Repairs",
                    "Cooling System Flush or Repair",
                    "General Maintenance",
                    "Other"
                ]
            },
            "Boat Canvas and Upholstery": {
                "request_a_pro": True,
                "specific_services": [
                    "Upholstery",
                    "Canvas or Sunshade",
                    "Trim and Finish",
                    "Boat Cover or T-Top",
                    "Acrylic or Strataglass Enclosures",
                    "Other"
                ]
            },
            "Boat Decking and Yacht Flooring": {
                "request_a_pro": True,
                "specific_services": [
                    "SeaDek",
                    "Real Teak Wood",
                    "Cork",
                    "Synthetic Teak",
                    "Vinyl Flooring",
                    "Tile Flooring",
                    "Other"
                ]
            }
        }
    },
    "2": {
        "name": "Boat Charters and Rentals",
        "subcategories": {
            "Boat Charters and Rentals": {
                "request_a_pro": True,
                "specific_services": [
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
                ]
            },
            "Boat Clubs": {
                "request_a_pro": True,
                "specific_services": [
                    "Membership Boat Club",
                    "Yacht Club",
                    "Private Fractional Ownership Club",
                    "Sailing Club",
                    "Luxury Boat Membership Club"
                ]
            },
            "Fishing Charters": {
                "request_a_pro": True,
                "specific_services": [
                    "Inshore Fishing Charter",
                    "Offshore (Deep Sea) Fishing Charter",
                    "Reef & Wreck Fishing Charter",
                    "Drift Boat Charter",
                    "Freshwater Fishing Charter",
                    "Private Party Boat Charter",
                    "Fishing Resort Vacation"
                ]
            },
            "Yacht and Catamaran Charters": {
                "request_a_pro": True,
                "specific_services": [
                    "Day Yacht Charter",
                    "Day Catamaran Charter",
                    "Group Yacht or Catamaran Charter",
                    "Weekly or Monthly Catamaran or Yacht Charter",
                    "Other"
                ]
            },
            "Sailboat Charters": {
                "request_a_pro": True,
                "specific_services": [
                    "Bareboat Charter (No Captain or Crew)",
                    "Skippered Charter",
                    "Crewed Charter",
                    "Cabin Charter",
                    "Sailing Charter (Learn to Sail)",
                    "Weekly or Monthly Charter"
                ]
            },
            "eFoil, Kiteboarding & Wing Surfing": {
                "request_a_pro": True,
                "specific_services": [
                    "eFoil Lessons",
                    "eFoil Equipment",
                    "Kiteboarding Lessons",
                    "Kiteboarding Equipment",
                    "Wing Surfing Lessons",
                    "Wing Surfing Equipment"
                ]
            },
            "Dive Equipment and Services": {
                "request_a_pro": True,
                "specific_services": [
                    "Private Scuba Diving Charter",
                    "Shared Scuba Diving Charter",
                    "Scuba Equipment Rental",
                    "Snorkel and Free Diving Charter",
                    "Night Diving",
                    "Underwater Scooter Rental"
                ]
            },
            "Jet Ski Rental": {
                "request_a_pro": True,
                "specific_services": [
                    "Hourly Jet Ski Rental",
                    "Multiple Day Jet Ski Rental",
                    "Jet Ski Tour"
                ]
            },
            "Kayak Rental": {
                "request_a_pro": True,
                "specific_services": [
                    "Hourly Kayak Rental",
                    "Multiple Day Kayak Rental",
                    "Kayak Tour"
                ]
            },
            "Paddleboard Rental": {
                "request_a_pro": True,
                "specific_services": [
                    "Hourly Paddleboard Rental",
                    "Multiple Day Paddleboard Rental",
                    "Paddleboard Tour"
                ]
            },
            "Pontoon Boat Charter or Rental": {
                "request_a_pro": True,
                "specific_services": [
                    "Hourly Pontoon Rental",
                    "Multiple Day Pontoon Rental",
                    "Pontoon Charter"
                ]
            },
            "Party Boat Charter": {
                "request_a_pro": True,
                "specific_services": [
                    "Pontoon Party Boat",
                    "Catamaran Party Boat",
                    "Yacht Party Boat",
                    "50+ Person Party Boat"
                ]
            },
            "Private Yacht Charter": {
                "request_a_pro": True,
                "specific_services": [
                    "Private Motoryacht Charter",
                    "Private Sailing Catamaran Charter",
                    "Private Fishing Yacht Charter",
                    "Superyacht Private Charter"
                ]
            }
        }
    },
    "3": {
        "name": "Boat Hauling and Yacht Delivery",
        "subcategories": {
            "Yacht Delivery": {
                "request_a_pro": True,
                "specific_services": [],  # Hard coded to Premium Captains Vendor
                "hardcoded_vendor": "Premium Captains"
            },
            "Boat Hauling and Transport": {
                "request_a_pro": True,
                "specific_services": [],  # Hard coded to We Will Transport It Vendor
                "hardcoded_vendor": "We Will Transport It"
            }
        }
    },
    "4": {
        "name": "Boat Maintenance",
        "subcategories": {
            "Ceramic Coating": {
                "request_a_pro": True,
                "specific_services": ["Ceramic Coating"]
            },
            "Boat Detailing": {
                "request_a_pro": True,
                "specific_services": ["Boat Detailing"]
            },
            "Bottom Painting": {
                "request_a_pro": True,
                "specific_services": ["Bottom Painting"]
            },
            "Boat and Yacht Maintenance": {
                "request_a_pro": True,
                "specific_services": [
                    "Ceramic Coating",
                    "Boat Detailing",
                    "Bottom Painting",
                    "Oil Change",
                    "Bilge Cleaning",
                    "Jet Ski Maintenance",
                    "Barnacle Cleaning",
                    "Fire and Safety Equipment and Services",
                    "Boat Wrapping or Marine Protection Film",
                    "Finsulate",
                    "Other"
                ]
            },
            "Boat Oil Change": {
                "request_a_pro": True,
                "specific_services": ["Oil Change"]
            },
            "Bilge Cleaning": {
                "request_a_pro": True,
                "specific_services": ["Bilge Cleaning"]
            },
            "Jet Ski Maintenance": {
                "request_a_pro": True,
                "specific_services": ["Jet Ski Maintenance"]
            },
            "Barnacle Cleaning": {
                "request_a_pro": True,
                "specific_services": ["Barnacle Cleaning"]
            },
            "Fire and Safety Equipment and Services": {
                "request_a_pro": True,
                "specific_services": ["Fire and Safety Equipment and Services"]
            },
            "Boat Wrapping and Marine Protection Film": {
                "request_a_pro": True,
                "specific_services": ["Boat Wrapping or Marine Protection Film"]
            },
            "Finsulate": {
                "request_a_pro": True,
                "specific_services": ["Finsulate"]
            }
        }
    },
    "5": {
        "name": "Boat Towing",
        "subcategories": {
            "Get Emergency Tow": {
                "request_a_pro": True,
                "specific_services": [],  # Hard coded to Tow Boat US Vendor
                "hardcoded_vendor": "Tow Boat US"
            },
            "Get Towing Membership": {
                "request_a_pro": True,
                "specific_services": []
            }
        }
    },
    "6": {
        "name": "Boater Resources",
        "subcategories": {
            "Boater Resources": {
                "request_a_pro": True,
                "specific_services": [
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
                ]
            },
            "Yacht WiFi": {
                "request_a_pro": True,
                "specific_services": [
                    "New WiFi",
                    "WiFi Diagnostics or Troubleshooting",
                    "Boat Network",
                    "Satellite",
                    "Cellular",
                    "Marina Connections"
                ]
            },
            "Provisioning": {
                "request_a_pro": True,
                "specific_services": [
                    "Food & Beverage Provisioning",
                    "Galley & Kitchen Supplies",
                    "Crew Provisioning",
                    "Cabin & Guest Comfort Supplies",
                    "Medical & First Aid Provisioning",
                    "Cleaning & Maintenance Supplies",
                    "Floral & Décor Provisioning",
                    "Custom Orders & Luxury Concierge Items",
                    "Fishing, Dive or Watersports Supplies"
                ]
            },
            "Boat and Yacht Parts": {
                "request_a_pro": True,
                "specific_services": [
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
                ]
            },
            "Yacht Photography": {
                "request_a_pro": True,
                "specific_services": [
                    "Listing Photography or Videography (Brokerage & Sales)",
                    "Lifestyle & Charter Photography or Videography",
                    "Drone & Aerial Photography or Videography",
                    "Virtual Tours/3D Walkthroughs",
                    "Refit or Restoration Progress Documentation",
                    "Underwater Photography or Videography",
                    "Event Coverage",
                    "Social Media Reels/Short-Form Content"
                ]
            },
            "Yacht Videography": {
                "request_a_pro": True,
                "specific_services": [
                    "Listing Photography or Videography (Brokerage & Sales)",
                    "Lifestyle & Charter Photography or Videography",
                    "Drone & Aerial Photography or Videography",
                    "Virtual Tours/3D Walkthroughs",
                    "Refit or Restoration Progress Documentation",
                    "Underwater Photography or Videography",
                    "Event Coverage",
                    "Social Media Reels/Short-Form Content"
                ]
            },
            "Maritime Advertising, PR and Web Design": {
                "request_a_pro": True,
                "specific_services": [
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
                ]
            },
            "Yacht Crew Placement": {
                "request_a_pro": True,
                "specific_services": [
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
                ]
            },
            "Yacht Account Management and Bookkeeping": {
                "request_a_pro": True,
                "specific_services": [
                    "Operational Expense Tracking",
                    "Crew Payroll & Expense Reconciliation",
                    "Budget Planning & Forecasting",
                    "Charter Income & Expense Reporting",
                    "Vendor & Invoice Management",
                    "Tax Compliance & VAT Management",
                    "Insurance Premium & Policy Accounting",
                    "Financial Reporting & Owner Statements"
                ]
            },
            "Boat Salvage": {
                "request_a_pro": True,
                "specific_services": [
                    "Emergency Water Removal",
                    "Emergency Boat Recovery",
                    "Sell Boat for Parts",
                    "Mold/Water Remediation"
                ]
            },
            "Maritime Attorney": {
                "request_a_pro": True,
                "specific_services": [
                    "Maritime Personal Injury Case",
                    "Marine Insurance Dispute",
                    "Maritime Commercial and Contract Case",
                    "Environmental & Regulatory Compliance",
                    "Vessel Documentation and Transactions",
                    "Maritime Criminal Defense",
                    "Other"
                ]
            }
        }
    },
    "7": {
        "name": "Buying or Selling a Boat",
        "subcategories": {
            "Buying or Selling a Boat or Yacht": {
                "request_a_pro": True,
                "specific_services": [
                    "Buy",
                    "Sell",
                    "Trade"
                ]
            },
            "Boat Insurance": {
                "request_a_pro": True,
                "specific_services": [
                    "I Just Bought the Vessel",
                    "New Vessel Policy",
                    "Looking For Quotes Before Purchasing Vessel"
                ]
            },
            "Yacht Insurance": {
                "request_a_pro": True,
                "specific_services": [
                    "I Just Bought the Vessel",
                    "New Vessel Policy",
                    "Looking For Quotes Before Purchasing Vessel"
                ]
            },
            "Yacht Builder": {
                "request_a_pro": True,
                "specific_services": [],  # Hard coded
                "hardcoded_vendor": "Yacht Builder"
            },
            "Yacht Broker": {
                "request_a_pro": True,
                "specific_services": [
                    "Buy a New Yacht",
                    "Buy a Pre-Owned Yacht",
                    "Sell a Pre-Owned Yacht",
                    "Trade My Yacht",
                    "Looking to Charter My Yacht",
                    "Looking for Yacht Management"
                ]
            },
            "Boat Broker": {
                "request_a_pro": True,
                "specific_services": [
                    "Buy a New Yacht",
                    "Buy a Pre-Owned Yacht",
                    "Sell a Pre-Owned Yacht",
                    "Trade My Yacht",
                    "Looking to Charter My Yacht",
                    "Looking for Yacht Management"
                ]
            },
            "Boat Builder": {
                "request_a_pro": True,
                "specific_services": [],  # Hard coded
                "hardcoded_vendor": "Boat Builder"
            },
            "Boat Financing": {
                "request_a_pro": True,
                "specific_services": [
                    "New Boat Financing",
                    "Used Boat Financing",
                    "Refinancing"
                ]
            },
            "Boat Surveyors": {
                "request_a_pro": True,
                "specific_services": [
                    "Hull & Engine(s)",
                    "Thermal Imaging",
                    "Insurance/Damage",
                    "Hull Only",
                    "Engine(s) Only"
                ]
            },
            "Yacht Dealers": {
                "request_a_pro": True,
                "specific_services": [
                    "Buy a New Yacht",
                    "Buy a Pre-Owned Yacht",
                    "Sell a Pre-Owned Yacht",
                    "Trade My Yacht",
                    "Looking to Charter My Yacht",
                    "Looking for Yacht Management"
                ]
            },
            "Boat Dealers": {
                "request_a_pro": True,
                "specific_services": [
                    "Buy a New Boat",
                    "Buy a Pre-Owned Boat",
                    "Sell a Pre-Owned Boat",
                    "Trade My Boat",
                    "Looking to Charter My Boat",
                    "Looking for Boat Management"
                ]
            }
        }
    },
    "8": {
        "name": "Dock and Slip Rental",
        "subcategories": {
            "Dock and Slip Rental": {
                "request_a_pro": True,
                "specific_services": [
                    "Private Dock",
                    "Boat Slip",
                    "Marina",
                    "Mooring Ball"
                ]
            },
            "Rent My Dock": {
                "request_a_pro": True,
                "specific_services": [
                    "Private Dock",
                    "Boat Slip",
                    "Marina",
                    "Mooring Ball"
                ]
            }
        }
    },
    "9": {
        "name": "Docks, Seawalls and Lifts",
        "subcategories": {
            "Dock, Boat Lift or Seawall Builders or Repair": {
                "request_a_pro": True,
                "specific_services": [
                    "Seawall Construction or Repair",
                    "New Dock",
                    "Dock Repair",
                    "Pilings or Structural Support",
                    "Floating Docks",
                    "Boat Lift",
                    "Seawall or Piling Cleaning"
                ]
            },
            "Boat Lift Installers": {
                "request_a_pro": True,
                "specific_services": [
                    "New Boat Lift",
                    "Boat Lift Installation",
                    "Lift Motor & Gearbox Repair",
                    "Cable & Pulley Replacement",
                    "Annual Maintenance & Alignment"
                ]
            },
            "Floating Dock Sales": {
                "request_a_pro": True,
                "specific_services": [
                    "New Floating Dock",
                    "Floating Dock Installation",
                    "Floating Dock Repair & Float Replacement",
                    "Custom Modifications & Add-Ons",
                    "Seasonal Maintenance & Dock Repositioning"
                ]
            },
            "Seawall Construction": {
                "request_a_pro": True,
                "specific_services": [
                    "New Seawall Construction",
                    "Seawall Repair & Reinforcement",
                    "Cap Replacement & Restoration",
                    "Erosion Control & Backfill Replacement",
                    "Seawall Maintenance or Inspection"
                ]
            },
            "Dock, Seawall or Piling Cleaning": {
                "request_a_pro": True,
                "specific_services": [
                    "Dock Cleaning",
                    "Seawall Cleaning",
                    "Piling Cleaning",
                    "Commercial or Industrial Requests"
                ]
            }
        }
    },
    "10": {
        "name": "Engines and Generators",
        "subcategories": {
            "Engines and Generators Sales/Service": {
                "request_a_pro": True,
                "specific_services": [
                    "Outboard Engine Service",
                    "Outboard Engine Sales",
                    "Inboard Engine Service",
                    "Inboard Engine Sales",
                    "Diesel Engine Service",
                    "Diesel Engine Sales",
                    "Generator Service",
                    "Generator Sales",
                    "Exhaust Systems & Service"
                ]
            },
            "Generator Sales or Service": {
                "request_a_pro": True,
                "specific_services": [
                    "Generator Installation",
                    "Routine Generator Maintenance",
                    "Electrical System Integration & Transfer Switches",
                    "Diagnostics & Repairs",
                    "Sound Shielding & Vibration Control",
                    "Generator Sales",
                    "Exhaust Systems & Service"
                ]
            },
            "Generator Sales": {
                "request_a_pro": True,
                "specific_services": [
                    "Cummins Onan",
                    "Kohler",
                    "Northern Lights",
                    "Caterpillar",
                    "Volvo Penta",
                    "NextGen",
                    "Phasor",
                    "Fischer Panda",
                    "Not Sure/Other"
                ]
            },
            "Generator Service": {
                "request_a_pro": True,
                "specific_services": [
                    "Generator Installation",
                    "Routine Generator Maintenance",
                    "Electrical System Integration & Transfer Switches",
                    "Diagnostics & Repairs",
                    "Sound Shielding & Vibration Control",
                    "Exhaust Systems & Service"
                ]
            },
            "Engine Service or Sales": {
                "request_a_pro": True,
                "specific_services": [
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
                ]
            },
            "Engine Service": {
                "request_a_pro": True,
                "specific_services": [
                    "Diesel Engine Maintenance",
                    "Outboard Engine Maintenance",
                    "Inboard Engine Maintenance",
                    "Diesel Engine Repair, Rebuild or Refit",
                    "Outboard Engine Repair, Rebuild or Refit",
                    "Inboard Engine Repair, Rebuild or Refit",
                    "Exhaust Systems & Service",
                    "Sound Shielding & Vibration Control"
                ]
            },
            "Engine Sales": {
                "request_a_pro": True,
                "specific_services": [
                    "Diesel Engine Sales",
                    "Inboard Engine Sales",
                    "Outboard Engine Sales",
                    "Electric Engine Sales"
                ]
            },
            "Diesel Engine Sales": {
                "request_a_pro": True,
                "specific_services": [
                    "Caterpillar",
                    "MAN Engines",
                    "MTU",
                    "Volvo Penta",
                    "Cummins Marine",
                    "Yanmar Marine",
                    "Perkins Marine",
                    "John Deer Marine"
                ]
            },
            "Outboard Engine Sales": {
                "request_a_pro": True,
                "specific_services": [
                    "Mercury",
                    "Yamaha",
                    "Suzuki",
                    "Honda",
                    "Seven Marine"
                ]
            },
            "Inboard Engine Sales": {
                "request_a_pro": True,
                "specific_services": [
                    "Caterpillar",
                    "MAN Engines",
                    "MTU",
                    "Volvo Penta",
                    "Cummins Marine",
                    "Yanmar Marine"
                ]
            },
            "Marine Exhaust Systems and Service": {
                "request_a_pro": True,
                "specific_services": [
                    "Marine Exhaust Fabrication",
                    "Exhaust System Repair & Overhaul",
                    "Exhaust Insulation & Lagging",
                    "Exhaust Filtration & Emissions Compliance",
                    "Exhaust Leak Detection & Corrosion Prevention"
                ]
            }
        }
    },
    "11": {
        "name": "Fuel Delivery",
        "subcategories": {
            "Fuel Delivery": {
                "request_a_pro": True,
                "specific_services": [
                    "Dyed Diesel Fuel (For Boats)",
                    "Regular Diesel Fuel (Landside Business)",
                    "Rec 90 (Ethanol Free Gas)"
                ]
            }
        }
    },
    "12": {
        "name": "Marine Systems",
        "subcategories": {
            "Marine Systems Install and Sales": {
                "request_a_pro": True,
                "specific_services": [
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
                ]
            },
            "Yacht Stabilizers and Seakeepers": {
                "request_a_pro": True,
                "specific_services": [
                    "New Seakeeper Install",
                    "Other Stabilizer Install",
                    "Stabilizer Maintenance",
                    "Stabilizer Retrofit or Upgrades"
                ]
            },
            "Instrument Panel and Dashboard": {
                "request_a_pro": True,
                "specific_services": [
                    "Electronic Dashboard Install or Upgrades",
                    "Instrument Panel Rewiring & Troubleshooting",
                    "Custom Dashboard Fabrication & Refacing",
                    "Gauge Replacement & Calibration",
                    "Backlighting & Switch Panel Modernization"
                ]
            },
            "Yacht AC Sales": {
                "request_a_pro": True,
                "specific_services": ["New AC Install or Replacement"]
            },
            "Yacht AC Service": {
                "request_a_pro": True,
                "specific_services": [
                    "New AC Install or Replacement",
                    "AC Maintenance & Servicing",
                    "Refrigerant Charging & Leak Repair",
                    "Pump & Water Flow Troubleshooting",
                    "Thermostat & Control Panel Upgrades"
                ]
            },
            "Boat Electrical Service": {
                "request_a_pro": True,
                "specific_services": [
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
            "Boat Sound Systems": {
                "request_a_pro": True,
                "specific_services": [
                    "Marine Audio System Install",
                    "Speaker & Subwoofer Upgrades",
                    "Amplifier Setup & Tuning",
                    "Multi-Zone Audio Configuration",
                    "Troubleshooting & System Repairs"
                ]
            },
            "Yacht Plumbing": {
                "request_a_pro": True,
                "specific_services": [
                    "Freshwater System Install or Repair",
                    "Marine Head & Toilet Systems",
                    "Greywater or Blackwater Tank Maintenance",
                    "Bilge Pump Install or Drainage",
                    "Watermaker (Desalinator) Service & Install"
                ]
            },
            "Boat Lighting": {
                "request_a_pro": True,
                "specific_services": [
                    "Navigation & Anchor Light Install",
                    "Underwater Lighting",
                    "Interior Cabin Lighting",
                    "Deck, Cockpit & Courtesy Lighting",
                    "Electrical Troubleshooting & Wiring"
                ]
            },
            "Yacht Refrigeration and Watermakers": {
                "request_a_pro": True,
                "specific_services": [
                    "Marine Refrigerator & Freezer Install",
                    "Refrigeration System Repairs & Troubleshooting",
                    "Watermaker (Desalinator) Install",
                    "Watermaker Maintenance & Servicing",
                    "Cold Plate & Evaporator Upgrades"
                ]
            },
            "Marine Batteries & Battery Installation": {
                "request_a_pro": True,
                "specific_services": [
                    "Marine Battery Sales",
                    "Marine Battery Installation",
                    "Battery Bank Design & Upgrades",
                    "Charging System Integration",
                    "Battery Testing & Maintenance"
                ]
            },
            "Yacht Mechanical Systems": {
                "request_a_pro": True,
                "specific_services": [
                    "Propulsion Systems",
                    "Steering & Rudder Systems",
                    "Hydraulic Systems",
                    "Fuel Systems",
                    "Bilge & Waste Systems"
                ]
            }
        }
    },
    "13": {
        "name": "Maritime Education and Training",
        "subcategories": {
            "Maritime Education and Training": {
                "request_a_pro": True,
                "specific_services": [
                    "Yacht, Sailboat or Catamaran On Water Training",
                    "Interested In Buying a Boat or Insurance Sign Off",
                    "Maritime Academy",
                    "Sailing Schools",
                    "Captains License"
                ]
            }
        }
    },
    "14": {
        "name": "Waterfront Property",
        "subcategories": {
            "Waterfront Homes For Sale": {
                "request_a_pro": True,
                "specific_services": [
                    "Buy a Waterfront Home or Condo",
                    "Sell a Waterfront Home or Condo",
                    "Buy a Waterfront New Development",
                    "Rent a Waterfront Property"
                ]
            },
            "Sell Your Waterfront Home": {
                "request_a_pro": True,
                "specific_services": [
                    "Buy a Waterfront Home or Condo",
                    "Sell a Waterfront Home or Condo",
                    "Buy a Waterfront New Development",
                    "Rent a Waterfront Property"
                ]
            },
            "Waterfront New Developments": {
                "request_a_pro": True,
                "specific_services": [
                    "Buy a Waterfront Home or Condo",
                    "Sell a Waterfront Home or Condo",
                    "Buy a Waterfront New Development",
                    "Rent a Waterfront Property"
                ]
            }
        }
    },
    "15": {
        "name": "Yacht Management",
        "subcategories": {
            "Yacht Management": {
                "request_a_pro": True,
                "specific_services": [
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
            }
        }
    },
    "16": {
        "name": "Wholesale or Dealer Product Pricing",
        "subcategories": {
            "Wholesale or Dealer Product Pricing": {
                "request_a_pro": True,
                "specific_services": [
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
    }
}

# Helper function to get all categories
def get_all_categories():
    """Return list of all primary category names"""
    return [cat_data["name"] for cat_data in DOCKSIDE_PROS_SERVICES.values()]

# Helper function to get subcategories for a category
def get_subcategories_for_category(category_name):
    """Return list of subcategories for a given category name"""
    for cat_data in DOCKSIDE_PROS_SERVICES.values():
        if cat_data["name"] == category_name:
            return list(cat_data["subcategories"].keys())
    return []

# Helper function to get specific services for a subcategory
def get_specific_services(category_name, subcategory_name):
    """Return list of specific services for a given category and subcategory"""
    for cat_data in DOCKSIDE_PROS_SERVICES.values():
        if cat_data["name"] == category_name:
            if subcategory_name in cat_data["subcategories"]:
                return cat_data["subcategories"][subcategory_name].get("specific_services", [])
    return []

# Helper function to validate service hierarchy
def validate_service_hierarchy(category, subcategory, specific_service=None):
    """Validate that the service hierarchy exists in the dictionary"""
    # Check if category exists
    category_found = False
    for cat_data in DOCKSIDE_PROS_SERVICES.values():
        if cat_data["name"] == category:
            category_found = True
            # Check if subcategory exists
            if subcategory not in cat_data["subcategories"]:
                return False, f"Subcategory '{subcategory}' not found in category '{category}'"
            
            # If specific service provided, check it exists
            if specific_service:
                services = cat_data["subcategories"][subcategory].get("specific_services", [])
                if specific_service not in services:
                    return False, f"Specific service '{specific_service}' not found in '{subcategory}'"
            
            return True, "Valid"
    
    if not category_found:
        return False, f"Category '{category}' not found"
    
    return False, "Unknown error"

# Export flattened lists for backward compatibility
def get_flattened_subcategories():
    """Get all subcategories as a flat list (for backward compatibility)"""
    subcategories = []
    for cat_data in DOCKSIDE_PROS_SERVICES.values():
        subcategories.extend(cat_data["subcategories"].keys())
    return list(set(subcategories))  # Remove duplicates

def get_flattened_specific_services():
    """Get all specific services as a flat list (for backward compatibility)"""
    services = []
    for cat_data in DOCKSIDE_PROS_SERVICES.values():
        for subcat_data in cat_data["subcategories"].values():
            services.extend(subcat_data.get("specific_services", []))
    return list(set(services))  # Remove duplicates

# Create mapping dictionaries for quick lookups
def build_service_mappings():
    """Build various mapping dictionaries for quick lookups"""
    mappings = {
        "subcategory_to_category": {},
        "specific_service_to_subcategory": {},
        "specific_service_to_category": {}
    }
    
    for cat_data in DOCKSIDE_PROS_SERVICES.values():
        category_name = cat_data["name"]
        
        for subcategory_name, subcat_data in cat_data["subcategories"].items():
            # Map subcategory to category
            mappings["subcategory_to_category"][subcategory_name] = category_name
            
            # Map specific services
            for service in subcat_data.get("specific_services", []):
                if service not in mappings["specific_service_to_subcategory"]:
                    mappings["specific_service_to_subcategory"][service] = []
                mappings["specific_service_to_subcategory"][service].append(subcategory_name)
                
                if service not in mappings["specific_service_to_category"]:
                    mappings["specific_service_to_category"][service] = []
                mappings["specific_service_to_category"][service].append(category_name)
    
    return mappings

# Initialize mappings on module load
SERVICE_MAPPINGS = build_service_mappings()

# Export key functions and data
__all__ = [
    'DOCKSIDE_PROS_SERVICES',
    'SERVICE_MAPPINGS',
    'get_all_categories',
    'get_subcategories_for_category',
    'get_specific_services',
    'validate_service_hierarchy',
    'get_flattened_subcategories',
    'get_flattened_specific_services'
]