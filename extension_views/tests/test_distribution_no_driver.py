"""
Test RS.GE Distribution Waybill WITHOUT Driver Information
Tests if driver fields are required for TYPE 4 (დისტრიბუცია)
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

def test_distribution_with_driver():
    """Test 1: Distribution WITH driver info (baseline)"""
    print_section("TEST 1: DISTRIBUTION WITH DRIVER INFO")
    
    # First get seller un_id
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
    
    print(f"[INFO] Seller UN_ID: {seller_un_id}")
    
    # Now try to save distribution WITH driver
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
                                <W_NAME>ტესტ პროდუქტი</W_NAME>
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
                        <BUYER_TIN>01008062291</BUYER_TIN>
                        <CHEK_BUYER_TIN>1</CHEK_BUYER_TIN>
                        <BUYER_NAME>ა. კ.</BUYER_NAME>
                        <START_ADDRESS>თბილისი</START_ADDRESS>
                        <END_ADDRESS>თბილისი</END_ADDRESS>
                        <DRIVER_TIN>01008062291</DRIVER_TIN>
                        <CHEK_DRIVER_TIN>1</CHEK_DRIVER_TIN>
                        <DRIVER_NAME>ა. კ.</DRIVER_NAME>
                        <TRANSPORT_COAST>0</TRANSPORT_COAST>
                        <RECEPTION_INFO></RECEPTION_INFO>
                        <RECEIVER_INFO></RECEIVER_INFO>
                        <DELIVERY_DATE></DELIVERY_DATE>
                        <STATUS>1</STATUS>
                        <SELER_UN_ID>{seller_un_id}</SELER_UN_ID>
                        <PAR_ID>0</PAR_ID>
                        <CAR_NUMBER>AA-123-BB</CAR_NUMBER>
                        <BEGIN_DATE>{begin_date}</BEGIN_DATE>
                        <TRAN_COST_PAYER>1</TRAN_COST_PAYER>
                        <TRANS_ID>1</TRANS_ID>
                        <TRANS_TXT></TRANS_TXT>
                        <COMMENT>ტესტი მძღოლით</COMMENT>
                        <TRANSPORTER_TIN></TRANSPORTER_TIN>
                    </WAYBILL>
                </waybill>
            </save_waybill>
        </soap:Body>
    </soap:Envelope>"""
    
    print("\n[SENDING] Distribution waybill WITH driver info...")
    
    url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "http://tempuri.org/save_waybill"
    }
    
    try:
        response = requests.post(url, data=waybill_xml.encode('utf-8'), headers=headers, timeout=30)
        print(f"[INFO] Response Status: {response.status_code}")
        
        # Check for STATUS in response
        if '<STATUS>' in response.text:
            status = response.text.split('<STATUS>')[1].split('</STATUS>')[0]
            print(f"[INFO] Waybill STATUS: {status}")
            
            if int(status) >= 0:
                print("[OK] SUCCESS - Distribution WITH driver accepted!")
                # Extract waybill ID
                if '<ID>' in response.text:
                    wb_id = response.text.split('<ID>')[1].split('</ID>')[0]
                    print(f"[OK] Waybill ID: {wb_id}")
                    return True, wb_id
            else:
                print(f"[FAIL] Error code: {status}")
                return False, status
        
        print(f"[INFO] Full response:\n{response.text[:500]}")
        return False, None
        
    except Exception as e:
        print(f"[FAIL] Exception: {str(e)}")
        return False, None

