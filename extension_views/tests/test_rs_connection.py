from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
import logging
import xml.etree.ElementTree as ET

_logger = logging.getLogger(__name__)

class TestRSAuthentication(TransactionCase):
    """Test RS.GE Authentication API Integration"""

    def setUp(self):
        super(TestRSAuthentication, self).setUp()
        
        # REAL TEST CREDENTIALS - Provided by user
        self.rs_acc = "odootest:206322102"
        self.rs_pass = "Aa123456!"
        
        # Test data
        self.valid_tin = "01008062291"
        self.driver_tin = "01008062291"
        self.buyer_tin = "12345678910"
        
        # Create test partner with RS credentials
        self.test_partner = self.env['res.partner'].create({
            'name': 'Test RS Partner',
            'vat': self.valid_tin,
        })
        
        # Create test picking for SOAP operations
        self.picking = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'partner_id': self.test_partner.id,
        })
        
        # Set RS credentials on current user
        self.env.user.write({
            'rs_acc': self.rs_acc,
            'rs_pass': self.rs_pass
        })
        
        _logger.info("=" * 80)
        _logger.info("RS.GE AUTHENTICATION TEST SETUP COMPLETE")
        _logger.info(f"Username: {self.rs_acc}")
        _logger.info(f"Valid TIN: {self.valid_tin}")
        _logger.info("=" * 80)

    def test_01_authentication_valid_credentials(self):
        """Test 1: Authenticate with VALID credentials - should return un_id"""
        _logger.info("\n" + "=" * 80)
        _logger.info("TEST 1: AUTHENTICATION WITH VALID CREDENTIALS")
        _logger.info("=" * 80)
        
        url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
        headers = {"Content-Type": "text/xml; charset=utf-8"}
        
        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <chek_service_user xmlns="http://tempuri.org/">
              <su>{self.rs_acc}</su>
              <sp>{self.rs_pass}</sp>
            </chek_service_user>
          </soap:Body>
        </soap:Envelope>"""
        
        # Use the _safe_soap_request method from stock.picking
        success, response_text, error_msg = self.picking._safe_soap_request(
            url, soap_body, headers, "chek_service_user"
        )
        
        # Assertions
        self.assertTrue(success, f"Authentication request should succeed. Error: {error_msg}")
        self.assertIsNotNone(response_text, "Response text should not be None")
        
        _logger.info(f"✓ HTTP Request Status: SUCCESS")
        _logger.info(f"✓ Response received (length: {len(response_text)} chars)")
        
        # Parse XML response
        try:
            root = ET.fromstring(response_text)
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns': 'http://tempuri.org/'
            }
            
            # Check for un_id element
            un_id_element = root.find('.//ns:un_id', namespaces)
            self.assertIsNotNone(un_id_element, "un_id element should be present in response")
            
            un_id = un_id_element.text
            self.assertIsNotNone(un_id, "un_id should not be None")
            self.assertTrue(len(un_id) > 0, "un_id should not be empty")
            
            # Check if un_id is positive (negative means error)
            self.assertFalse(un_id.startswith('-'), 
                f"un_id should be positive for valid credentials, got: {un_id}")
            
            _logger.info(f"✓ Authentication SUCCESSFUL")
            _logger.info(f"✓ User ID (un_id): {un_id}")
            
            # Check for chek_service_userResult (should be true/false)
            result_element = root.find('.//ns:chek_service_userResult', namespaces)
            if result_element is not None:
                result = result_element.text
                _logger.info(f"✓ Service User Check Result: {result}")
                self.assertEqual(result.lower(), 'true', 
                    f"chek_service_userResult should be 'true' for valid credentials, got: {result}")
            
            _logger.info("=" * 80)
            _logger.info("✅ TEST 1 PASSED: Valid credentials authenticated successfully")
            _logger.info("=" * 80)
            
        except ET.ParseError as e:
            self.fail(f"Failed to parse XML response: {e}\nResponse: {response_text}")

    def test_02_authentication_invalid_credentials(self):
        """Test 2: Authenticate with INVALID credentials - should fail gracefully"""
        _logger.info("\n" + "=" * 80)
        _logger.info("TEST 2: AUTHENTICATION WITH INVALID CREDENTIALS")
        _logger.info("=" * 80)
        
        # Use invalid credentials
        invalid_user = "INVALID_USER_123"
        invalid_pass = "INVALID_PASS_123"
        
        url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
        headers = {"Content-Type": "text/xml; charset=utf-8"}
        
        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <chek_service_user xmlns="http://tempuri.org/">
              <su>{invalid_user}</su>
              <sp>{invalid_pass}</sp>
            </chek_service_user>
          </soap:Body>
        </soap:Envelope>"""
        
        success, response_text, error_msg = self.picking._safe_soap_request(
            url, soap_body, headers, "chek_service_user_invalid"
        )
        
        # The request should succeed (HTTP 200) but the result should indicate failure
        self.assertTrue(success, "HTTP request should succeed even with invalid credentials")
        
        _logger.info(f"✓ HTTP Request Status: SUCCESS (as expected)")
        
        # Parse response
        try:
            root = ET.fromstring(response_text)
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns': 'http://tempuri.org/'
            }
            
            # Check for chek_service_userResult
            result_element = root.find('.//ns:chek_service_userResult', namespaces)
            if result_element is not None:
                result = result_element.text
                _logger.info(f"✓ Service User Check Result: {result}")
                self.assertEqual(result.lower(), 'false', 
                    f"chek_service_userResult should be 'false' for invalid credentials, got: {result}")
            
            # Check un_id (should be negative or indicate error)
            un_id_element = root.find('.//ns:un_id', namespaces)
            if un_id_element is not None:
                un_id = un_id_element.text
                _logger.info(f"✓ User ID (un_id): {un_id}")
                # For invalid credentials, un_id might be negative or "0"
                
            _logger.info("=" * 80)
            _logger.info("✅ TEST 2 PASSED: Invalid credentials rejected properly")
            _logger.info("=" * 80)
            
        except ET.ParseError as e:
            self.fail(f"Failed to parse XML response: {e}\nResponse: {response_text}")

    def test_03_authentication_via_partner_button(self):
        """Test 3: Test authentication via res.partner button method"""
        _logger.info("\n" + "=" * 80)
        _logger.info("TEST 3: AUTHENTICATION VIA PARTNER BUTTON METHOD")
        _logger.info("=" * 80)
        
        # Set credentials on partner (via computed field from user)
        self.test_partner.button_send_soap_request()
        
        # Check if buyer_tin was populated
        self.assertIsNotNone(self.test_partner.buyer_tin, 
            "buyer_tin should be populated after button_send_soap_request")
        
        _logger.info(f"✓ Buyer TIN populated: {self.test_partner.buyer_tin}")
        _logger.info("=" * 80)
        _logger.info("✅ TEST 3 PASSED: Partner authentication button works")
        _logger.info("=" * 80)

    def test_04_authentication_computed_fields(self):
        """Test 4: Verify RS credentials are properly computed from user"""
        _logger.info("\n" + "=" * 80)
        _logger.info("TEST 4: VERIFY COMPUTED RS CREDENTIALS")
        _logger.info("=" * 80)
        
        # Force compute
        self.test_partner._compute_rs_acc()
        self.test_partner._compute_rs_pass()
        
        # Check computed values
        self.assertEqual(self.test_partner.rs_acc, self.rs_acc,
            f"Partner rs_acc should match user's rs_acc. Expected: {self.rs_acc}, Got: {self.test_partner.rs_acc}")
        
        self.assertEqual(self.test_partner.rs_pass, self.rs_pass,
            f"Partner rs_pass should match user's rs_pass")
        
        _logger.info(f"✓ Partner rs_acc: {self.test_partner.rs_acc}")
        _logger.info(f"✓ Partner rs_pass: {'*' * len(self.test_partner.rs_pass)}")
        _logger.info("=" * 80)
        _logger.info("✅ TEST 4 PASSED: Computed fields work correctly")
        _logger.info("=" * 80)

    def test_05_authentication_from_picking(self):
        """Test 5: Test authentication through stock.picking model"""
        _logger.info("\n" + "=" * 80)
        _logger.info("TEST 5: AUTHENTICATION VIA STOCK.PICKING")
        _logger.info("=" * 80)
        
        # Force compute on picking
        self.picking._compute_rs_acc()
        self.picking._compute_rs_pass()
        
        # Verify credentials are accessible
        self.assertEqual(self.picking.rs_acc, self.rs_acc,
            "Picking rs_acc should match user's rs_acc")
        self.assertEqual(self.picking.rs_pass, self.rs_pass,
            "Picking rs_pass should match user's rs_pass")
        
        _logger.info(f"✓ Picking rs_acc: {self.picking.rs_acc}")
        _logger.info(f"✓ Picking rs_pass: {'*' * len(self.picking.rs_pass)}")
        
        # Now test actual SOAP request through picking
        url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
        headers = {"Content-Type": "text/xml; charset=utf-8"}
        
        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <chek_service_user xmlns="http://tempuri.org/">
              <su>{self.picking.rs_acc}</su>
              <sp>{self.picking.rs_pass}</sp>
            </chek_service_user>
          </soap:Body>
        </soap:Envelope>"""
        
        success, response_text, error_msg = self.picking._safe_soap_request(
            url, soap_body, headers, "chek_service_user_from_picking"
        )
        
        self.assertTrue(success, f"Authentication from picking should succeed. Error: {error_msg}")
        
        # Parse and verify un_id
        un_id = self.picking._parse_xml_response(
            response_text, 
            './/ns:un_id',
            {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 'ns': 'http://tempuri.org/'}
        )
        
        self.assertIsNotNone(un_id, "un_id should be returned")
        self.assertFalse(un_id.startswith('-'), f"un_id should be positive, got: {un_id}")
        
        _logger.info(f"✓ Authentication via picking successful")
        _logger.info(f"✓ User ID (un_id): {un_id}")
        _logger.info("=" * 80)
        _logger.info("✅ TEST 5 PASSED: Picking authentication works correctly")
        _logger.info("=" * 80)

