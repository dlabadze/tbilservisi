"""
Standalone RS.GE Authentication Test
This script tests RS.GE API authentication without requiring Odoo test framework.
Run with: python test_auth_standalone.py
"""

import requests
import xml.etree.ElementTree as ET
import logging
import sys
import io

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
_logger = logging.getLogger(__name__)

# Test Credentials
RS_ACC = "odootest:206322102"
RS_PASS = "Aa123456!"
VALID_TIN = "01008062291"
DRIVER_TIN = "01008062291"
BUYER_TIN = "12345678910"

def print_section(title):
    print("\n" + "=" * 80)
    print(title.center(80))
    print("=" * 80)

def get_error_text_from_code(error_code):
    """Get error text from RS.GE error codes"""
    try:
        soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
                       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                       xmlns:xsd="http://www.w3.org/2001/XMLSchema">
            <soap:Body>
                <get_error_codes xmlns="http://tempuri.org/">
                    <su>{RS_ACC}</su>
                    <sp>{RS_PASS}</sp>
                </get_error_codes>
            </soap:Body>
        </soap:Envelope>
        """
        
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_error_codes"
        }
        
        response = requests.post(
            "http://services.rs.ge/waybillservice/waybillservice.asmx",
            data=soap_request,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            error_dict = {}
            
            for error_code_elem in root.findall(".//ERROR_CODE"):
                id_elem = error_code_elem.find("ID")
                text_elem = error_code_elem.find("TEXT")
                if id_elem is not None and text_elem is not None:
                    error_dict[id_elem.text] = text_elem.text
            
            error_code_str = str(error_code)
            return error_dict.get(error_code_str, f"Unknown error: code {error_code}")
        
        return f"Could not retrieve error codes (HTTP {response.status_code})"
    except Exception as e:
        return f"Error retrieving error text: {str(e)}"

def test_authentication():
    """Test 1: Authenticate with VALID credentials"""
    print_section("TEST 1: AUTHENTICATION WITH VALID CREDENTIALS")
    
    url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
    headers = {"Content-Type": "text/xml; charset=utf-8"}
    
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <chek_service_user xmlns="http://tempuri.org/">
          <su>{RS_ACC}</su>
          <sp>{RS_PASS}</sp>
        </chek_service_user>
      </soap:Body>
    </soap:Envelope>"""
    
    try:
        _logger.info(f"Sending request to: {url}")
        _logger.info(f"Username: {RS_ACC}")
        
        response = requests.post(url, data=soap_body.encode('utf-8'), headers=headers, timeout=30)
        
        _logger.info(f"Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("[OK] HTTP Request: SUCCESS")
            
            # Parse XML response
            root = ET.fromstring(response.text)
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns': 'http://tempuri.org/'
            }
            
            # Check for un_id
            un_id_element = root.find('.//ns:un_id', namespaces)
            if un_id_element is not None:
                un_id = un_id_element.text
                print(f"[OK] User ID (un_id): {un_id}")
                
                if un_id.startswith('-'):
                    error_text = get_error_text_from_code(un_id)
                    print(f"[FAIL] FAILED: un_id is negative (error code): {un_id}")
                    print(f"[FAIL] Error description: {error_text}")
                    print("\n[INFO] Full response (first 1000 chars):")
                    print(response.text[:1000])
                    print("\n[INFO] This usually means:")
                    print("  - Service user credentials are incorrect")
                    print("  - Service user doesn't have API access")
                    print("  - Credentials may have expired")
                    print("  - Wrong environment (test vs production)")
                    return False
                else:
                    print(f"[OK] AUTHENTICATION SUCCESSFUL")
            else:
                print("[FAIL] FAILED: un_id not found in response")
                return False
            
            # Check for chek_service_userResult
            result_element = root.find('.//ns:chek_service_userResult', namespaces)
            if result_element is not None:
                result = result_element.text
                print(f"[OK] Service User Check Result: {result}")
                
                if result.lower() == 'true':
                    print("[OK] Authentication result is TRUE")
                    return True
                else:
                    print(f"[FAIL] Authentication result is FALSE")
                    return False
            
            print("\n" + "-" * 80)
            print("Response XML (first 500 chars):")
            print(response.text[:500])
            print("-" * 80)
            
            return True
            
        else:
            print(f"[FAIL] HTTP Request FAILED: Status {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print("[FAIL] FAILED: Request timed out (30 seconds)")
        return False
    except requests.exceptions.ConnectionError:
        print("[FAIL] FAILED: Connection error - check internet connection")
        return False
    except Exception as e:
        print(f"[FAIL] FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_invalid_credentials():
    """Test 2: Authenticate with INVALID credentials"""
    print_section("TEST 2: AUTHENTICATION WITH INVALID CREDENTIALS")
    
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
    
    try:
        _logger.info(f"Testing with invalid credentials: {invalid_user}")
        
        response = requests.post(url, data=soap_body.encode('utf-8'), headers=headers, timeout=30)
        
        if response.status_code == 200:
            print("[OK] HTTP Request: SUCCESS (as expected)")
            
            # Parse response
            root = ET.fromstring(response.text)
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns': 'http://tempuri.org/'
            }
            
            # Check for chek_service_userResult
            result_element = root.find('.//ns:chek_service_userResult', namespaces)
            if result_element is not None:
                result = result_element.text
                print(f"[OK] Service User Check Result: {result}")
                
                if result.lower() == 'false':
                    print("[OK] Invalid credentials correctly rejected")
                    return True
                else:
                    print(f"[FAIL] UNEXPECTED: Result is {result} (expected 'false')")
                    return False
            
            # Check un_id
            un_id_element = root.find('.//ns:un_id', namespaces)
            if un_id_element is not None:
                un_id = un_id_element.text
                print(f"[OK] User ID (un_id): {un_id}")
            
            return True
            
        else:
            print(f"[FAIL] Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[FAIL] FAILED: {str(e)}")
        return False

def test_get_name_from_tin():
    """Test 3: Get name from TIN"""
    print_section("TEST 3: GET NAME FROM TIN")
    
    url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "http://tempuri.org/get_name_from_tin"
    }
    
    soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <get_name_from_tin xmlns="http://tempuri.org/">
          <su>{RS_ACC}</su>
          <sp>{RS_PASS}</sp>
          <tin>{VALID_TIN}</tin>
        </get_name_from_tin>
      </soap:Body>
    </soap:Envelope>"""
    
    try:
        _logger.info(f"Getting name for TIN: {VALID_TIN}")
        
        response = requests.post(url, data=soap_request.encode('utf-8'), headers=headers, timeout=30)
        
        if response.status_code == 200:
            print("[OK] HTTP Request: SUCCESS")
            
            # Parse response
            root = ET.fromstring(response.text)
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns': 'http://tempuri.org/'
            }
            
            # Find the result
            result_element = root.find('.//ns:get_name_from_tinResult', namespaces)
            
            if result_element is not None:
                name = result_element.text
                print(f"[OK] Name from TIN: {name}")
                
                if name and not name.startswith('-'):
                    print("[OK] Name retrieved successfully")
                    return True
                elif name and name.startswith('-'):
                    print(f"[FAIL] Error code returned: {name}")
                    return False
                else:
                    print("[FAIL] Empty result")
                    return False
            else:
                print("[FAIL] Could not find get_name_from_tinResult in response")
                print(f"Response: {response.text[:500]}")
                return False
                
        else:
            print(f"[FAIL] HTTP Request FAILED: Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[FAIL] FAILED: {str(e)}")
        return False

def main():
    """Run all tests"""
    print_section("RS.GE API AUTHENTICATION TESTS")
    print(f"Test Credentials: {RS_ACC}")
    print(f"Valid TIN: {VALID_TIN}")
    
    results = {}
    
    # Run tests
    results['Authentication (Valid)'] = test_authentication()
    print()
    
    results['Authentication (Invalid)'] = test_invalid_credentials()
    print()
    
    results['Get Name from TIN'] = test_get_name_from_tin()
    print()
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "[OK] PASSED" if passed_test else "[FAIL] FAILED"
        print(f"{test_name}: {status}")
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n*** ALL TESTS PASSED! ***")
        return 0
    else:
        print(f"\n*** WARNING: {total - passed} test(s) failed ***")
        return 1

if __name__ == "__main__":
    exit(main())

