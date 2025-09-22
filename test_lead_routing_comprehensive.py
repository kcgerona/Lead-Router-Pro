#!/usr/bin/env python3
"""
Comprehensive Lead Routing Test Script
Tests vendor matching, pool creation, and assignment algorithms
"""

import json
import logging
import sys
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import random

# Add parent directory to path
sys.path.insert(0, '/root/Lead-Router-Pro')

from api.services.lead_routing_service import lead_routing_service
from api.services.service_categories import SERVICE_CATEGORIES, LEVEL_3_SERVICES
from database.simple_connection import db as simple_db_instance

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LeadRoutingTester:
    """Comprehensive testing for lead routing logic"""
    
    def __init__(self):
        self.account_id = "test_location_001"
        self.test_results = []
        
    def setup_test_data(self):
        """Create test vendors with various service configurations"""
        logger.info("\n" + "="*80)
        logger.info("SETTING UP TEST DATA")
        logger.info("="*80)
        
        conn = sqlite3.connect('smart_lead_router.db')
        cursor = conn.cursor()
        
        # Clean up existing test vendors
        cursor.execute("DELETE FROM vendors WHERE account_id = ?", (self.account_id,))
        
        # Test Vendor 1: Level 3 Services (AC specialist)
        vendor1 = {
            'id': 'test_vendor_001',
            'account_id': self.account_id,
            'name': 'Marine AC Specialists',
            'company_name': 'Marine AC Specialists LLC',
            'email': 'ac@marine.com',
            'status': 'active',
            'taking_new_work': True,
            'services_offered': json.dumps(['AC Service', 'AC Installation', 'AC Repair']),  # Level 3 services
            'coverage_type': 'state',
            'coverage_states': json.dumps(['Florida']),
            'coverage_counties': json.dumps([]),  # Empty for state coverage
            'lead_close_percentage': 75.0,
            'last_lead_assigned': (datetime.now() - timedelta(days=3)).isoformat()
        }
        
        # Test Vendor 2: Level 2 Category (General maintenance)
        vendor2 = {
            'id': 'test_vendor_002',
            'account_id': self.account_id,
            'name': 'Complete Marine Services',
            'company_name': 'Complete Marine Services Inc',
            'email': 'complete@marine.com',
            'status': 'active',
            'taking_new_work': True,
            'services_offered': json.dumps(['Boat Maintenance', 'Yacht Maintenance']),  # Level 2 categories
            'coverage_type': 'county',
            'coverage_states': json.dumps([]),  # Empty for county coverage
            'coverage_counties': json.dumps(['Broward County, Florida', 'Miami-Dade County, Florida']),
            'lead_close_percentage': 60.0,
            'last_lead_assigned': (datetime.now() - timedelta(days=1)).isoformat()
        }
        
        # Test Vendor 3: Mixed Level 2 and Level 3
        vendor3 = {
            'id': 'test_vendor_003',
            'account_id': self.account_id,
            'name': 'Premium Yacht Services',
            'company_name': 'Premium Yacht Services',
            'email': 'premium@yacht.com',
            'status': 'active',
            'taking_new_work': True,
            'services_offered': json.dumps(['Yacht Maintenance', 'AC Service', 'Generator Service']),  # Mixed
            'coverage_type': 'national',
            'coverage_states': json.dumps([]),  # National = all states
            'coverage_counties': json.dumps([]),  # Empty for national coverage
            'lead_close_percentage': 85.0,
            'last_lead_assigned': (datetime.now() - timedelta(days=7)).isoformat()
        }
        
        # Test Vendor 4: Inactive vendor (should not be matched)
        vendor4 = {
            'id': 'test_vendor_004',
            'account_id': self.account_id,
            'name': 'Inactive Marine',
            'company_name': 'Inactive Marine Co',
            'email': 'inactive@marine.com',
            'status': 'inactive',  # INACTIVE
            'taking_new_work': True,
            'services_offered': json.dumps(['AC Service', 'Boat Maintenance']),
            'coverage_type': 'state',
            'coverage_states': json.dumps(['Florida']),
            'coverage_counties': json.dumps([]),  # Empty for state coverage
            'lead_close_percentage': 50.0,
            'last_lead_assigned': None
        }
        
        # Test Vendor 5: Not taking new work (should not be matched)
        vendor5 = {
            'id': 'test_vendor_005',
            'account_id': self.account_id,
            'name': 'Busy Marine Services',
            'company_name': 'Busy Marine Services',
            'email': 'busy@marine.com',
            'status': 'active',
            'taking_new_work': False,  # NOT TAKING WORK
            'services_offered': json.dumps(['AC Service', 'Generator Service']),
            'coverage_type': 'county',
            'coverage_states': json.dumps([]),  # Empty for county coverage
            'coverage_counties': json.dumps(['Broward County, Florida']),
            'lead_close_percentage': 90.0,
            'last_lead_assigned': None
        }
        
        # Test Vendor 6: Global coverage
        vendor6 = {
            'id': 'test_vendor_006',
            'account_id': self.account_id,
            'name': 'Global Marine Network',
            'company_name': 'Global Marine Network',
            'email': 'global@marine.com',
            'status': 'active',
            'taking_new_work': True,
            'services_offered': json.dumps(['Boat Transport', 'Yacht Delivery']),
            'coverage_type': 'global',  # GLOBAL COVERAGE
            'coverage_states': json.dumps([]),
            'coverage_counties': json.dumps([]),
            'lead_close_percentage': 65.0,
            'last_lead_assigned': (datetime.now() - timedelta(days=2)).isoformat()
        }
        
        # Insert all test vendors
        vendors = [vendor1, vendor2, vendor3, vendor4, vendor5, vendor6]
        
        for vendor in vendors:
            cursor.execute("""
                INSERT INTO vendors (
                    id, account_id, name, company_name, email, status, taking_new_work,
                    services_offered, coverage_type, coverage_states, coverage_counties,
                    lead_close_percentage, last_lead_assigned, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                vendor['id'], vendor['account_id'], vendor['name'], vendor['company_name'],
                vendor['email'], vendor['status'], vendor['taking_new_work'],
                vendor['services_offered'], vendor['coverage_type'], 
                vendor['coverage_states'], vendor['coverage_counties'],
                vendor['lead_close_percentage'], vendor['last_lead_assigned']
            ))
            
            status = "✅ ACTIVE" if vendor['status'] == 'active' else "❌ INACTIVE"
            taking = "✅ YES" if vendor['taking_new_work'] else "❌ NO"
            logger.info(f"Created vendor: {vendor['name']} - Status: {status}, Taking Work: {taking}")
            logger.info(f"  Services: {vendor['services_offered']}")
            logger.info(f"  Coverage: {vendor['coverage_type']} - {vendor.get('coverage_states', vendor.get('coverage_counties', 'N/A'))}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"\n✅ Created {len(vendors)} test vendors")
        
    def test_service_matching(self):
        """Test various service matching scenarios"""
        logger.info("\n" + "="*80)
        logger.info("TEST 1: SERVICE MATCHING")
        logger.info("="*80)
        
        test_cases = [
            # Test Case 1: Level 3 specific service (AC Service)
            {
                'name': 'Level 3 AC Service Request',
                'service': 'AC Service',
                'zip': '33301',  # Fort Lauderdale, FL (Broward County)
                'expected_vendors': ['Marine AC Specialists', 'Premium Yacht Services'],
                'excluded_vendors': ['Complete Marine Services']  # Has only Level 2 categories
            },
            
            # Test Case 2: Level 2 category (Boat Maintenance)
            {
                'name': 'Level 2 Boat Maintenance Request',
                'service': 'Boat Maintenance',
                'zip': '33139',  # Miami Beach, FL (Miami-Dade County)
                'expected_vendors': ['Complete Marine Services'],  # Only vendor with this category and coverage
                'excluded_vendors': ['Marine AC Specialists', 'Premium Yacht Services']  # Have specific Level 3 services
            },
            
            # Test Case 3: Service with global coverage vendor
            {
                'name': 'Boat Transport (Global Coverage)',
                'service': 'Boat Transport',
                'zip': '90210',  # Beverly Hills, CA
                'expected_vendors': ['Global Marine Network'],  # Global coverage
                'excluded_vendors': ['Marine AC Specialists', 'Complete Marine Services', 'Premium Yacht Services']
            },
            
            # Test Case 4: Multiple vendors for same service
            {
                'name': 'AC Service with Multiple Vendors',
                'service': 'AC Service',
                'zip': '33316',  # Fort Lauderdale, FL (Broward County)
                'expected_vendors': ['Marine AC Specialists', 'Premium Yacht Services'],
                'excluded_vendors': ['Complete Marine Services', 'Global Marine Network']
            }
        ]
        
        for test_case in test_cases:
            logger.info(f"\n🧪 Testing: {test_case['name']}")
            logger.info(f"  Service: '{test_case['service']}'")
            logger.info(f"  ZIP: {test_case['zip']}")
            
            # Find matching vendors
            matching_vendors = lead_routing_service.find_matching_vendors(
                account_id=self.account_id,
                service_category=test_case['service'],
                zip_code=test_case['zip'],
                priority='normal',
                specific_service=test_case['service']
            )
            
            # Extract vendor names
            matched_names = [v.get('company_name', v.get('name')) for v in matching_vendors]
            
            logger.info(f"  Found {len(matching_vendors)} matching vendors: {matched_names}")
            
            # Verify expected vendors are included
            test_passed = True
            for expected in test_case['expected_vendors']:
                if expected in matched_names:
                    logger.info(f"  ✅ Expected vendor '{expected}' found")
                else:
                    logger.error(f"  ❌ Expected vendor '{expected}' NOT found")
                    test_passed = False
            
            # Verify excluded vendors are NOT included
            for excluded in test_case['excluded_vendors']:
                if excluded not in matched_names:
                    logger.info(f"  ✅ Excluded vendor '{excluded}' correctly not matched")
                else:
                    logger.error(f"  ❌ Excluded vendor '{excluded}' incorrectly matched")
                    test_passed = False
            
            # Check inactive/busy vendors are excluded
            if 'Inactive Marine' in matched_names:
                logger.error(f"  ❌ Inactive vendor incorrectly included")
                test_passed = False
            else:
                logger.info(f"  ✅ Inactive vendors correctly excluded")
            
            if 'Busy Marine Services' in matched_names:
                logger.error(f"  ❌ Vendor not taking work incorrectly included")
                test_passed = False
            else:
                logger.info(f"  ✅ Vendors not taking work correctly excluded")
            
            self.test_results.append({
                'test': test_case['name'],
                'passed': test_passed,
                'vendor_count': len(matching_vendors)
            })
    
    def test_vendor_pool_completeness(self):
        """Verify all qualified vendors are included in the pool"""
        logger.info("\n" + "="*80)
        logger.info("TEST 2: VENDOR POOL COMPLETENESS")
        logger.info("="*80)
        
        # Test that ALL qualified vendors make it into the pool
        service = 'AC Service'
        zip_code = '33301'  # Broward County, FL
        
        logger.info(f"🔍 Testing pool completeness for '{service}' in ZIP {zip_code}")
        
        # Get the vendor pool
        vendor_pool = lead_routing_service.find_matching_vendors(
            account_id=self.account_id,
            service_category=service,
            zip_code=zip_code,
            priority='normal',
            specific_service=service
        )
        
        # Manually verify expected vendors
        expected_in_pool = {
            'Marine AC Specialists': 'State coverage (Florida)',
            'Premium Yacht Services': 'National coverage'
        }
        
        logger.info(f"\n📊 Vendor Pool Analysis:")
        logger.info(f"  Total vendors in pool: {len(vendor_pool)}")
        
        for vendor in vendor_pool:
            name = vendor.get('company_name', vendor.get('name'))
            coverage_reason = vendor.get('coverage_match_reason', 'Unknown')
            logger.info(f"  • {name}: {coverage_reason}")
            
            if name in expected_in_pool:
                logger.info(f"    ✅ Expected vendor confirmed in pool")
                del expected_in_pool[name]
        
        # Check if any expected vendors are missing
        if expected_in_pool:
            logger.error(f"\n❌ Missing vendors from pool:")
            for name, reason in expected_in_pool.items():
                logger.error(f"  • {name} ({reason})")
            test_passed = False
        else:
            logger.info(f"\n✅ All expected vendors are in the qualified pool")
            test_passed = True
        
        self.test_results.append({
            'test': 'Vendor Pool Completeness',
            'passed': test_passed,
            'vendor_count': len(vendor_pool)
        })
    
    def test_round_robin_assignment(self):
        """Test round-robin assignment algorithm"""
        logger.info("\n" + "="*80)
        logger.info("TEST 3: ROUND-ROBIN ASSIGNMENT")
        logger.info("="*80)
        
        # Set routing to 100% round-robin
        lead_routing_service.update_routing_configuration(self.account_id, performance_percentage=0)
        
        # Get a pool of vendors
        vendor_pool = lead_routing_service.find_matching_vendors(
            account_id=self.account_id,
            service_category='AC Service',
            zip_code='33301',
            priority='normal',
            specific_service='AC Service'
        )
        
        if len(vendor_pool) < 2:
            logger.warning("⚠️ Need at least 2 vendors for round-robin test")
            return
        
        logger.info(f"🔄 Testing round-robin with {len(vendor_pool)} vendors")
        
        # Track assignments
        assignments = []
        
        # Make multiple assignments
        for i in range(6):
            selected = lead_routing_service.select_vendor_from_pool(vendor_pool, self.account_id)
            if selected:
                name = selected.get('company_name', selected.get('name'))
                last_assigned = selected.get('last_lead_assigned', 'Never')
                logger.info(f"  Assignment {i+1}: {name} (last assigned: {last_assigned})")
                assignments.append(name)
                
                # Update the vendor pool to reflect the new assignment time
                # In real scenario, this would be updated in the database
                for v in vendor_pool:
                    if v['id'] == selected['id']:
                        v['last_lead_assigned'] = datetime.now().isoformat()
        
        # Verify round-robin pattern
        unique_vendors = list(set(assignments))
        logger.info(f"\n📊 Round-Robin Results:")
        logger.info(f"  Total assignments: {len(assignments)}")
        logger.info(f"  Unique vendors used: {len(unique_vendors)}")
        logger.info(f"  Assignment pattern: {assignments}")
        
        # Check if vendors are being rotated
        test_passed = len(unique_vendors) > 1
        if test_passed:
            logger.info(f"  ✅ Round-robin is rotating between vendors")
        else:
            logger.error(f"  ❌ Round-robin not working - same vendor selected repeatedly")
        
        self.test_results.append({
            'test': 'Round-Robin Assignment',
            'passed': test_passed,
            'assignments': len(assignments)
        })
    
    def test_performance_based_assignment(self):
        """Test performance-based assignment algorithm"""
        logger.info("\n" + "="*80)
        logger.info("TEST 4: PERFORMANCE-BASED ASSIGNMENT")
        logger.info("="*80)
        
        # Set routing to 100% performance-based
        lead_routing_service.update_routing_configuration(self.account_id, performance_percentage=100)
        
        # Get a pool of vendors
        vendor_pool = lead_routing_service.find_matching_vendors(
            account_id=self.account_id,
            service_category='AC Service',
            zip_code='33301',
            priority='normal',
            specific_service='AC Service'
        )
        
        if len(vendor_pool) < 2:
            logger.warning("⚠️ Need at least 2 vendors for performance test")
            return
        
        logger.info(f"🏆 Testing performance-based routing with {len(vendor_pool)} vendors")
        
        # Display vendor close rates
        logger.info(f"\n📊 Vendor Performance Metrics:")
        for vendor in vendor_pool:
            name = vendor.get('company_name', vendor.get('name'))
            close_rate = vendor.get('lead_close_percentage', 0)
            logger.info(f"  • {name}: {close_rate}% close rate")
        
        # Track assignments
        assignments = []
        
        # Make multiple assignments
        for i in range(6):
            selected = lead_routing_service.select_vendor_from_pool(vendor_pool, self.account_id)
            if selected:
                name = selected.get('company_name', selected.get('name'))
                close_rate = selected.get('lead_close_percentage', 0)
                logger.info(f"  Assignment {i+1}: {name} ({close_rate}% close rate)")
                assignments.append((name, close_rate))
        
        # Verify performance-based pattern (highest performer should get most leads)
        if assignments:
            # Count assignments per vendor
            vendor_counts = {}
            for name, rate in assignments:
                vendor_counts[name] = vendor_counts.get(name, 0) + 1
            
            # Find vendor with most assignments
            top_vendor = max(vendor_counts, key=vendor_counts.get)
            top_count = vendor_counts[top_vendor]
            
            # Get the close rate of the top vendor
            top_vendor_rate = next((rate for name, rate in assignments if name == top_vendor), 0)
            
            logger.info(f"\n📊 Performance-Based Results:")
            logger.info(f"  Most assignments: {top_vendor} ({top_count} leads)")
            logger.info(f"  Their close rate: {top_vendor_rate}%")
            
            # Verify the vendor with most assignments has high close rate
            test_passed = top_vendor_rate >= 75  # Should be Premium Yacht Services (85%)
            
            if test_passed:
                logger.info(f"  ✅ High-performing vendor correctly prioritized")
            else:
                logger.error(f"  ❌ Performance-based routing not working correctly")
        else:
            test_passed = False
            logger.error(f"  ❌ No assignments made")
        
        self.test_results.append({
            'test': 'Performance-Based Assignment',
            'passed': test_passed,
            'assignments': len(assignments)
        })
    
    def test_mixed_routing(self):
        """Test mixed routing (50/50 round-robin and performance)"""
        logger.info("\n" + "="*80)
        logger.info("TEST 5: MIXED ROUTING (50/50)")
        logger.info("="*80)
        
        # Set routing to 50% performance, 50% round-robin
        lead_routing_service.update_routing_configuration(self.account_id, performance_percentage=50)
        
        # Get a pool of vendors
        vendor_pool = lead_routing_service.find_matching_vendors(
            account_id=self.account_id,
            service_category='AC Service',
            zip_code='33301',
            priority='normal',
            specific_service='AC Service'
        )
        
        logger.info(f"🔀 Testing 50/50 mixed routing with {len(vendor_pool)} vendors")
        
        # Track assignments and routing methods
        assignments = []
        routing_methods = {'performance': 0, 'round_robin': 0}
        
        # Make many assignments to see distribution
        for i in range(20):
            # To track which method is used, we'll check logs
            selected = lead_routing_service.select_vendor_from_pool(vendor_pool, self.account_id)
            if selected:
                name = selected.get('company_name', selected.get('name'))
                assignments.append(name)
        
        logger.info(f"\n📊 Mixed Routing Results:")
        logger.info(f"  Total assignments: {len(assignments)}")
        
        # Count unique vendors
        vendor_counts = {}
        for name in assignments:
            vendor_counts[name] = vendor_counts.get(name, 0) + 1
        
        logger.info(f"  Distribution:")
        for vendor, count in vendor_counts.items():
            percentage = (count / len(assignments)) * 100
            logger.info(f"    • {vendor}: {count} assignments ({percentage:.1f}%)")
        
        test_passed = len(vendor_counts) > 1  # Should use multiple vendors
        
        if test_passed:
            logger.info(f"  ✅ Mixed routing using multiple vendors")
        else:
            logger.error(f"  ❌ Mixed routing not distributing properly")
        
        self.test_results.append({
            'test': 'Mixed Routing (50/50)',
            'passed': test_passed,
            'assignments': len(assignments)
        })
    
    def test_coverage_types(self):
        """Test different coverage types (global, national, state, county)"""
        logger.info("\n" + "="*80)
        logger.info("TEST 6: COVERAGE TYPES")
        logger.info("="*80)
        
        test_cases = [
            {
                'name': 'Global Coverage Test',
                'service': 'Boat Transport',
                'zips': ['33301', '90210', '10001'],  # FL, CA, NY
                'expected_vendor': 'Global Marine Network'
            },
            {
                'name': 'National Coverage Test',
                'service': 'Generator Service',
                'zips': ['33301', '90210', '10001'],  # FL, CA, NY
                'expected_vendor': 'Premium Yacht Services'  # Has national coverage
            },
            {
                'name': 'State Coverage Test',
                'service': 'AC Service',
                'zips': ['33301', '33139', '32801'],  # All Florida
                'expected_vendor': 'Marine AC Specialists'  # State coverage for FL
            },
            {
                'name': 'County Coverage Test',
                'service': 'Boat Maintenance',
                'zips': ['33301', '33139'],  # Broward and Miami-Dade
                'expected_vendor': 'Complete Marine Services'
            }
        ]
        
        for test_case in test_cases:
            logger.info(f"\n🌍 {test_case['name']}")
            logger.info(f"  Service: {test_case['service']}")
            
            all_matched = True
            for zip_code in test_case['zips']:
                vendors = lead_routing_service.find_matching_vendors(
                    account_id=self.account_id,
                    service_category=test_case['service'],
                    zip_code=zip_code,
                    priority='normal',
                    specific_service=test_case['service']
                )
                
                vendor_names = [v.get('company_name', v.get('name')) for v in vendors]
                
                if test_case['expected_vendor'] in vendor_names:
                    logger.info(f"  ✅ ZIP {zip_code}: Found {test_case['expected_vendor']}")
                else:
                    logger.error(f"  ❌ ZIP {zip_code}: Did NOT find {test_case['expected_vendor']}")
                    logger.info(f"     Found instead: {vendor_names}")
                    all_matched = False
            
            self.test_results.append({
                'test': test_case['name'],
                'passed': all_matched,
                'zips_tested': len(test_case['zips'])
            })
    
    def print_summary(self):
        """Print test summary"""
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        
        passed = sum(1 for r in self.test_results if r['passed'])
        failed = len(self.test_results) - passed
        
        logger.info(f"\n📊 Results: {passed} PASSED, {failed} FAILED out of {len(self.test_results)} tests")
        
        logger.info("\nDetailed Results:")
        for result in self.test_results:
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            logger.info(f"  {status}: {result['test']}")
            if 'vendor_count' in result:
                logger.info(f"         Vendors: {result['vendor_count']}")
            if 'assignments' in result:
                logger.info(f"         Assignments: {result['assignments']}")
        
        # Overall verdict
        if failed == 0:
            logger.info("\n🎉 ALL TESTS PASSED! Lead routing is working correctly.")
        else:
            logger.error(f"\n⚠️ {failed} TEST(S) FAILED! Lead routing needs attention.")
        
        return passed, failed
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        try:
            self.setup_test_data()
            self.test_service_matching()
            self.test_vendor_pool_completeness()
            self.test_round_robin_assignment()
            self.test_performance_based_assignment()
            self.test_mixed_routing()
            self.test_coverage_types()
            passed, failed = self.print_summary()
            
            return passed, failed
            
        except Exception as e:
            logger.error(f"❌ Test execution failed: {e}")
            import traceback
            traceback.print_exc()
            return 0, 1

def main():
    """Main test execution"""
    logger.info("🚀 Starting Comprehensive Lead Routing Tests")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    tester = LeadRoutingTester()
    passed, failed = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()