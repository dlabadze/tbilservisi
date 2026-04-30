"""
Detailed RS.GE API Test with Full Request/Response Debug
Shows EXACTLY what is being sent and received
"""

import requests
import xml.etree.ElementTree as ET
import sys
import io

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Test Credentials
RS_ACC = "odootest:206322102"
RS_PASS = "Aa123456!"
VALID_TIN = "01008062291"

def print_section(title):
    print("\n" + "=" * 100)
    print(title.center(100))
    print("=" * 100)

def test_authentication_detailed():
    """Test authentication with full request/response details"""
    print_section("TEST 1: AUTHENTICATION (chek_service_user)")
    
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
    
    print("\n[SENDING TO]")
    print(f"URL: {url}")
    print(f"Method: POST")
    
    print("\n[REQUEST HEADERS]")
    for key, value in headers.items():
        print(f"  {key}: {value}")
    
    print("\n[REQUEST BODY - EXACT SOAP ENVELOPE BEING SENT]")
    print("-" * 100)
    print(soap_body)
    print("-" * 100)
    
    print("\n[CREDENTIALS BEING SENT]")
    print(f"  Username (su): {RS_ACC}")
    print(f"  Password (sp): {RS_PASS}")
    
    try:
        print("\n[SENDING REQUEST...]")
        response = requests.post(url, data=soap_body.encode('utf-8'), headers=headers, timeout=30)
        
        print(f"\n[RESPONSE RECEIVED]")
        print(f"  Status Code: {response.status_code}")
        print(f"  Status: {'SUCCESS' if response.status_code == 200 else 'FAILED'}")
        
        print("\n[RESPONSE HEADERS]")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        
        print("\n[RESPONSE BODY - EXACT XML RECEIVED]")
        print("-" * 100)
        print(response.text)
        print("-" * 100)
        
        if response.status_code == 200:
            # Parse and extract values
            root = ET.fromstring(response.text)
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns': 'http://tempuri.org/'
            }
            
            un_id_element = root.find('.//ns:un_id', namespaces)
            result_element = root.find('.//ns:chek_service_userResult', namespaces)
            s_user_id_element = root.find('.//ns:s_user_id', namespaces)
            
            print("\n[PARSED VALUES]")
            if un_id_element is not None:
                un_id = un_id_element.text
                print(f"  un_id: {un_id}")
                if un_id and not un_id.startswith('-'):
                    print(f"  [OK] Authentication SUCCESSFUL! User ID is positive")
                    return True, un_id
                else:
                    print(f"  [FAIL] Authentication FAILED! Error code: {un_id}")
            
            if result_element is not None:
                result = result_element.text
                print(f"  chek_service_userResult: {result}")
            
            if s_user_id_element is not None:
                s_user_id = s_user_id_element.text
                print(f"  s_user_id: {s_user_id}")
            
            if un_id and un_id.startswith('-'):
                return False, un_id
            return True, un_id if un_id_element is not None else None
            
    except Exception as e:
        print(f"\n[EXCEPTION OCCURRED]")
        print(f"  Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def test_get_name_from_tin_detailed():
    """Test TIN name lookup with full request/response details"""
    print_section("TEST 2: GET NAME FROM TIN (get_name_from_tin)")
    
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
    
    print("\n[SENDING TO]")
    print(f"URL: {url}")
    print(f"Method: POST")
    
    print("\n[REQUEST HEADERS]")
    for key, value in headers.items():
        print(f"  {key}: {value}")
    
    print("\n[REQUEST BODY - EXACT SOAP ENVELOPE BEING SENT]")
    print("-" * 100)
    print(soap_request)
    print("-" * 100)
    
    print("\n[PARAMETERS BEING SENT]")
    print(f"  Username (su): {RS_ACC}")
    print(f"  Password (sp): {RS_PASS}")
    print(f"  TIN (tin): {VALID_TIN}")
    
    try:
        print("\n[SENDING REQUEST...]")
        response = requests.post(url, data=soap_request.encode('utf-8'), headers=headers, timeout=30)
        
        print(f"\n[RESPONSE RECEIVED]")
        print(f"  Status Code: {response.status_code}")
        print(f"  Status: {'SUCCESS' if response.status_code == 200 else 'FAILED'}")
        
        print("\n[RESPONSE HEADERS]")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        
        print("\n[RESPONSE BODY - EXACT XML RECEIVED]")
        print("-" * 100)
        print(response.text)
        print("-" * 100)
        
        if response.status_code == 200:
            # Parse and extract values
            root = ET.fromstring(response.text)
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns': 'http://tempuri.org/'
            }
            
            result_element = root.find('.//ns:get_name_from_tinResult', namespaces)
            
            print("\n[PARSED VALUES]")
            if result_element is not None:
                result = result_element.text
                print(f"  get_name_from_tinResult: '{result}'")
                
                if result is None or result == '':
                    print(f"  [INFO] Result is empty/null - likely auth issue")
                    return False, None
                elif result.startswith('-'):
                    print(f"  [FAIL] Error code returned: {result}")
                    return False, result
                else:
                    print(f"  [OK] SUCCESS! Company/Person name retrieved")
                    return True, result
            else:
                print(f"  [FAIL] get_name_from_tinResult element not found")
                return False, None
                
    except Exception as e:
        print(f"\n[EXCEPTION OCCURRED]")
        print(f"  Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def main():
    """Run detailed debug tests"""
    print_section("RS.GE API - DETAILED DEBUG TEST")
    print(f"\nTest Credentials:")
    print(f"  Username: {RS_ACC}")
    print(f"  Password: {RS_PASS}")
    print(f"  Test TIN: {VALID_TIN}")
    
    # Test 1: Authentication
    auth_success, auth_result = test_authentication_detailed()
    
    print("\n")
    
    # Test 2: TIN Lookup
    tin_success, tin_result = test_get_name_from_tin_detailed()
    
    # Summary
    print_section("SUMMARY")
    print(f"\n[1] Authentication Test: {'[OK] PASSED' if auth_success else '[FAIL] FAILED'}")
    if auth_result:
        print(f"    Result: {auth_result}")
    
    print(f"\n[2] TIN Lookup Test: {'[OK] PASSED' if tin_success else '[FAIL] FAILED'}")
    if tin_result:
        print(f"    Result: {tin_result}")
    
    if auth_success and tin_success:
        print("\n*** ALL TESTS PASSED! API IS WORKING! ***")
        print(f"*** Company Name for TIN {VALID_TIN}: {tin_result} ***")
        return 0
    elif auth_success and not tin_success:
        print("\n*** Authentication works but TIN lookup failed ***")
        print("*** Check if TIN exists in RS.GE database ***")
        return 1
    else:
        print("\n*** Authentication failed - verify credentials with RS.GE ***")
        return 1

if __name__ == "__main__":
    exit(main())

