"""
Test RS.GE get_name_from_tin API
Detailed test for TIN name lookup functionality
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
TEST_TINS = [
    "01008062291",  # User provided TIN
    "12345678910",  # User provided buyer TIN
    "206322102",    # Part of username (might be company TIN)
]

def print_section(title):
    print("\n" + "=" * 80)
    print(title.center(80))
    print("=" * 80)

def test_get_name_from_tin(tin):
    """Test getting name from a specific TIN"""
    print_section(f"TESTING TIN: {tin}")
    
    url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "http://tempuri.org/get_name_from_tin"
    }
    
    soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
               xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
               xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <get_name_from_tin xmlns="http://tempuri.org/">
      <su>{RS_ACC}</su>
      <sp>{RS_PASS}</sp>
      <tin>{tin}</tin>
    </get_name_from_tin>
  </soap:Body>
</soap:Envelope>"""
    
    print(f"[INFO] Sending request to: {url}")
    print(f"[INFO] Username: {RS_ACC}")
    print(f"[INFO] TIN: {tin}")
    
    try:
        response = requests.post(
            url, 
            data=soap_request.encode('utf-8'), 
            headers=headers, 
            timeout=30
        )
        
        print(f"[INFO] Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("[OK] HTTP Request: SUCCESS")
            
            # Parse the full response
            root = ET.fromstring(response.text)
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns': 'http://tempuri.org/'
            }
            
            # Pretty print the response
            print("\n[INFO] Full SOAP Response:")
            print("-" * 80)
            print(response.text)
            print("-" * 80)
            
            # Try to find the result
            result_element = root.find('.//ns:get_name_from_tinResult', namespaces)
            
            if result_element is not None:
                result = result_element.text
                print(f"\n[INFO] Result: '{result}'")
                
                if result is None or result == '':
                    print("[FAIL] Result is None or empty")
                    return False, None
                elif result.startswith('-'):
                    print(f"[FAIL] Error code returned: {result}")
                    # Try to decode error
                    if result == '-3':
                        print("[INFO] Error -3: Invalid service user or authentication failed")
                    elif result == '-100':
                        print("[INFO] Error -100: Authentication error")
                    elif result == '-2':
                        print("[INFO] Error -2: Invalid TIN format")
                    elif result == '-1':
                        print("[INFO] Error -1: TIN not found")
                    return False, result
                else:
                    print(f"[OK] Name retrieved: {result}")
                    return True, result
            else:
                print("[FAIL] Could not find get_name_from_tinResult in response")
                
                # Try alternative parsing
                if '<get_name_from_tinResult>' in response.text:
                    start_tag = "<get_name_from_tinResult>"
                    end_tag = "</get_name_from_tinResult>"
                    start_index = response.text.find(start_tag) + len(start_tag)
                    end_index = response.text.find(end_tag)
                    result = response.text[start_index:end_index].strip()
                    print(f"[INFO] Alternative parsing found: '{result}'")
                    
                    if result:
                        if result.startswith('-'):
                            print(f"[FAIL] Error code: {result}")
                            return False, result
                        else:
                            print(f"[OK] Name: {result}")
                            return True, result
                
                return False, None
                
        else:
            print(f"[FAIL] HTTP Error: {response.status_code}")
            print(f"[INFO] Response: {response.text[:500]}")
            return False, None
            
    except requests.exceptions.Timeout:
        print("[FAIL] Request timeout (30 seconds)")
        return False, None
    except requests.exceptions.ConnectionError:
        print("[FAIL] Connection error")
        return False, None
    except Exception as e:
        print(f"[FAIL] Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def test_with_different_formats():
    """Test TIN with different formatting"""
    print_section("TESTING DIFFERENT TIN FORMATS")
    
    tin_formats = [
        ("Standard", "01008062291"),
        ("Without leading zero", "1008062291"),
        ("With spaces", "01 00 80 62 291"),
        ("Short TIN", "206322102"),
    ]
    
    results = {}
    for format_name, tin in tin_formats:
        print(f"\n[TEST] Format: {format_name}")
        print(f"[TEST] TIN: {tin}")
        
        success, result = test_get_name_from_tin(tin)
        results[format_name] = (success, result)
        
        print()  # Spacing
    
    return results

def main():
    """Run all TIN lookup tests"""
    print_section("RS.GE GET_NAME_FROM_TIN API TEST")
    print(f"Credentials: {RS_ACC}")
    print(f"Testing multiple TINs...")
    
    all_results = {}
    
    # Test each provided TIN
    for tin in TEST_TINS:
        success, result = test_get_name_from_tin(tin)
        all_results[tin] = (success, result)
        print()  # Spacing between tests
    
    # Test different formats
    print("\n" + "=" * 80)
    format_results = test_with_different_formats()
    
    # Summary
    print_section("TEST SUMMARY")
    
    print("\n[1] Standard TIN Tests:")
    for tin, (success, result) in all_results.items():
        status = "[OK] PASSED" if success else "[FAIL] FAILED"
        print(f"  TIN {tin}: {status} - Result: {result}")
    
    print("\n[2] Format Variation Tests:")
    for format_name, (success, result) in format_results.items():
        status = "[OK] PASSED" if success else "[FAIL] FAILED"
        print(f"  {format_name}: {status} - Result: {result}")
    
    # Overall stats
    total_tests = len(all_results) + len(format_results)
    passed_tests = sum(1 for s, _ in all_results.values() if s) + \
                   sum(1 for s, _ in format_results.values() if s)
    
    print(f"\n[STATS] Total: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == 0:
        print("\n[WARNING] All tests failed - likely due to authentication error -3")
        print("[INFO] The service user credentials may need to be verified with RS.GE")
    elif passed_tests == total_tests:
        print("\n[SUCCESS] All TIN lookups successful!")
    else:
        print(f"\n[PARTIAL] Some lookups succeeded, some failed")
    
    return 0 if passed_tests > 0 else 1

if __name__ == "__main__":
    exit(main())

