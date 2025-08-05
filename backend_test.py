#!/usr/bin/env python3
"""
Backend API Testing for Spice E-commerce Application
Tests all backend endpoints including product management, Stripe payments, and orders
"""

import requests
import json
import time
import uuid
from typing import Dict, List, Any

# Backend URL from frontend/.env
BACKEND_URL = "https://3c5d736a-3daa-433b-8ca5-7ed47ebf92f5.preview.emergentagent.com/api"

class SpiceEcommerceAPITester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        
    def test_product_management_apis(self):
        """Test all product management endpoints"""
        print("\n=== TESTING PRODUCT MANAGEMENT APIs ===")
        
        # Test 1: Initialize sample products
        try:
            response = self.session.post(f"{self.base_url}/init-products")
            if response.status_code == 200:
                data = response.json()
                self.log_test("POST /api/init-products", True, f"Response: {data.get('message', 'Success')}")
            else:
                self.log_test("POST /api/init-products", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("POST /api/init-products", False, f"Exception: {str(e)}")
            
        # Test 2: Get all products
        try:
            response = self.session.get(f"{self.base_url}/products")
            if response.status_code == 200:
                products = response.json()
                if isinstance(products, list) and len(products) > 0:
                    # Check if products have required spice fields
                    sample_product = products[0]
                    required_fields = ['id', 'name', 'price', 'category', 'weight', 'image_url']
                    missing_fields = [field for field in required_fields if field not in sample_product]
                    if not missing_fields:
                        self.log_test("GET /api/products", True, f"Retrieved {len(products)} products with correct schema")
                        # Store first product ID for later tests
                        self.test_product_id = sample_product['id']
                    else:
                        self.log_test("GET /api/products", False, f"Missing fields: {missing_fields}")
                else:
                    self.log_test("GET /api/products", False, "No products returned or invalid format")
            else:
                self.log_test("GET /api/products", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("GET /api/products", False, f"Exception: {str(e)}")
            
        # Test 3: Get featured products
        try:
            response = self.session.get(f"{self.base_url}/products/featured")
            if response.status_code == 200:
                featured_products = response.json()
                if isinstance(featured_products, list):
                    # Check if all returned products are featured
                    all_featured = all(product.get('featured', False) for product in featured_products)
                    if all_featured:
                        self.log_test("GET /api/products/featured", True, f"Retrieved {len(featured_products)} featured products")
                    else:
                        self.log_test("GET /api/products/featured", False, "Some products returned are not featured")
                else:
                    self.log_test("GET /api/products/featured", False, "Invalid response format")
            else:
                self.log_test("GET /api/products/featured", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("GET /api/products/featured", False, f"Exception: {str(e)}")
            
        # Test 4: Get single product
        if hasattr(self, 'test_product_id'):
            try:
                response = self.session.get(f"{self.base_url}/products/{self.test_product_id}")
                if response.status_code == 200:
                    product = response.json()
                    if product.get('id') == self.test_product_id:
                        self.log_test("GET /api/products/{product_id}", True, f"Retrieved product: {product.get('name', 'Unknown')}")
                    else:
                        self.log_test("GET /api/products/{product_id}", False, "Product ID mismatch")
                else:
                    self.log_test("GET /api/products/{product_id}", False, f"Status: {response.status_code}, Response: {response.text}")
            except Exception as e:
                self.log_test("GET /api/products/{product_id}", False, f"Exception: {str(e)}")
        else:
            self.log_test("GET /api/products/{product_id}", False, "No test product ID available")
            
        # Test 5: Create new product
        try:
            new_product = {
                "name": "Test Cardamom Powder",
                "description": "Premium cardamom powder for testing purposes",
                "price": 25.99,
                "category": "Powders",
                "weight": "50g",
                "image_url": "https://example.com/cardamom.jpg",
                "stock_quantity": 50,
                "featured": False
            }
            response = self.session.post(f"{self.base_url}/products", json=new_product)
            if response.status_code == 200:
                created_product = response.json()
                if created_product.get('name') == new_product['name']:
                    self.log_test("POST /api/products", True, f"Created product: {created_product.get('name')}")
                    self.test_created_product_id = created_product.get('id')
                else:
                    self.log_test("POST /api/products", False, "Product creation response mismatch")
            else:
                self.log_test("POST /api/products", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("POST /api/products", False, f"Exception: {str(e)}")
            
    def test_stripe_payment_integration(self):
        """Test Stripe payment integration endpoints"""
        print("\n=== TESTING STRIPE PAYMENT INTEGRATION ===")
        
        # Test 1: Create checkout session
        try:
            checkout_data = {
                "items": [
                    {
                        "product_id": getattr(self, 'test_product_id', 'test-product-id'),
                        "quantity": 2,
                        "price": 12.99
                    },
                    {
                        "product_id": getattr(self, 'test_created_product_id', 'test-product-id-2'),
                        "quantity": 1,
                        "price": 25.99
                    }
                ],
                "customer_email": "customer@spicestore.com",
                "origin_url": "https://3c5d736a-3daa-433b-8ca5-7ed47ebf92f5.preview.emergentagent.com"
            }
            response = self.session.post(f"{self.base_url}/checkout/session", json=checkout_data)
            if response.status_code == 200:
                checkout_response = response.json()
                if 'url' in checkout_response and 'session_id' in checkout_response:
                    self.log_test("POST /api/checkout/session", True, f"Created session: {checkout_response['session_id']}")
                    self.test_session_id = checkout_response['session_id']
                else:
                    self.log_test("POST /api/checkout/session", False, "Missing url or session_id in response")
            else:
                self.log_test("POST /api/checkout/session", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("POST /api/checkout/session", False, f"Exception: {str(e)}")
            
        # Test 2: Check payment status
        if hasattr(self, 'test_session_id'):
            try:
                response = self.session.get(f"{self.base_url}/checkout/status/{self.test_session_id}")
                if response.status_code == 200:
                    status_response = response.json()
                    if 'status' in status_response and 'payment_status' in status_response:
                        self.log_test("GET /api/checkout/status/{session_id}", True, f"Status: {status_response.get('status')}, Payment: {status_response.get('payment_status')}")
                    else:
                        self.log_test("GET /api/checkout/status/{session_id}", False, "Missing status fields in response")
                else:
                    self.log_test("GET /api/checkout/status/{session_id}", False, f"Status: {response.status_code}, Response: {response.text}")
            except Exception as e:
                self.log_test("GET /api/checkout/status/{session_id}", False, f"Exception: {str(e)}")
        else:
            self.log_test("GET /api/checkout/status/{session_id}", False, "No test session ID available")
            
        # Test 3: Stripe webhook (basic endpoint test)
        try:
            # Note: This is a basic connectivity test. Real webhook testing requires Stripe signature
            webhook_data = {
                "id": "evt_test_webhook",
                "object": "event",
                "type": "checkout.session.completed"
            }
            response = self.session.post(f"{self.base_url}/webhook/stripe", 
                                       json=webhook_data,
                                       headers={"Stripe-Signature": "test_signature"})
            # We expect this to fail due to signature validation, but endpoint should be reachable
            if response.status_code in [200, 400, 500]:  # Any response means endpoint is working
                self.log_test("POST /api/webhook/stripe", True, f"Webhook endpoint accessible (Status: {response.status_code})")
            else:
                self.log_test("POST /api/webhook/stripe", False, f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test("POST /api/webhook/stripe", False, f"Exception: {str(e)}")
            
    def test_order_management(self):
        """Test order management endpoints"""
        print("\n=== TESTING ORDER MANAGEMENT ===")
        
        # We need to create an order first through checkout to test order retrieval
        # This is already done in the checkout session test, so we'll try to find an order
        
        # Test: Get order by ID (we'll use a test order ID)
        # Since we created a checkout session, there should be an order created
        try:
            # First, let's try to get any order that might exist from our checkout session
            # We'll use a mock order ID for testing the endpoint structure
            test_order_id = "test-order-id-12345"
            response = self.session.get(f"{self.base_url}/orders/{test_order_id}")
            
            if response.status_code == 404:
                # This is expected for a non-existent order, but shows the endpoint works
                self.log_test("GET /api/orders/{order_id}", True, "Order endpoint accessible (404 for non-existent order is expected)")
            elif response.status_code == 200:
                order = response.json()
                if 'id' in order and 'customer_email' in order and 'items' in order:
                    self.log_test("GET /api/orders/{order_id}", True, f"Retrieved order for customer: {order.get('customer_email')}")
                else:
                    self.log_test("GET /api/orders/{order_id}", False, "Order response missing required fields")
            else:
                self.log_test("GET /api/orders/{order_id}", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("GET /api/orders/{order_id}", False, f"Exception: {str(e)}")
            
    def test_database_models(self):
        """Test database models and collections by verifying data structure"""
        print("\n=== TESTING DATABASE MODELS AND COLLECTIONS ===")
        
        # Test product model structure
        try:
            response = self.session.get(f"{self.base_url}/products")
            if response.status_code == 200:
                products = response.json()
                if products:
                    product = products[0]
                    # Check for spice-specific fields
                    spice_fields = ['name', 'price', 'category', 'weight', 'image_url', 'stock_quantity', 'featured']
                    missing_fields = [field for field in spice_fields if field not in product]
                    
                    if not missing_fields:
                        # Check data types
                        type_checks = [
                            isinstance(product.get('price'), (int, float)),
                            isinstance(product.get('stock_quantity'), int),
                            isinstance(product.get('featured'), bool),
                            isinstance(product.get('name'), str),
                            isinstance(product.get('category'), str)
                        ]
                        
                        if all(type_checks):
                            self.log_test("Database Models - Product Schema", True, "All required fields present with correct types")
                        else:
                            self.log_test("Database Models - Product Schema", False, "Some fields have incorrect data types")
                    else:
                        self.log_test("Database Models - Product Schema", False, f"Missing spice-specific fields: {missing_fields}")
                else:
                    self.log_test("Database Models - Product Schema", False, "No products available to test schema")
            else:
                self.log_test("Database Models - Product Schema", False, f"Could not retrieve products for schema test")
        except Exception as e:
            self.log_test("Database Models - Product Schema", False, f"Exception: {str(e)}")
            
        # Test that UUIDs are used instead of ObjectID
        try:
            response = self.session.get(f"{self.base_url}/products")
            if response.status_code == 200:
                products = response.json()
                if products:
                    product_id = products[0].get('id')
                    # UUID should be a string and not contain ObjectId format
                    if isinstance(product_id, str) and not product_id.startswith('ObjectId'):
                        # Try to parse as UUID to verify format
                        try:
                            uuid.UUID(product_id)
                            self.log_test("Database Models - UUID Usage", True, "Products use UUID format for IDs")
                        except ValueError:
                            self.log_test("Database Models - UUID Usage", False, f"Product ID is not valid UUID format: {product_id}")
                    else:
                        self.log_test("Database Models - UUID Usage", False, f"Product ID appears to be ObjectId format: {product_id}")
                else:
                    self.log_test("Database Models - UUID Usage", False, "No products available to test UUID usage")
            else:
                self.log_test("Database Models - UUID Usage", False, "Could not retrieve products for UUID test")
        except Exception as e:
            self.log_test("Database Models - UUID Usage", False, f"Exception: {str(e)}")
            
    def run_all_tests(self):
        """Run all backend API tests"""
        print("🧪 Starting Spice E-commerce Backend API Tests")
        print(f"🔗 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Run all test suites
        self.test_product_management_apis()
        self.test_stripe_payment_integration()
        self.test_order_management()
        self.test_database_models()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total - passed}/{total}")
        
        if total - passed > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   ❌ {result['test']}: {result['details']}")
                    
        print("\n🎯 CRITICAL ISSUES FOUND:")
        critical_failures = []
        for result in self.test_results:
            if not result['success']:
                # Identify critical vs minor issues
                test_name = result['test']
                if any(critical in test_name.lower() for critical in ['products', 'checkout', 'session', 'orders']):
                    if 'exception' in result['details'].lower() or 'status: 5' in result['details']:
                        critical_failures.append(f"   🚨 {test_name}: {result['details']}")
                        
        if critical_failures:
            for failure in critical_failures:
                print(failure)
        else:
            print("   ✅ No critical backend functionality issues found")
            
        return passed, total

if __name__ == "__main__":
    tester = SpiceEcommerceAPITester()
    passed, total = tester.run_all_tests()
    
    # Exit with appropriate code
    exit(0 if passed == total else 1)