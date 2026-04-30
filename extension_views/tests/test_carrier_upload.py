"""
Test Carrier Waybill Upload (TRANS_ID = 7)
Upload actual waybill to RS.GE with carrier configuration
"""

import requests
import xml.etree.ElementTree as ET
import sys
import io
from datetime import datetime

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Test Credentials
RS_ACC = "odootest:206322102"
RS_PASS = "Aa123456!"

# Test Data  
CARRIER_TIN = "12345678910"      # Carrier TIN (user provided)
BUYER_TIN = "12345678910"        # Buyer TIN (same as carrier for testing)
BUYER_NAME = "ტესტ მყიდველი"     # Test buyer name

def print_section(title):
    print("\n" + "=" * 100)
    print(title.center(100))
    print("=" * 100)

def upload_carrier_waybill():
    """Upload waybill with TRANS_ID = 7 (Carrier)"""
    print_section("UPLOADING WAYBILL WITH TRANS_ID = 7 (გადამზიდავი)")
    
    # Step 1: Authenticate
    print("\n[STEP 1] Authenticating...")
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
    
    response = requests.post(url, data=soap_body.encode('utf-8'), headers=headers, timeout=30)
    root = ET.fromstring(response.text)
    namespaces = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 'ns': 'http://tempuri.org/'}
    
    un_id_element = root.find('.//ns:un_id', namespaces)
    seller_un_id = un_id_element.text
    
    print(f"[OK] Authenticated - Seller UN_ID: {seller_un_id}")
    
    # Step 2: Prepare waybill with carrier
    print("\n[STEP 2] Preparing waybill data...")
    begin_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    
    print(f"  TYPE: 2 (მიწოდება ტრანსპორტირებით)")
    print(f"  TRANS_ID: 7 (გადამზიდავი)")
    print(f"  TRANSPORTER_TIN: {CARRIER_TIN}")
    print(f"  STATUS: 0 (დრაფტი)")
    print(f"  DRIVER_TIN: (empty - carrier will assign)")
    print(f"  DRIVER_NAME: (empty - carrier will assign)")
    print(f"  CAR_NUMBER: (empty - carrier will assign)")
    
    # Step 3: Build SOAP request
    waybill_xml = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
        <soap:Body>
            <save_waybill xmlns="http://tempuri.org/">
                <su>{RS_ACC}</su>
                <sp>{RS_PASS}</sp>
                <waybill>
                    <WAYBILL xmlns="">
                        <GOODS_LIST>
                            <GOODS>
                                <ID>0</ID>
                                <W_NAME>ტესტ პროდუქტი - გადამზიდავით</W_NAME>
                                <UNIT_ID>1</UNIT_ID>
                                <UNIT_TXT>ცალი</UNIT_TXT>
                                <QUANTITY>5</QUANTITY>
                                <PRICE>100</PRICE>
                                <STATUS>1</STATUS>
                                <AMOUNT>500</AMOUNT>
                                <BAR_CODE></BAR_CODE>
                                <A_ID>0</A_ID>
                                <VAT_TYPE>0</VAT_TYPE>
                            </GOODS>
                        </GOODS_LIST>
                        <ID>0</ID>
                        <TYPE>2</TYPE>
                        <BUYER_TIN>{BUYER_TIN}</BUYER_TIN>
                        <CHEK_BUYER_TIN>1</CHEK_BUYER_TIN>
                        <BUYER_NAME>ტესტ მყიდველი</BUYER_NAME>
                        <START_ADDRESS>თბილისი, ვაკე, ჭავჭავაძის 12</START_ADDRESS>
                        <END_ADDRESS>თბილისი, საბურთალო, კოსტავას 77</END_ADDRESS>
                        <DRIVER_TIN></DRIVER_TIN>
                        <CHEK_DRIVER_TIN>1</CHEK_DRIVER_TIN>
                        <DRIVER_NAME></DRIVER_NAME>
                        <TRANSPORT_COAST>50</TRANSPORT_COAST>
                        <RECEPTION_INFO></RECEPTION_INFO>
                        <RECEIVER_INFO></RECEIVER_INFO>
                        <DELIVERY_DATE></DELIVERY_DATE>
                        <STATUS>0</STATUS>
                        <SELER_UN_ID>{seller_un_id}</SELER_UN_ID>
                        <PAR_ID>0</PAR_ID>
                        <CAR_NUMBER></CAR_NUMBER>
                        <BEGIN_DATE>{begin_date}</BEGIN_DATE>
                        <TRAN_COST_PAYER>1</TRAN_COST_PAYER>
                        <TRANS_ID>7</TRANS_ID>
                        <TRANS_TXT></TRANS_TXT>
                        <COMMENT>ტესტ ზედნადები გადამზიდავით - მძღოლის გარეშე</COMMENT>
                        <TRANSPORTER_TIN>{CARRIER_TIN}</TRANSPORTER_TIN>
                    </WAYBILL>
                </waybill>
            </save_waybill>
        </soap:Body>
    </soap:Envelope>"""
    
    # Step 4: Upload to RS.GE
    print("\n[STEP 3] Uploading to RS.GE...")
    url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "http://tempuri.org/save_waybill"
    }
    
    try:
        response = requests.post(url, data=waybill_xml.encode('utf-8'), headers=headers, timeout=30)
        print(f"[OK] Response received - HTTP Status: {response.status_code}")
        
        # Parse response
        if '<STATUS>' in response.text:
            status = response.text.split('<STATUS>')[1].split('</STATUS>')[0]
            print(f"\n[RESPONSE] Waybill STATUS: {status}")
            
            if int(status) >= 0:
                print("\n" + "=" * 100)
                print("[SUCCESS] WAYBILL UPLOADED SUCCESSFULLY!".center(100))
                print("=" * 100)
                
                # Extract waybill details
                if '<ID>' in response.text:
                    wb_id = response.text.split('<ID>')[1].split('</ID>')[0]
                    print(f"\n[OK] Waybill ID: {wb_id}")
                
                if '<WAYBILL_NUMBER>' in response.text:
                    wb_number = response.text.split('<WAYBILL_NUMBER>')[1].split('</WAYBILL_NUMBER>')[0]
                    print(f"[OK] Waybill Number: {wb_number}")
                
                print(f"\n[INFO] Waybill Details:")
                print(f"  - Status: 0 (დრაფტი - Draft)")
                print(f"  - Carrier TIN: {CARRIER_TIN}")
                print(f"  - Driver: Not assigned (carrier will assign)")
                print(f"  - Car: Not assigned (carrier will assign)")
                
                print(f"\n[NEXT STEPS]")
                print(f"  1. Carrier will receive notification in RS.GE")
                print(f"  2. Carrier assigns driver and vehicle")
                print(f"  3. Carrier activates waybill (changes status to 1)")
                
                return True, wb_id if '<ID>' in response.text else None
            else:
                print("\n" + "=" * 100)
                print("[FAILED] UPLOAD FAILED".center(100))
                print("=" * 100)
                print(f"\n[ERROR] Status Code: {status}")
                
                # Common error codes
                error_messages = {
                    '-1': 'ველის შევსება არასწორია',
                    '-2': 'არასწორი TIN',
                    '-3': 'ავტორიზაციის შეცდომა',
                    '-100': 'მომხმარებლის შეცდომა',
                    '-4002': 'TIN ვალიდაციის შეცდომა'
                }
                
                if status in error_messages:
                    print(f"[ERROR] {error_messages[status]}")
                
                # Show full response for debugging
                print(f"\n[DEBUG] Full Response:")
                print(response.text)
                
                return False, status
        else:
            print("\n[ERROR] No STATUS found in response")
            print(f"[DEBUG] Response: {response.text[:500]}")
            return False, None
            
    except Exception as e:
        print(f"\n[EXCEPTION] Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def main():
    """Run carrier upload test"""
    print_section("RS.GE CARRIER WAYBILL UPLOAD TEST")
    
    print(f"\n[CONFIG] Test Configuration:")
    print(f"  Username: {RS_ACC}")
    print(f"  Carrier TIN: {CARRIER_TIN}")
    print(f"  Buyer TIN: {BUYER_TIN}")
    print(f"  Buyer Name: {BUYER_NAME}")
    
    success, result = upload_carrier_waybill()
    
    if success:
        print("\n" + "=" * 100)
        print("TEST PASSED - CARRIER CONFIGURATION WORKING!".center(100))
        print("=" * 100)
        print(f"\n[RESULT] Waybill uploaded successfully with ID: {result}")
        print(f"[VERIFIED] TRANS_ID = 7 works without driver information")
        return 0
    else:
        print("\n" + "=" * 100)
        print("TEST FAILED".center(100))
        print("=" * 100)
        if result:
            print(f"\n[ERROR CODE] {result}")
        print(f"\n[INFO] Check error details above")
        return 1

if __name__ == "__main__":
    exit(main())

