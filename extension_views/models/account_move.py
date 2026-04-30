import requests
import xml.etree.ElementTree as ET
import logging
from datetime import datetime, timezone, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    status = fields.Char('Status')
    combined_invoice_id = fields.Many2one('combined.invoice.model', string='Combined Invoice Model')
    invoice_number = fields.Char(related='combined_invoice_id.invoice_number', string='ზედნადების ნომერი')
    invoice_id = fields.Char(related='combined_invoice_id.invoice_id', string='ზედნადების ID')
    factura_num = fields.Char(related='combined_invoice_id.factura_num', string='ფაქტურის id')
    get_invoice_id = fields.Char(related='combined_invoice_id.get_invoice_id', string='ფაქტურის ნომერი')
    start_location = fields.Char('ტრანსპორტირების დაწყების ადგილი')
    end_location = fields.Char('ტრანსპორტირების დასრულების ადგილი')
    editable_end_location = fields.Char('ტრანსპორტირების დასრულების ადგილი')
    error_field = fields.Char('error_field')
    
    delivery = fields.Selection([
        ('2', 'მიწოდება ტრანსპორტირებით'),
        ('3', 'ტრანსპორტირების გარეშე'),
    ], 'მიწოდების სახე', default='2')
    
    trans_id = fields.Selection([
        ('1', 'საავტომობილო'),
        ('2', 'სარკინიგზო'),
        ('3', 'საავიაციო'),
        ('4', 'სხვა'),
        ('6', 'საავტომობილო - უცხო ქვეყნის'),
        ('7', 'გადამზიდავი'),
        ('8', 'მოპედი/მოტოციკლი'),
    ], string='ტრანსპორტირების სახე', default='1')

    trans_txt = fields.Char('ტრანსპორტირების ტექსტი')
    is_trans_id_4 = fields.Boolean(compute='_compute_is_trans_id_4')

    buyer_type = fields.Selection([
        ('1', 'საქართველოს მოქალაქე'),
        ('0', 'უცხოეთის მოქალაქე'),
    ], string='მყიდველი', default='1')

    driver_type = fields.Selection([
        ('1', 'საქართველოს მოქალაქე'),
        ('0', 'უცხოეთის მოქალაქე'),
    ], string='მძღოლის ტიპი', default='1')
    
    car_number = fields.Char('მანქანის ნომერი')
    driver_id = fields.Char('მძღოლის პირადი ნომერი')
    driver_name = fields.Char('მძღოლის სახელი')
    transport_cost = fields.Float('ტრანსპორტირების ღირებულება')
    transport_cost_payer = fields.Selection([
        ('1', 'მყიდველი'),
        ('2', 'გამყიდველი'),
    ], string='ტრანსპორტირების ღირებულების გადამხდელი', default='1')
    
    comment = fields.Text('კომენტარი')
    product_comment = fields.Char(string='სერვისის აღწერა')
    rs_acc = fields.Char(compute='_compute_rs_acc', string='rs.ge ექაუნთი', readonly=True)
    rs_pass = fields.Char(compute='_compute_rs_pass', string='rs.ge პაროლი', readonly=True)
    partner_vat = fields.Char(related='partner_id.vat', string='Customer VAT', readonly=True, store=True)
    completed_soap = fields.Char(string='გაგზავნილია')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    warehouse_address = fields.Char(related='warehouse_id.partner_id.name', string='Warehouse Address', readonly=True)
    begin_date = fields.Datetime(string='დაწყების დრო', default=fields.Datetime.now)
    show_all_fields = fields.Boolean(string='რს-ის ველები')
    extracted_data = fields.Text(string='Extracted Data')
    is_soap_completed = fields.Boolean(compute='_compute_is_soap_completed')
    formatted_begin_date = fields.Char(compute='_compute_formatted_begin_date', string='Formatted Begin Date')

    @api.depends('trans_id')
    def _compute_is_trans_id_4(self):
        for record in self:
            record.is_trans_id_4 = record.trans_id == '4'

    @api.depends('begin_date')
    def _compute_formatted_begin_date(self):
        for record in self:
            if record.begin_date:
                begin_date_datetime = fields.Datetime.from_string(record.begin_date)
                record.formatted_begin_date = begin_date_datetime.strftime("%Y-%m-%dT%H:%M:%S")

    @api.depends('completed_soap')
    def _compute_is_soap_completed(self):
        for record in self:
            record.is_soap_completed = record.completed_soap == '1'

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.end_location = self.partner_id.street
            if not self.editable_end_location:
                self.editable_end_location = self.partner_id.street

    @api.onchange('delivery')
    def _onchange_delivery(self):
        if self.delivery == '3':
            self.start_location = self.editable_end_location

    @api.depends('user_id.rs_acc')
    def _compute_rs_acc(self):
        for record in self:
            user = self.env.user
            record.rs_acc = user.rs_acc

    @api.depends('user_id.rs_pass')
    def _compute_rs_pass(self):
        for record in self:
            user = self.env.user
            record.rs_pass = user.rs_pass

    @api.onchange('driver_id')
    def get_driver_name(self):
        if self.driver_id:
            self.driver_name = self.get_name_from_tin(self.rs_acc, self.rs_pass, self.driver_id)

    # ============================================================================
    # SOAP METHODS
    # ============================================================================

    def _safe_soap_request(self, url, soap_body, headers, service_name="API"):
        try:
            _logger.info(f'=== {service_name} REQUEST ===')
            _logger.info(f'URL: {url}')
            _logger.info(f'Body: {soap_body[:500]}...' if len(soap_body) > 500 else f'Body: {soap_body}')
            
            response = requests.post(
                url, 
                data=soap_body.encode('utf-8'), 
                headers=headers,
                timeout=60
            )
            
            _logger.info(f'{service_name} Response Status: {response.status_code}')
            _logger.info(f'{service_name} Response: {response.text[:500]}...' if len(response.text) > 500 else f'{service_name} Response: {response.text}')
            
            if response.status_code != 200:
                error_msg = f"HTTP შეცდომა {response.status_code}: {response.text[:200]}"
                return False, response.text, error_msg
            
            if 'soap:Fault' in response.text or 'faultstring' in response.text:
                try:
                    root = ET.fromstring(response.text)
                    fault_string = root.find('.//{http://schemas.xmlsoap.org/soap/envelope/}Body/{http://schemas.xmlsoap.org/soap/envelope/}Fault/faultstring')
                    if fault_string is not None:
                        error_msg = f"SOAP შეცდომა: {fault_string.text}"
                        return False, response.text, error_msg
                except:
                    pass
                error_msg = "SOAP შეცდომა დაფიქსირდა"
                return False, response.text, error_msg
            
            return True, response.text, None
            
        except requests.exceptions.Timeout:
            error_msg = f"{service_name}: დროის ლიმიტი ამოიწურა (60 წამი)"
            _logger.error(error_msg)
            return False, None, error_msg
            
        except requests.exceptions.ConnectionError:
            error_msg = f"{service_name}: კავშირის შეცდომა - შეამოწმეთ ინტერნეტი"
            _logger.error(error_msg)
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"{service_name}: {str(e)}"
            _logger.exception(f"Unexpected error in {service_name}")
            return False, None, error_msg

    def _parse_xml_response(self, response_text, xpath, namespaces=None):
        if namespaces is None:
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns': 'http://tempuri.org/'
            }
        
        try:
            root = ET.fromstring(response_text)
            element = root.find(xpath, namespaces)
            return element.text if element is not None else None
        except Exception as e:
            _logger.error(f"XML parsing error: {str(e)}")
            return None

    def _get_error_text_from_code(self, rs_acc, rs_pass, error_code):
        try:
            soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
                           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                           xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                <soap:Body>
                    <get_error_codes xmlns="http://tempuri.org/">
                        <su>{rs_acc}</su>
                        <sp>{rs_pass}</sp>
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
            
            if response.status_code != 200:
                return f"HTTP შეცდომა {response.status_code}: {response.text[:200]}"
            
            root = ET.fromstring(response.content)
            error_dict = {}
            
            for error_code_elem in root.findall(".//ERROR_CODE"):
                id_elem = error_code_elem.find("ID")
                text_elem = error_code_elem.find("TEXT")
                if id_elem is not None and text_elem is not None:
                    error_dict[id_elem.text] = text_elem.text
            
            error_code_str = str(error_code)
            return error_dict.get(error_code_str, f"უცნობი შეცდომა: კოდი {error_code}")
            
        except Exception as e:
            _logger.exception("Error getting error codes from RS.GE")
            return f"შეცდომის კოდის მიღება ვერ მოხერხდა: {str(e)}"

    def get_name_from_tin(self, rs_acc, rs_pass, tin):
        soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <get_name_from_tin xmlns="http://tempuri.org/">
          <su>{rs_acc}</su>
          <sp>{rs_pass}</sp>
          <tin>{tin}</tin>
        </get_name_from_tin>
      </soap:Body>
    </soap:Envelope>"""

        url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_name_from_tin"
        }

        success, response_text, error_msg = self._safe_soap_request(
            url, soap_request, headers, f"get_name_from_tin(TIN:{tin})"
        )
        
        if not success:
            _logger.error(f"get_name_from_tin failed: {error_msg}")
            return f"შეცდომა: {error_msg}"
        
        name = self._parse_xml_response(
            response_text,
            './/ns:get_name_from_tinResult',
            {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 
             'ns': 'http://tempuri.org/'}
        )
        
        if not name:
            if '<get_name_from_tinResult>' in response_text:
                start_tag = "<get_name_from_tinResult>"
                end_tag = "</get_name_from_tinResult>"
                start_index = response_text.find(start_tag) + len(start_tag)
                end_index = response_text.find(end_tag)
                result = response_text[start_index:end_index].strip()
                
                if result.startswith('-'):
                    error_text = self._get_error_text_from_code(rs_acc, rs_pass, result)
                    _logger.error(f"get_name_from_tin error: {error_text}")
                    return f"შეცდომა: {error_text}"
                
                return result if result else "უცნობი"
            
            _logger.error("get_name_from_tin: Response empty")
            return "უცნობი (ცარიელი პასუხი)"
        
        _logger.info(f'✅ Name from TIN {tin}: {name}')
        return name

    def generate_goods_list_xml(self):
        goods_list_xml = "<GOODS_LIST>"

        for line in self.invoice_line_ids:
            product = line.product_id

            if not product:
                continue

            if product.type == 'service':
                continue

            quantity = line.quantity
            if quantity == 0:
                raise UserError("რაოდენობა ვერ იქნება ნულის ტოლი product: %s" % product.name)

            price_unit = line.price_total / quantity if quantity != 0 else 0
            amount = line.price_total
            barcode = product.barcode
            unit_id = product.unit_id
            tax_id = line.tax_ids[0].name if line.tax_ids else ''
            unit_txt = product.unit_txt

            vat_type = -1
            if tax_id == '18%':
                vat_type = 0
            elif tax_id == '0%':
                vat_type = 1

            goods_xml = f"""
                <GOODS>
                    <ID>0</ID>
                    <W_NAME>{product.name}</W_NAME>
                    <UNIT_ID>{unit_id}</UNIT_ID>
                    <UNIT_TXT>{unit_txt}</UNIT_TXT>
                    <QUANTITY>{quantity}</QUANTITY>
                    <PRICE>{price_unit}</PRICE>
                    <STATUS>1</STATUS>
                    <AMOUNT>{amount}</AMOUNT>
                    <BAR_CODE>{barcode}</BAR_CODE>
                    <A_ID>0</A_ID>
                    <VAT_TYPE>{vat_type}</VAT_TYPE>
                </GOODS>
            """
            goods_list_xml += goods_xml

        goods_list_xml += "</GOODS_LIST>"
        return goods_list_xml

    def send_soap_request(self):
        try:
            goods_list_xml = self.generate_goods_list_xml()
            _logger.info('Goods List XML: %s', goods_list_xml)

            buyer_type = self.buyer_type
            start_location = self.start_location
            end_location = self.end_location
            driver_id = self.driver_id
            driver_type = self.driver_type
            driver_name = self.get_name_from_tin(self.rs_acc, self.rs_pass, driver_id)
            self.driver_name = driver_name
            transport_cost = self.transport_cost
            car_number = self.car_number
            transport_cost_payer = self.transport_cost_payer
            trans_id = self.trans_id
            delivery = self.delivery
            editable_end_location = self.editable_end_location
            comment = self.comment
            trans_txt = self.trans_txt
            formatted_begin_date = self.formatted_begin_date
            buyer_name = self.partner_id.name
            buyer_tin = self.partner_vat
            rs_acc = self.rs_acc
            rs_pass = self.rs_pass

            url_check_service_user = "http://services.rs.ge/WayBillService/WayBillService.asmx"
            headers = {"Content-Type": "text/xml; charset=utf-8"}
            soap_body_check_service_user = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <chek_service_user xmlns="http://tempuri.org/">
                  <su>{rs_acc}</su>
                  <sp>{rs_pass}</sp>
                </chek_service_user>
              </soap:Body>
            </soap:Envelope>"""

            success, response_text, error_msg = self._safe_soap_request(url_check_service_user, soap_body_check_service_user, headers, "chek_service_user")
            if not success:
                raise UserError(f"Check service user failed: {error_msg}")

            seller_un_id = self._parse_xml_response(response_text, './/ns:un_id', {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 'ns': 'http://tempuri.org/'})
            if not seller_un_id:
                raise UserError("Unable to find 'un_id' in the response")

            url_save_waybill = "http://services.rs.ge/waybillservice/waybillservice.asmx"
            soap_request_save_waybill = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                <soap:Body>
                    <save_waybill xmlns="http://tempuri.org/">
                        <su>{rs_acc}</su>
                        <sp>{rs_pass}</sp>
                        <waybill>
                            <WAYBILL xmlns="">
                                {goods_list_xml}
                                <ID>0</ID>
                                <TYPE>{delivery}</TYPE>
                                <BUYER_TIN>{buyer_tin}</BUYER_TIN>
                                <CHEK_BUYER_TIN>{buyer_type}</CHEK_BUYER_TIN>
                                <BUYER_NAME>{buyer_name}</BUYER_NAME>
                                <START_ADDRESS>{start_location}</START_ADDRESS>
                                <END_ADDRESS>{editable_end_location}</END_ADDRESS>
                                <DRIVER_TIN>{driver_id}</DRIVER_TIN>
                                <CHEK_DRIVER_TIN>{driver_type}</CHEK_DRIVER_TIN>
                                <DRIVER_NAME>{driver_name}</DRIVER_NAME>
                                <TRANSPORT_COAST>{transport_cost}</TRANSPORT_COAST>
                                <RECEPTION_INFO></RECEPTION_INFO>
                                <RECEIVER_INFO></RECEIVER_INFO>
                                <DELIVERY_DATE></DELIVERY_DATE>
                                <STATUS>1</STATUS>
                                <SELER_UN_ID>{seller_un_id}</SELER_UN_ID>
                                <PAR_ID>0</PAR_ID>
                                <CAR_NUMBER>{car_number}</CAR_NUMBER>
                                <BEGIN_DATE>{formatted_begin_date}</BEGIN_DATE>
                                <TRAN_COST_PAYER>{transport_cost_payer}</TRAN_COST_PAYER>
                                <TRANS_ID>{trans_id}</TRANS_ID>
                                <TRANS_TXT>{trans_txt}</TRANS_TXT>
                                <COMMENT>{comment}</COMMENT>
                                <TRANSPORTER_TIN></TRANSPORTER_TIN>
                            </WAYBILL>
                        </waybill>
                    </save_waybill>
                </soap:Body>
            </soap:Envelope>"""

            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/save_waybill"
            }

            success, response_text, error_msg = self._safe_soap_request(url_save_waybill, soap_request_save_waybill, headers, "save_waybill")
            if not success:
                raise UserError(f"Save waybill failed: {error_msg}")

            if '<STATUS>' in response_text and '</STATUS>' in response_text:
                Status = response_text.split('<STATUS>')[1].split('</STATUS>')[0]
            else:
                raise UserError(f'Invalid response from server: No STATUS found')

            if Status >= '0':
                pass # Success
            elif Status < '0':
                error_text = self._get_error_text_from_code(rs_acc, rs_pass, Status)
                self.error_field = error_text
                raise UserError(error_text)

        except Exception as e:
            _logger.exception("Error occurred while sending SOAP request")
            raise UserError(f"Error: {e}")

    def button_send_soap_request(self):
        """Upload waybills - auto-detects single vs batch mode"""
        _logger.info(f'Executing button_send_soap_request for {len(self)} record(s)')
        
        if len(self) == 1:
            for record in self:
                if not record.invoice_id:
                    record.send_soap_request()
                else:
                    raise UserError('ზედნადები უკვე ატვირთლია')
        else:
            success_records = []
            error_records = []
            skipped_records = []
            
            for record in self:
                try:
                    if record.invoice_id:
                        skipped_records.append((record.name, 'ზედნადები უკვე ატვირთულია'))
                        continue
                        
                    record.send_soap_request()
                    success_records.append(record.name)
                    self.env.cr.commit()
                    
                except Exception as e:
                    error_records.append((record.name, str(e)))
                    self.env.cr.rollback()
                    _logger.exception(f"Error processing waybill {record.name}")
            
            messages = []
            if success_records:
                messages.append(f"✓ წარმატებით ატვირთულია ({len(success_records)}): {', '.join(success_records)}")
            if skipped_records:
                skipped_msg = '\n'.join([f"  - {name}: {reason}" for name, reason in skipped_records])
                messages.append(f"⊘ გამოტოვებულია ({len(skipped_records)}):\n{skipped_msg}")
            if error_records:
                error_msg = '\n'.join([f"  - {name}: {error}" for name, error in error_records])
                messages.append(f"✗ შეცდომები ({len(error_records)}):\n{error_msg}")
            
            final_message = '\n\n'.join(messages)
            
            if error_records and not success_records:
                raise UserError(final_message)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('ზედნადებების ატვირთვა დასრულდა'),
                    'message': final_message,
                    'type': 'success' if not error_records else 'warning',
                    'sticky': True,
                }
            }

    def check_seller_and_service_user_id(self, rs_acc, rs_pass):
        _logger.info('Starting check_seller_and_service_user_id')
        url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
        }

        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
                <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                  <soap:Body>
                    <chek_service_user xmlns="http://tempuri.org/">
                      <su>{rs_acc}</su>
                      <sp>{rs_pass}</sp>
                    </chek_service_user>
                  </soap:Body>
                </soap:Envelope>"""

        response = requests.post(url, data=soap_body, headers=headers)
        _logger.info('SOAP Request to RS service:', response.text)  # _logger.infoing SOAP response for debugging
        root = ET.fromstring(response.text)

        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
        }

        un_id_element = root.find('.//ns:un_id', namespaces)
        if un_id_element is not None:
            seller_un_id = un_id_element.text
        else:
            raise UserError("Unable to find 'un_id' in the response")
        _logger.info(seller_un_id)

        url = "https://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {"Content-Type": "application/soap+xml; charset=utf-8"}

        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
                <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
                  <soap12:Body>
                    <chek xmlns="http://tempuri.org/">
                      <su>{rs_acc}</su>
                      <sp>{rs_pass}</sp>
                      <user_id>{seller_un_id}</user_id>
                    </chek>
                  </soap12:Body>
                </soap12:Envelope>"""

        response = requests.post(url, data=soap_body, headers=headers)
        _logger.info('SOAP Request to Revenue service:', response.text)  # _logger.infoing SOAP response for debugging
        root = ET.fromstring(response.text)

        user_id_element = root.find('.//ns:user_id', namespaces)
        if user_id_element is not None:
            user_id = user_id_element.text
        else:
            raise UserError("Unable to find 'user_id' in the response")
        _logger.info(seller_un_id, user_id)
        return seller_un_id, user_id

    def rs_un_id(self, rs_acc, rs_pass):
        url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
        }

        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
                        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                          <soap:Body>
                            <chek_service_user xmlns="http://tempuri.org/">
                              <su>{rs_acc}</su>
                              <sp>{rs_pass}</sp>
                            </chek_service_user>
                          </soap:Body>
                        </soap:Envelope>"""

        response = requests.post(url, data=soap_body, headers=headers)
        root = ET.fromstring(response.text)

        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
        }

        un_id_element = root.find('.//ns:un_id', namespaces)
        un_id = un_id_element.text if un_id_element is not None else None

        s_user_element = root.find('.//ns:s_user_id', namespaces)
        s_user_id = s_user_element.text if s_user_element is not None else None
        (_logger.info(un_id, s_user_id))

        return un_id, s_user_id

    def chek(self, rs_acc, rs_pass):
        un_id, s_user_id = self.rs_un_id(rs_acc, rs_pass)

        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/chek"
        }
        body = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <chek xmlns="http://tempuri.org/">
                  <su>{rs_acc}</su>
                  <sp>{rs_pass}</sp>
                  <user_id>{un_id}</user_id>
                </chek>
              </soap:Body>
            </soap:Envelope>"""

        response = requests.post(url, headers=headers, data=body)
        root = ET.fromstring(response.text)

        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
        }

        user_id_element = root.find('.//ns:user_id', namespaces)
        user_id = user_id_element.text if user_id_element is not None else None
        (_logger.info(user_id))
        return user_id

    def un_id_from_tin(self, rs_acc, rs_pass, tin):
        user_id = self.chek(rs_acc, rs_pass)

        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_un_id_from_tin"
        }
        body = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <get_un_id_from_tin xmlns="http://tempuri.org/">
                  <user_id>{user_id}</user_id>
                  <tin>{tin}</tin>
                  <su>{rs_acc}</su>
                  <sp>{rs_pass}</sp>
                </get_un_id_from_tin>
              </soap:Body>
            </soap:Envelope>
            """

        response = requests.post(url, headers=headers, data=body)
        root = ET.fromstring(response.text)
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
        }

        un_id_element = root.find('.//ns:get_un_id_from_tinResult', namespaces)
        name_element = root.find('.//ns:name', namespaces)
        un_id = un_id_element.text if un_id_element is not None else None
        saxeli = name_element.text if name_element is not None else None
        _logger.info(un_id, saxeli)
        return un_id

    def save_invoice_momsaxureba(self, rs_acc, rs_pass, tin):
        user_id = self.chek(rs_acc, rs_pass)
        un_id, s_user_id = self.rs_un_id(rs_acc, rs_pass)
        buyer_un_id = self.un_id_from_tin(rs_acc, rs_pass, tin)
        tz = timezone(timedelta(hours=4))
        now_with_tz = datetime.now(tz)
        if self.invoice_date:
             op_datetime = now_with_tz.replace(year=self.invoice_date.year, month=self.invoice_date.month, day=self.invoice_date.day)
        else:
             op_datetime = now_with_tz
        current_datetime = op_datetime.strftime('%Y-%m-%dT%H:%M:%S%z')
        formatted_datetime = f"{current_datetime[:-2]}:{current_datetime[-2:]}"  # Format as +04:00


        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/save_invoice_n"
        }
        
        # Get note from invoice narration or use empty string
        note = self.comment if self.comment else ""
        
        if note:
            # 1. Escape special XML characters
            note = note.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # 2. Convert non-ASCII (Georgian) chars to XML entities (e.g. &#4304;)
            note = note.encode('ascii', 'xmlcharrefreplace').decode('ascii')
        else:
            note = ""
        
        body = f"""<?xml version="1.0" encoding="utf-8"?>
                <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                  <soap:Body>
                    <save_invoice_n xmlns="http://tempuri.org/">
                      <user_id>{user_id}</user_id>
                      <invois_id>{self.factura_num if self.factura_num else 0}</invois_id>
                      <operation_date>{formatted_datetime}</operation_date>
                      <seller_un_id>{un_id}</seller_un_id>
                      <buyer_un_id>{buyer_un_id}</buyer_un_id>
                      <overhead_no></overhead_no>
                      <overhead_dt>{formatted_datetime}</overhead_dt>
                      <b_s_user_id>0</b_s_user_id>
                      <su>{rs_acc}</su>
                      <sp>{rs_pass}</sp>
                      <note>{note}</note>
                    </save_invoice_n>
                  </soap:Body>
                </soap:Envelope>"""

        response = requests.post(url, data=body.encode('utf-8'), headers=headers)
        
        # Log the response to debug errors
        _logger.info(f"save_invoice_n Response Status: {response.status_code}")
        _logger.info(f"save_invoice_n Response Body: {response.text}")
        
        if response.status_code != 200:
             raise UserError(f"RS.GE Error ({response.status_code}): {response.text[:200]}")

        root = ET.fromstring(response.text)
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
        }
        factura_num = root.find('.//ns:invois_id', namespaces)
        factura_num = factura_num.text if factura_num is not None else None
        _logger.info('Saved invoice with factura_num:', factura_num)
        return factura_num

    def save_invoice_desc_momsaxureba(self, rs_acc, rs_pass,factura_num):
        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/save_invoice_desc"
        }
        user_id = self.chek(rs_acc, rs_pass)

        _logger.info('Generating goods list XML and sending SOAP requests')
        # Define the unit_id dictionary
        unit_id_dict = {
            '1': 'ცალი',
            '2': 'კგ',
            '3': 'გრამი',
            '4': 'ლიტრი',
            '5': 'ტონა',
            '7': 'სანტიმეტრი',
            '8': 'მეტრი',
            '9': 'კილომეტრი',
            '10': 'კვ.სმ',
            '11': 'კვ.მ',
            '12': 'მ³',
            '13': 'მილილიტრი',
            '99': 'სხვა'
        }
        
        for index, line in enumerate(self.invoice_line_ids):
            # Use header-level product_comment if available, otherwise fallback to line.name
            product = self.product_comment if self.product_comment else line.name
            unit_txt = line.unit_txt
            quantity = line.quantity
            if quantity == 0:
                raise UserError("რაოდენობა ვერ იქნება ნულის ტოლი product: %s" % product)
            price_unit = line.price_unit
            amount = quantity * price_unit
            tax_id = line.tax_ids.name
        
            # Check if unit_id exists in the dictionary; if not, default to 'მომსახურება'
            unit_id = unit_id_dict.get(line.unit_id, 'მომსახურება')
        
            body = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <save_invoice_desc xmlns="http://tempuri.org/">
                  <user_id>{user_id}</user_id>
                  <id>0</id>
                  <su>{rs_acc}</su>
                  <sp>{rs_pass}</sp>
                  <invois_id>{factura_num}</invois_id>
                  <goods>{product}</goods>
                  <g_unit>{unit_id}</g_unit>
                  <g_number>{quantity}</g_number>
                  <full_amount>{amount}</full_amount>
                  <drg_amount>18</drg_amount>
                  <aqcizi_amount>0</aqcizi_amount>
                  <akciz_id>0</akciz_id>
                </save_invoice_desc>
              </soap:Body>
            </soap:Envelope>"""


            _logger.info(factura_num)
            _logger.info(body)

            # Send SOAP request
            response = requests.post(url, headers=headers, data=body.encode('utf-8'))
            root = ET.fromstring(response.text)
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
            }
            save_invoice_desc_id = root.find('.//ns:id', namespaces)
            if save_invoice_desc_id is not None:
                save_invoice_desc_id = save_invoice_desc_id.text
                _logger.info(f'Saved invoice description for product {index} with ID:', save_invoice_desc_id)
                _logger.info(save_invoice_desc_id)
            else:
                _logger.info(f'Failed to save invoice description for product {index}')

        return True  # Or handle success/failure as needed
    def change_status_invoice(self,rs_pass,rs_acc,factura_num):
        # Define the SOAP request
        seller_un_id, user_id = self.check_seller_and_service_user_id(rs_acc, rs_pass)

        soap_request = f'''<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <change_invoice_status xmlns="http://tempuri.org/">
                  <user_id>{user_id}</user_id>
                  <inv_id>{factura_num}</inv_id>
                  <status>1</status>
                  <su>{rs_acc}</su>
                  <sp>{rs_pass}</sp>
                </change_invoice_status>
              </soap:Body>
            </soap:Envelope>'''


        # Define the headers
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'Content-Length': str(len(soap_request)),
            'SOAPAction': '"http://tempuri.org/change_invoice_status"'
        }

        # Send the request
        response = requests.post('http://www.revenue.mof.ge/ntosservice/ntosservice.asmx', data=soap_request, headers=headers)
        # Define the SOAP request
    def generate_goods_list_xml_1(self, line):
        """Generate XML for a single line item, skipping lines with unit_id or product_id"""
        # Skip if line has unit_id or product_id
        if line.unit_id or line.product_id:
            _logger.info(f'Skipping line with unit_id or product_id: {line.name}')
            return None
            
        if not line.name:
            return None
                
        quantity = line.quantity
        if quantity == 0:
            raise UserError("რაოდენობა ვერ იქნება ნულის ტოლი product: %s" % (line.product_id.name if line.product_id else line.name))
            
        price_unit = line.price_unit
        amount = quantity * price_unit
            
        momsaxureba_xml = f"""
            <goods>{line.name}</goods>
            <g_unit>მომსახურება</g_unit>
            <g_number>{quantity}</g_number>
            <full_amount>{amount}</full_amount>
            <drg_amount>18</drg_amount>
            <aqcizi_amount>0</aqcizi_amount>
            <akciz_id>0</akciz_id>
        """
            
        _logger.info(f'Generated XML for line item: {line.name}')
        return momsaxureba_xml
    def _get_error_text(self, rs_acc, rs_pass, error_code):
        """Helper method to get error text from error code"""
        soap_request = f"""
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                <soap:Body>
                    <get_error_codes xmlns="http://tempuri.org/">
                        <su>{rs_acc}</su>
                        <sp>{rs_pass}</sp>
                    </get_error_codes>
                </soap:Body>
            </soap:Envelope>
        """
        
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_error_codes"
        }
        
        response = requests.post("http://services.rs.ge/waybillservice/waybillservice.asmx", 
                               data=soap_request, 
                               headers=headers)
        
        if response.status_code != 200:
            return f"Error getting error codes: {response.status_code}"
        
        root = ET.fromstring(response.content)
        error_dict = {}
        
        for error_code_elem in root.findall(".//ERROR_CODE"):
            id_value = error_code_elem.find("ID").text
            text_value = error_code_elem.find("TEXT").text
            error_dict[id_value] = text_value
        
        return error_dict.get(str(error_code), "Unknown error")

    def get_invoice(self, factura_num, rs_acc, rs_pass):
        user_id= self.chek(rs_acc, rs_pass)
        _logger.info(user_id)
        _logger.info(factura_num)
        _logger.info(rs_acc)
        _logger.info(rs_pass)
        # Define the SOAP request
        soap_request = f'''<?xml version="1.0" encoding="utf-8"?>
                <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
                  <soap12:Body>
                    <get_invoice xmlns="http://tempuri.org/">
                      <user_id>{user_id}</user_id>
                      <invois_id>{factura_num}</invois_id>
                      <su>{rs_acc}</su>
                      <sp>{rs_pass}</sp>
                    </get_invoice>
                  </soap12:Body>
                </soap12:Envelope>'''
        
        # Define the headers
        headers = {
            'Content-Type': 'application/soap+xml; charset=utf-8',
        }
        
        # Send the request
        response = requests.post('http://www.revenue.mof.ge/ntosservice/ntosservice.asmx', data=soap_request, headers=headers)
        
        
        
        # Define the headers
        headers = {
            'Content-Type': 'application/soap+xml; charset=utf-8',
            'Content-Length': str(len(soap_request)),
        }
        
        # Send the request
        response = requests.post('http://www.revenue.mof.ge/ntosservice/ntosservice.asmx', data=soap_request, headers=headers)
        
        # _logger.info the response
        response_content = response.content.decode('utf-8')
        # Extract the specific elements
        ns = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 'tempuri': 'http://tempuri.org/'}
        root = ET.fromstring(response_content)
        f_series_element = root.find('.//tempuri:f_series', ns)
        f_number_element = root.find('.//tempuri:f_number', ns)
        
        f_series_value = f_series_element.text if f_series_element is not None else ''
        f_number_value = f_number_element.text if f_number_element is not None else ''
        f_complete = f"{f_series_value} {f_number_value}"
        return f_complete

    def faqturebi(self):
        _logger.info('Executing faqturebi method')
        
        buyer_tin = self.partner_id.vat
        rs_acc = self.rs_acc
        rs_pass = self.rs_pass
        invoice_id = self.invoice_id
        
        if invoice_id:
               
                
            # Get user_id first
            user_id = self.chek(rs_acc, rs_pass)
            
            # First SOAP call to save_invoice
            soap_request = f"""
                <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                  <soap:Body>
                    <save_invoice xmlns="http://tempuri.org/">
                      <su>{rs_acc}</su>
                      <sp>{rs_pass}</sp>
                      <waybill_id>{invoice_id}</waybill_id>
                      <in_inv_id>0</in_inv_id>
                    </save_invoice>
                  </soap:Body>
                </soap:Envelope>
            """
            
            url = 'http://services.rs.ge/WayBillService/WayBillService.asmx'
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'http://tempuri.org/save_invoice',
            }
            
            response = requests.post(url, data=soap_request, headers=headers)
            _logger.info('SOAP Request to save invoice:', response.text)
            
            root = ET.fromstring(response.text)
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'tempuri': 'http://tempuri.org/'
            }
            
            out_inv_id_element = root.find('.//tempuri:out_inv_id', namespaces)
            if out_inv_id_element is None:
                raise UserError("Unable to find 'out_inv_id' in the response")
            
            out_inv_id = out_inv_id_element.text
            _logger.info(f'Got out_inv_id: {out_inv_id}')
            
            save_invoiceResult = int(root.find('.//tempuri:save_invoiceResult', namespaces).text)
            
            # Handle error codes if needed
            if save_invoiceResult < 0:
                error_text = self._get_error_text(rs_acc, rs_pass, save_invoiceResult)
                _logger.error(f'Error saving invoice: {error_text}')
                raise UserError(error_text)
            
            # Process each line item separately
            for line in self.invoice_line_ids:
                momsaxureba_xml = self.generate_goods_list_xml_1(line)
                if not momsaxureba_xml:
                    continue
                    
                # Send individual SOAP request for each line
                soap_request = f"""
                    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                                  xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
                                  xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                      <soap:Body>
                        <save_invoice_desc xmlns="http://tempuri.org/">
                          <user_id>{user_id}</user_id>
                          <id>0</id>
                          <su>{rs_acc}</su>
                          <sp>{rs_pass}</sp>
                          <invois_id>{out_inv_id}</invois_id>
                          {momsaxureba_xml}
                        </save_invoice_desc>
                      </soap:Body>
                    </soap:Envelope>
                """
                
                _logger.info(f'Sending SOAP request for line item: {line.name}')
                url = 'http://www.revenue.mof.ge/ntosservice/ntosservice.asmx'
                headers = {
                    'Content-Type': 'text/xml; charset=utf-8',
                    'SOAPAction': 'http://tempuri.org/save_invoice_desc',
                }
                
                response = requests.post(url, data=soap_request.encode('utf-8'), headers=headers)
                _logger.info(f'Response for line item {line.name}: {response.text}')
            
            # Update status and related records
            factura_num = out_inv_id
            change_status_invoice = self.change_status_invoice(rs_pass, rs_acc, factura_num)
            
            combined_invoice = self.combined_invoice_id
            combined_invoice.write({'factura_num': factura_num})
            
            get_invoice = self.get_invoice(out_inv_id, rs_acc, rs_pass)
            combined_invoice.write({'get_invoice_id': get_invoice})
            
            _logger.info(f'Completed processing invoice with factura_num: {factura_num}')


        else:
            factura_num = self.save_invoice_momsaxureba(rs_acc, rs_pass, buyer_tin)
            _logger.info('Saved invoice with factura_num:', factura_num)

            # Save invoice description
            self.save_invoice_desc_momsaxureba(rs_acc, rs_pass, factura_num)
            
            _logger.info('Created new combined invoice record with factura_num:', factura_num)
            change_status_invoice = self.change_status_invoice(rs_pass, rs_acc, factura_num)
            get_invoice = self.get_invoice(factura_num, rs_acc, rs_pass)
                        # Create a new combined.invoice.model record
            new_invoice = self.env['combined.invoice.model'].create({
                'factura_num': factura_num,  # Assigning the factura_num obtained
                # Add any other fields you need to set for this record
                'get_invoice_id': get_invoice,
            })
            # Update the combined_invoice_id on this sale order if needed
            self.combined_invoice_id = new_invoice.id

            ###write to invoice



    def button_factura(self):
        _logger.info('Executing button_factura method')
        for record in self:
            if not record.factura_num:  # Check if factura_num is empty
                record.faqturebi()
            else:
                raise UserError('ფაქტურა უკვე ატვირთულია')
        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
                <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                  <soap:Body>
                    <chek_service_user xmlns="http://tempuri.org/">
                      <su>{rs_acc}</su>
                      <sp>{rs_pass}</sp>
                    </chek_service_user>
                  </soap:Body>
                </soap:Envelope>"""
        
        headers = {"Content-Type": "text/xml; charset=utf-8"}
        
        success, response_text, error_msg = self._safe_soap_request(
            url, soap_body, headers, "chek_service_user"
        )
        
        if not success:
            raise UserError(f"RS.GE ავტორიზაცია ვერ მოხერხდა: {error_msg}")
        
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'
        }
        
        seller_un_id = self._parse_xml_response(response_text, './/ns:un_id', namespaces)
        
        if not seller_un_id:
            error_code = self._parse_xml_response(response_text, './/ns:error', namespaces)
            if error_code:
                error_text = self._get_error_text_from_code(rs_acc, rs_pass, error_code)
                raise UserError(f"RS.GE ავტორიზაცია ვერ მოხერხდა: {error_text}")
            raise UserError("un_id ვერ მოიძებნა RS.GE პასუხში")
        
        _logger.info(f'Seller UN ID: {seller_un_id}')
        
        url = "https://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
                <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
                  <soap12:Body>
                    <chek xmlns="http://tempuri.org/">
                      <su>{rs_acc}</su>
                      <sp>{rs_pass}</sp>
                      <user_id>{seller_un_id}</user_id>
                    </chek>
                  </soap12:Body>
                </soap12:Envelope>"""
        
        headers = {"Content-Type": "application/soap+xml; charset=utf-8"}
        
        success, response_text, error_msg = self._safe_soap_request(
            url, soap_body, headers, "chek(Revenue)"
        )
        
        if not success:
            raise UserError(f"Revenue სერვისი: ავტორიზაცია ვერ მოხერხდა: {error_msg}")
        
        user_id = self._parse_xml_response(response_text, './/ns:user_id', namespaces)
        
        if not user_id:
            raise UserError("user_id ვერ მოიძებნა Revenue სერვისის პასუხში")
        
        _logger.info(f'✅ Seller UN ID: {seller_un_id}, User ID: {user_id}')
        return seller_un_id, user_id

    def rs_un_id(self, rs_acc, rs_pass):
        url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
        }

        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
                        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                          <soap:Body>
                            <chek_service_user xmlns="http://tempuri.org/">
                              <su>{rs_acc}</su>
                              <sp>{rs_pass}</sp>
                            </chek_service_user>
                          </soap:Body>
                        </soap:Envelope>"""

        response = requests.post(url, data=soap_body, headers=headers)
        root = ET.fromstring(response.text)

        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'
        }

        un_id_element = root.find('.//ns:un_id', namespaces)
        un_id = un_id_element.text if un_id_element is not None else None

        s_user_element = root.find('.//ns:s_user_id', namespaces)
        s_user_id = s_user_element.text if s_user_element is not None else None

        return un_id, s_user_id

    def chek(self, rs_acc, rs_pass):
        un_id, s_user_id = self.rs_un_id(rs_acc, rs_pass)

        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/chek"
        }
        body = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <chek xmlns="http://tempuri.org/">
                  <su>{rs_acc}</su>
                  <sp>{rs_pass}</sp>
                  <user_id>{un_id}</user_id>
                </chek>
              </soap:Body>
            </soap:Envelope>"""

        success, response_text, error_msg = self._safe_soap_request(
            url, body, headers, "chek(Revenue)"
        )
        
        if not success:
            raise UserError(f"Revenue ავტორიზაცია ვერ მოხერხდა: {error_msg}")

        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'
        }

        user_id = self._parse_xml_response(response_text, './/ns:user_id', namespaces)
        
        if not user_id:
            raise UserError("user_id ვერ მოიძებნა Revenue პასუხში")
        
        _logger.info(f'✅ Revenue User ID: {user_id}')
        return user_id

    def un_id_from_tin(self, rs_acc, rs_pass, tin):
        user_id = self.chek(rs_acc, rs_pass)

        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_un_id_from_tin"
        }
        body = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <get_un_id_from_tin xmlns="http://tempuri.org/">
                  <user_id>{user_id}</user_id>
                  <tin>{tin}</tin>
                  <su>{rs_acc}</su>
                  <sp>{rs_pass}</sp>
                </get_un_id_from_tin>
              </soap:Body>
            </soap:Envelope>
            """

        success, response_text, error_msg = self._safe_soap_request(
            url, body, headers, f"get_un_id_from_tin(TIN:{tin})"
        )
        
        if not success:
            raise UserError(f"UN ID-ს მიღება ვერ მოხერხდა: {error_msg}")

        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'
        }

        un_id = self._parse_xml_response(response_text, './/ns:get_un_id_from_tinResult', namespaces)
        saxeli = self._parse_xml_response(response_text, './/ns:name', namespaces)
        
        if not un_id:
            raise UserError(f"UN ID ვერ მოიძებნა TIN-ისთვის: {tin}")
        
        _logger.info(f'✅ UN ID from TIN {tin}: {un_id}, Name: {saxeli}')
        return un_id

    def get_invoice(self, factura_num, rs_acc, rs_pass):
        user_id = self.chek(rs_acc, rs_pass)
        
        soap_request = f'''<?xml version="1.0" encoding="utf-8"?>
                <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
                  <soap12:Body>
                    <get_invoice xmlns="http://tempuri.org/">
                      <user_id>{user_id}</user_id>
                      <invois_id>{factura_num}</invois_id>
                      <su>{rs_acc}</su>
                      <sp>{rs_pass}</sp>
                    </get_invoice>
                  </soap12:Body>
                </soap12:Envelope>'''

        headers = {
            'Content-Type': 'application/soap+xml; charset=utf-8',
            'Content-Length': str(len(soap_request)),
        }

        url = 'http://www.revenue.mof.ge/ntosservice/ntosservice.asmx'
        
        success, response_text, error_msg = self._safe_soap_request(
            url, soap_request, headers, f"get_invoice({factura_num})"
        )
        
        if not success:
            raise UserError(f"ფაქტურის მონაცემების მიღება ვერ მოხერხდა: {error_msg}")

        ns = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 'tempuri': 'http://tempuri.org/'}
        
        f_series = self._parse_xml_response(response_text, './/tempuri:f_series', ns)
        f_number = self._parse_xml_response(response_text, './/tempuri:f_number', ns)

        f_series_value = f_series if f_series else ''
        f_number_value = f_number if f_number else ''
        f_complete = f"{f_series_value} {f_number_value}".strip()
        
        if not f_complete:
            raise UserError(f"ფაქტურის ნომერი ვერ მოიძებნა: {factura_num}")
        
        _logger.info(f'✅ Invoice retrieved: {f_complete} for factura_num: {factura_num}')
        return f_complete

    def generate_goods_list_xml_1(self, line):
        if line.unit_id or line.product_id:
            _logger.info(f'Skipping line with unit_id or product_id: {line.name}')
            return None

        if not line.name:
            return None

        quantity = line.quantity
        if quantity == 0:
            raise UserError("რაოდენობა ვერ იქნება ნულის ტოლი product: %s" % (line.product_id.name if line.product_id else line.name))

        # Use header-level product_comment if available, otherwise fallback to product name
        if self.product_comment:
            product_name = self.product_comment
        else:
            product_name = line.product_id.name if line.product_id else line.name

        price_unit = line.price_unit
        amount = quantity * price_unit

        momsaxureba_xml = f"""
            <goods>{product_name}</goods>
            <g_unit>მომსახურება</g_unit>
            <g_number>{quantity}</g_number>
            <full_amount>{amount}</full_amount>
            <drg_amount>18</drg_amount>
            <aqcizi_amount>0</aqcizi_amount>
            <akciz_id>0</akciz_id>
        """

        _logger.info(f'Generated XML for line item: {product_name}')
        return momsaxureba_xml

    def _get_error_text(self, rs_acc, rs_pass, error_code):
        soap_request = f"""
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                <soap:Body>
                    <get_error_codes xmlns="http://tempuri.org/">
                        <su>{rs_acc}</su>
                        <sp>{rs_pass}</sp>
                    </get_error_codes>
                </soap:Body>
            </soap:Envelope>
        """

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_error_codes"
        }

        response = requests.post("http://services.rs.ge/waybillservice/waybillservice.asmx",
                                 data=soap_request,
                                 headers=headers)

        if response.status_code != 200:
            return f"Error getting error codes: {response.status_code}"

        root = ET.fromstring(response.content)
        error_dict = {}

        for error_code_elem in root.findall(".//ERROR_CODE"):
            id_value = error_code_elem.find("ID").text
            text_value = error_code_elem.find("TEXT").text
            error_dict[id_value] = text_value

        return error_dict.get(str(error_code), "Unknown error")

    def send_soap_request_return(self):
        # Placeholder or implementation if available. 
        # Assuming it's similar to send_soap_request but for returns or different logic.
        # If not found in source, I'll leave it as a pass or simple log.
        _logger.info("send_soap_request_return called")
        pass

    def button_factura(self):
        for record in self:
            record.faqturebi()

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    barcode = fields.Char(related='product_id.barcode', string="Barcode", store=True)
    unit_id = fields.Selection(related='product_id.unit_id', string="Unit", store=True)
    unit_txt = fields.Char(related='product_id.unit_txt', string="სხვა ერთეული", store=True)
    get_invoice_id = fields.Char(related='move_id.get_invoice_id', string='ფაქტურის ნომერი')
