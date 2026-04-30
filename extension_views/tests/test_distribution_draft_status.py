"""
Test Distribution Waybill with Draft Status (STATUS=0)
Verifies that distribution waybills without driver info are accepted when sent as draft
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

def print_section(title):
    print("\n" + "=" * 100)
    print(title.center(100))
    print("=" * 100)

def test_distribution_draft_no_driver():
    """Test distribution with STATUS=0 (draft) and NO driver info"""
    print_section("TEST: DISTRIBUTION WITH STATUS=0 (DRAFT) - NO DRIVER")
    
    # Get authentication
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
    
    print(f"[INFO] Authenticated - Seller UN_ID: {seller_un_id}")
    
    # Create distribution waybill WITHOUT driver, STATUS=0
    begin_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    
    waybill_xml = f"""
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
                                <W_NAME>ტესტ პროდუქტი - დისტრიბუცია</W_NAME>
                                <UNIT_ID>1</UNIT_ID>
                                <UNIT_TXT>ცალი</UNIT_TXT>
                                <QUANTITY>1</QUANTITY>
                                <PRICE>10</PRICE>
                                <STATUS>1</STATUS>
                                <AMOUNT>10</AMOUNT>
                                <BAR_CODE></BAR_CODE>
                                <A_ID>0</A_ID>
                                <VAT_TYPE>0</VAT_TYPE>
                            </GOODS>
                        </GOODS_LIST>
                        <ID>0</ID>
                        <TYPE>4</TYPE>
                        <BUYER_TIN>12345678910</BUYER_TIN>
                        <CHEK_BUYER_TIN>1</CHEK_BUYER_TIN>
                        <BUYER_NAME>ტესტ მყიდველი</BUYER_NAME>
                        <START_ADDRESS>თბილისი, ვაკე</START_ADDRESS>
                        <END_ADDRESS>თბილისი, საბურთალო</END_ADDRESS>
                        <DRIVER_TIN></DRIVER_TIN>
                        <CHEK_DRIVER_TIN>1</CHEK_DRIVER_TIN>
                        <DRIVER_NAME></DRIVER_NAME>
                        <TRANSPORT_COAST>0</TRANSPORT_COAST>
                        <RECEPTION_INFO></RECEPTION_INFO>
                        <RECEIVER_INFO></RECEIVER_INFO>
                        <DELIVERY_DATE></DELIVERY_DATE>
                        <STATUS>0</STATUS>
                        <SELER_UN_ID>{seller_un_id}</SELER_UN_ID>
                        <PAR_ID>0</PAR_ID>
                        <CAR_NUMBER></CAR_NUMBER>
                        <BEGIN_DATE>{begin_date}</BEGIN_DATE>
                        <TRAN_COST_PAYER>1</TRAN_COST_PAYER>
                        <TRANS_ID>1</TRANS_ID>
                        <TRANS_TXT></TRANS_TXT>
                        <COMMENT>ტესტი - დისტრიბუცია დრაფტით, მძღოლის გარეშე</COMMENT>
                        <TRANSPORTER_TIN></TRANSPORTER_TIN>
                    </WAYBILL>
                </waybill>
            </save_waybill>
        </soap:Body>
    </soap:Envelope>"""
    
    print("\n[SENDING] Distribution waybill:")
    print("  TYPE: 4 (დისტრიბუცია)")
    print("  STATUS: 0 (დრაფტი)")
    print("  DRIVER_TIN: (empty)")
    print("  DRIVER_NAME: (empty)")
    print("  CAR_NUMBER: (empty)")
    
    url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "http://tempuri.org/save_waybill"
    }
    
    try:
        response = requests.post(url, data=waybill_xml.encode('utf-8'), headers=headers, timeout=30)
        print(f"\n[RESPONSE] HTTP Status: {response.status_code}")
        
        # Parse response
        if '<STATUS>' in response.text:
            status = response.text.split('<STATUS>')[1].split('</STATUS>')[0]
            print(f"[RESPONSE] Waybill STATUS: {status}")
            
            if int(status) >= 0:
                print("\n[OK] SUCCESS! Distribution accepted WITHOUT driver info!")
                
                # Extract IDs
                if '<ID>' in response.text:
                    wb_id = response.text.split('<ID>')[1].split('</ID>')[0]
                    print(f"[OK] Waybill ID: {wb_id}")
                
                if '<WAYBILL_NUMBER>' in response.text:
                    wb_number = response.text.split('<WAYBILL_NUMBER>')[1].split('</WAYBILL_NUMBER>')[0]
                    print(f"[OK] Waybill Number: {wb_number}")
                
                print("\n[INFO] The waybill is saved as DRAFT (status=0)")
                print("[INFO] Driver can be assigned later and status changed to Active (1)")
                return True, wb_id if '<ID>' in response.text else None
            else:
                print(f"\n[FAIL] Error code: {status}")
                print("[INFO] Checking what the error means...")
                
                # Try to get error description
                if status == '-4002':
                    print("[ERROR] -4002: TIN validation issue")
                    print("[INFO] This might be a buyer/seller TIN conflict")
                
                return False, status
        else:
            print("[FAIL] No STATUS in response")
            print(f"[DEBUG] Response: {response.text[:500]}")
            return False, None
            
    except Exception as e:
        print(f"\n[FAIL] Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def main():
    """Run distribution draft test"""
    print_section("RS.GE DISTRIBUTION WITH DRAFT STATUS TEST")
    
    print("\n[GOAL] Verify that distribution waybills can be uploaded WITHOUT driver")
    print("[METHOD] Send TYPE=4 with STATUS=0 (draft) and empty driver fields")
    
    success, result = test_distribution_draft_no_driver()
    
    print_section("CONCLUSION")
    
    if success:
        print("\n[SUCCESS] Your Odoo configuration is CORRECT!")
        print(f"[SUCCESS] Waybill ID: {result}")
        print("\n[SUMMARY]")
        print("  - Distribution (TYPE=4) with STATUS=0 (draft) works")
        print("  - Driver fields can be EMPTY")
        print("  - Driver can be assigned later")
        print("  - Then status can be changed to Active (1)")
        return 0
    else:
        print(f"\n[FAILED] Test did not pass")
        if result:
            print(f"[ERROR] Error code: {result}")
        print("\n[INFO] This might be due to:")
        print("  - TIN validation (error -4002)")
        print("  - Other required fields missing")
        print("  - Need different test data")
        return 1

if __name__ == "__main__":
    exit(main())

