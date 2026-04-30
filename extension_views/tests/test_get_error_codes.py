"""
Get RS.GE Error Codes - Find what error -4002 means
"""

import requests
import xml.etree.ElementTree as ET
import sys
import io

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

RS_ACC = "odootest:206322102"
RS_PASS = "Aa123456!"

def get_all_error_codes():
    """Get all RS.GE error codes"""
    print("=" * 100)
    print("RS.GE ERROR CODES LOOKUP".center(100))
    print("=" * 100)
    
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
    </soap:Envelope>"""
    
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "http://tempuri.org/get_error_codes"
    }
    
    try:
        response = requests.post(
            "http://services.rs.ge/waybillservice/waybillservice.asmx",
            data=soap_request,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            print("[OK] Successfully retrieved error codes\n")
            
            root = ET.fromstring(response.content)
            error_dict = {}
            
            for error_code in root.findall(".//ERROR_CODE"):
                id_value = error_code.find("ID")
                text_value = error_code.find("TEXT")
                type_value = error_code.find("TYPE")
                
                if id_value is not None and text_value is not None:
                    error_id = id_value.text
                    error_text = text_value.text
                    error_type = type_value.text if type_value is not None else "N/A"
                    error_dict[error_id] = (error_text, error_type)
            
            # Look for -4002 specifically
            print("=" * 100)
            print(f"SEARCHING FOR ERROR CODE: -4002")
            print("=" * 100)
            
            if "-4002" in error_dict:
                text, err_type = error_dict["-4002"]
                print(f"\n[FOUND] Error -4002:")
                print(f"  Text: {text}")
                print(f"  Type: {err_type}")
            else:
                print("\n[NOT FOUND] Error code -4002 not in standard error list")
                print("[INFO] This might be a dynamic validation error")
            
            # Show related errors (4000-range)
            print("\n" + "=" * 100)
            print("RELATED ERRORS IN 4000-RANGE:")
            print("=" * 100)
            
            for error_id in sorted(error_dict.keys(), key=lambda x: int(x)):
                if error_id.startswith('-4'):
                    text, err_type = error_dict[error_id]
                    print(f"\n{error_id}: {text}")
                    print(f"  Type: {err_type}")
            
            # Show all errors for reference
            print("\n" + "=" * 100)
            print(f"ALL ERROR CODES (Total: {len(error_dict)}):")
            print("=" * 100)
            
            for error_id in sorted(error_dict.keys(), key=lambda x: int(x)):
                text, err_type = error_dict[error_id]
                print(f"{error_id}: {text} (Type: {err_type})")
            
            return error_dict
        else:
            print(f"[FAIL] HTTP Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"[FAIL] Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    get_all_error_codes()