def test_distribution_without_driver():
    """Test 2: Distribution WITHOUT driver info"""
    print_section("TEST 2: DISTRIBUTION WITHOUT DRIVER INFO")
    
    # First get seller un_id
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
    
    print(f"[INFO] Seller UN_ID: {seller_un_id}")
    
    # Now try to save distribution WITHOUT driver (empty fields)
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
                                <W_NAME>ტესტ პროდუქტი 2</W_NAME>
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
                        <BUYER_TIN>01008062291</BUYER_TIN>
                        <CHEK_BUYER_TIN>1</CHEK_BUYER_TIN>
                        <BUYER_NAME>ა. კ.</BUYER_NAME>
                        <START_ADDRESS>თბილისი</START_ADDRESS>
                        <END_ADDRESS>თბილისი</END_ADDRESS>
                        <DRIVER_TIN></DRIVER_TIN>
                        <CHEK_DRIVER_TIN>1</CHEK_DRIVER_TIN>
                        <DRIVER_NAME></DRIVER_NAME>
                        <TRANSPORT_COAST>0</TRANSPORT_COAST>
                        <RECEPTION_INFO></RECEPTION_INFO>
                        <RECEIVER_INFO></RECEIVER_INFO>
                        <DELIVERY_DATE></DELIVERY_DATE>
                        <STATUS>1</STATUS>
                        <SELER_UN_ID>{seller_un_id}</SELER_UN_ID>
                        <PAR_ID>0</PAR_ID>
                        <CAR_NUMBER></CAR_NUMBER>
                        <BEGIN_DATE>{begin_date}</BEGIN_DATE>
                        <TRAN_COST_PAYER>1</TRAN_COST_PAYER>
                        <TRANS_ID>1</TRANS_ID>
                        <TRANS_TXT></TRANS_TXT>
                        <COMMENT>ტესტი მძღოლის გარეშე</COMMENT>
                        <TRANSPORTER_TIN></TRANSPORTER_TIN>
                    </WAYBILL>
                </waybill>
            </save_waybill>
        </soap:Body>
    </soap:Envelope>"""
    
    print("\n[SENDING] Distribution waybill WITHOUT driver info (empty fields)...")
    print("[INFO] DRIVER_TIN: (empty)")
    print("[INFO] DRIVER_NAME: (empty)")
    print("[INFO] CAR_NUMBER: (empty)")
    
    url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "http://tempuri.org/save_waybill"
    }
    
    try:
        response = requests.post(url, data=waybill_xml.encode('utf-8'), headers=headers, timeout=30)
        print(f"[INFO] Response Status: {response.status_code}")
        
        # Check for STATUS in response
        if '<STATUS>' in response.text:
            status = response.text.split('<STATUS>')[1].split('</STATUS>')[0]
            print(f"[INFO] Waybill STATUS: {status}")
            
            if int(status) >= 0:
                print("[OK] SUCCESS - Distribution WITHOUT driver accepted!")
                # Extract waybill ID
                if '<ID>' in response.text:
                    wb_id = response.text.split('<ID>')[1].split('</ID>')[0]
                    print(f"[OK] Waybill ID: {wb_id}")
                    return True, wb_id
            else:
                print(f"[FAIL] Error code: {status}")
                print("[INFO] Driver fields might be REQUIRED for TYPE 4")
                return False, status
        
        print(f"[INFO] Full response:\n{response.text[:500]}")
        return False, None
        
    except Exception as e:
        print(f"[FAIL] Exception: {str(e)}")
        return False, None

def main():
    """Run distribution driver tests"""
    print_section("RS.GE TYPE 4 (DISTRIBUTION) - DRIVER REQUIREMENT TEST")
    
    print("\n[QUESTION] Are driver fields required for TYPE 4 (დისტრიბუცია)?")
    print("[METHOD] Testing with and without driver information...\n")
    
    # Test 1: With driver
    test1_success, test1_result = test_distribution_with_driver()
    
    print()
    
    # Test 2: Without driver  
    test2_success, test2_result = test_distribution_without_driver()
    
    # Summary
    print_section("CONCLUSION")
    
    print(f"\n[1] Distribution WITH driver: {'[OK] PASSED' if test1_success else '[FAIL] FAILED'}")
    if test1_result:
        print(f"    Result: {test1_result}")
    
    print(f"\n[2] Distribution WITHOUT driver: {'[OK] PASSED' if test2_success else '[FAIL] FAILED'}")
    if test2_result:
        print(f"    Result: {test2_result}")
    
    print("\n[ANSWER]")
    if test1_success and test2_success:
        print("*** Driver fields are OPTIONAL for TYPE 4 (დისტრიბუცია) ***")
        print("*** You can upload distribution waybills WITHOUT driver info! ***")
    elif test1_success and not test2_success:
        print("*** Driver fields are REQUIRED for TYPE 4 (დისტრიბუცია) ***")
        print("*** You must provide driver information even for distribution! ***")
    else:
        print("*** Both tests failed - check credentials or waybill structure ***")
    
    return 0 if (test1_success or test2_success) else 1

if __name__ == "__main__":
    exit(main())

