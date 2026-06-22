import requests
import xml.etree.ElementTree as ET
import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from xml.sax.saxutils import escape

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Fields from extend_views.py
    transport_cost_payer = fields.Selection([
        ('1', 'მყიდველი'),
        ('2', 'გამყიდველი'),
    ], string='ტრანსპორტირების ღირებულების გადამხდელი', default='1')

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

    start_location = fields.Char('ტრანსპორტირების დაწყების ადგილი')
    end_location = fields.Char('ტრანსპორტირების დასრულების ადგილი')
    editable_end_location = fields.Char('ტრანსპორტირების დასრულების ადგილი')
    
    delivery = fields.Selection([
        ('2', 'მიწოდება ტრანსპორტირებით'),
        ('3', 'ტრანსპორტირების გარეშე'),
        ('4', 'დისტრიბუცია'),
        ('6', 'ქვე-ზედნადები'),
    ], 'მიწოდების სახე', default='2')

    car_number = fields.Char('მანქანის ნომერი')
    driver_id = fields.Char('მძღოლის პირადი ნომერი')
    driver_name = fields.Char('მძღოლის სახელი')
    transporter_tin = fields.Char('გადამზიდავის პირადი ნომერი')
    sub_waybill_parent_id = fields.Many2one('stock.picking', string='მშობელი ზედნადები', domain="[('delivery', '=', '4')]")
    transport_cost = fields.Float('ტრანსპორტირების ღირებულება')
    comment = fields.Text('კომენტარი')
    return_id = fields.Many2one('stock.picking', string='Return Picking')
    
    rs_acc = fields.Char(compute='_compute_rs_acc', string='rs.ge ექაუნთი', readonly=True)
    rs_pass = fields.Char(compute='_compute_rs_pass', string='rs.ge პაროლი', readonly=True)
    
    partner_vat = fields.Char(related='partner_id.vat', string='Customer VAT', readonly=True, store=True)
    
    combined_invoice_id = fields.Many2one('combined.invoice.model', string='Combined Invoice Model', compute='_compute_combined_invoice_id', store=True)
    invoice_number = fields.Char(related='combined_invoice_id.invoice_number', string='ზედნადების ნომერი', store=True)
    invoice_id = fields.Char(related='combined_invoice_id.invoice_id', string='ზედნადების ID', store=True)
    factura_num = fields.Char(related='combined_invoice_id.factura_num', string='ფაქტურის id')
    get_invoice_id = fields.Char(related='combined_invoice_id.get_invoice_id', string='ფაქტურის ნომერი')
    
    completed_soap = fields.Char(string='გაგზავნილია')
    is_soap_completed = fields.Boolean(compute='_compute_is_soap_completed')
    
    begin_date = fields.Datetime(string='დაწყების დრო', default=fields.Datetime.now)
    formatted_begin_date = fields.Char(compute='_compute_formatted_begin_date', string='Formatted Begin Date')
    
    field5 = fields.Char('Field 5') # From sale_soap.py
    company_review = fields.Char('Company Review') # From sale_soap.py
    show_all_fields = fields.Boolean(string='რს-ის ველები')
    is_start_location_required = fields.Boolean(string="Is Start Location Required", compute="_compute_is_start_location_required")
    is_editable_end_location_required = fields.Boolean(string="Is Editable End Location Required", compute="_compute_is_editable_end_location_required")
    error_field = fields.Char('error_field')
    rs_fasi = fields.Boolean(compute='_compute_rs_fasi', string='რს ფასის გადაცემა შიდა გადაზიდვაზე')

    @api.depends('user_id.rs_fasi')
    def _compute_rs_fasi(self):
        for record in self:
            user = self.env.user
            record.rs_fasi = user.rs_fasi

    @api.depends('trans_id')
    def _compute_is_trans_id_4(self):
        for record in self:
            record.is_trans_id_4 = record.trans_id == '4'

    @api.depends('origin')
    def _compute_combined_invoice_id(self):
        for picking in self:
            if picking.origin:
                sale_order = self.env['sale.order'].search([('name', '=', picking.origin)], limit=1)
                if sale_order:
                    self._copy_values_from_order(picking, sale_order)
                else:
                    purchase_order = self.env['purchase.order'].search([('name', '=', picking.origin)], limit=1)
                    if purchase_order:
                        self._copy_values_from_order(picking, purchase_order)

    def _copy_values_from_order(self, picking, order):
        picking.combined_invoice_id = order.combined_invoice_id
        picking.start_location = order.start_location
        picking.editable_end_location = order.editable_end_location
        picking.driver_id = order.driver_id
        picking.driver_name = order.driver_name
        picking.transport_cost = order.transport_cost
        picking.car_number = order.car_number
        picking.transport_cost_payer = order.transport_cost_payer
        picking.trans_id = order.trans_id
        picking.delivery = order.delivery
        picking.comment = order.comment
        picking.trans_txt = order.trans_txt
        picking.begin_date = order.begin_date
        picking.buyer_type = order.buyer_type
        picking.driver_type = order.driver_type

    @api.depends('delivery')
    def _compute_is_start_location_required(self):
        for record in self:
            record.is_start_location_required = record.delivery == '2'

    @api.depends('delivery')
    def _compute_is_editable_end_location_required(self):
        for record in self:
            record.is_editable_end_location_required = record.delivery == '2'

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
    def get_driver_name_onchange(self):
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

    def get_waybill(self, waybill_id, rs_acc, rs_pass):
        """Fetch waybill details from RS.GE to get existing goods IDs."""
        soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <get_waybill xmlns="http://tempuri.org/">
              <su>{rs_acc}</su>
              <sp>{rs_pass}</sp>
              <waybill_id>{waybill_id}</waybill_id>
            </get_waybill>
          </soap:Body>
        </soap:Envelope>"""

        url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_waybill"
        }

        success, response_text, error_msg = self._safe_soap_request(
            url, soap_request, headers, f"get_waybill({waybill_id})"
        )

        if not success:
            _logger.error(f"get_waybill failed: {error_msg}")
            return None

        return response_text

    def generate_goods_list_xml(self, existing_goods=None):
        goods_list_xml = "<GOODS_LIST>"
        existing_goods_map = {}
        
        if existing_goods:
            # Map existing goods by name to preserve IDs
            # Assuming existing_goods is a list of dicts with 'name' and 'id'
            for good in existing_goods:
                existing_goods_map[good.get('name')] = good.get('id')

        for move in self.move_ids_without_package:
            product = move.product_id
            if not product:
                continue

            if product.type == 'service':
                continue

            # Use rs_quantity if set, otherwise default to quantity (Done Qty)
            quantity = move.rs_quantity if hasattr(move, 'rs_quantity') and move.rs_quantity > 0 else move.quantity
            if quantity == 0:
                raise UserError("რაოდენობა ვერ იქნება ნულის ტოლი product: %s" % product.name)
            
            amount = move.cost_including_tax if hasattr(move, 'cost_including_tax') and move.cost_including_tax else (move.price_unit * quantity if move.price_unit else 0)
            barcode = product.barcode if product.barcode else ''

            unit_id = move.unit_id if hasattr(move, 'unit_id') else product.unit_id
            if not unit_id:
                raise UserError(_('დამატეთ rs.ge-ს ერთეული პროდუქციაზე'))
            
            tax_id = move.tax_id.name if hasattr(move, 'tax_id') and move.tax_id else ''
            vat_type = -1
            
            # Calculate price unit safely
            price_unit = (amount / quantity) if quantity else 0
            
            unit_txt = move.unit_txt if hasattr(move, 'unit_txt') else product.unit_txt

            if tax_id == '18%':
                vat_type = 0
            elif tax_id =='0%':
                vat_type = 1
            else:
                # Default to 0 or handle as error if strict
                pass 
            
            # Determine ID: use existing ID if found, else 0
            goods_id = existing_goods_map.get(product.name, '0')

            goods_xml = f"""
                <GOODS>
                    <ID>{goods_id}</ID>
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
        rs_acc = self.rs_acc
        rs_pass = self.rs_pass
        
        # Determine Waybill ID for creation (0) or correction (existing ID)
        waybill_id = self.invoice_id if self.invoice_id else '0'
        existing_goods = []

        if waybill_id != '0':
            # Fetch existing waybill details to get goods IDs
            response_text = self.get_waybill(waybill_id, rs_acc, rs_pass)
            if response_text:
                try:
                    root = ET.fromstring(response_text)
                    namespaces = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 'ns': 'http://tempuri.org/'}
                    # Adjust parsing based on actual response structure
                    # Assuming <GOODS><ID>...</ID><W_NAME>...</W_NAME></GOODS> inside <WAYBILL>
                    # Note: The response might be wrapped in get_waybillResult
                    
                    # We need to find all GOODS elements. 
                    # Since the structure can be nested, we'll search recursively for GOODS
                    # Be careful with namespaces.
                    
                    # Let's try to find GOODS_LIST or GOODS directly
                    # The response usually contains the full WAYBILL object
                    
                    goods_elements = root.findall('.//GOODS')
                    if not goods_elements:
                        # Try with namespace if needed, but usually inner XML might not have it or use default
                        goods_elements = root.findall('.//GOODS')
                    
                    for goods in goods_elements:
                        g_id = goods.find('ID')
                        w_name = goods.find('W_NAME')
                        if g_id is not None and w_name is not None:
                            existing_goods.append({
                                'id': g_id.text,
                                'name': w_name.text
                            })
                    _logger.info(f"Fetched existing goods for correction: {existing_goods}")
                except Exception as e:
                    _logger.warning(f"Failed to parse existing waybill goods: {e}")

        goods_list_xml = self.generate_goods_list_xml(existing_goods)
        _logger.info(f"Generated Goods List XML: {goods_list_xml}")

        start_location = self.start_location
        end_location = self.editable_end_location
        driver_id = self.driver_id
        driver_type = self.driver_type
        driver_name = self.driver_name
        transport_cost = self.transport_cost
        car_number = self.car_number
        transport_cost_payer = self.transport_cost_payer
        trans_id = self.trans_id
        comment = self.comment
        trans_txt = self.trans_txt
        formatted_begin_date = self.formatted_begin_date
        buyer_name = self.partner_id.name
        buyer_tin = self.partner_vat
        buyer_type = self.buyer_type
        delivery = self.delivery
        
        # New fields logic
        transporter_tin = self.transporter_tin if self.trans_id == '7' else ''
        par_id = '0'
        if self.delivery == '6' and self.sub_waybill_parent_id:
             # Ensure we get the ID from the parent waybill
             # If parent has invoice_id, use that. 
             if self.sub_waybill_parent_id.invoice_id:
                 par_id = self.sub_waybill_parent_id.invoice_id
             else:
                 raise UserError(_('მშობელი ზედნადები არ არის ატვირთული RS.GE-ზე'))

        if self.picking_type_id.code == 'internal':
            # For internal transfers, delivery is usually 1 (Internal) but if Carrier is used, logic might differ.
            # Protocol says: TYPE=1 is Internal. 
            # If trans_id is 7 (Carrier), we still use TYPE=1 but provide TRANSPORTER_TIN?
            # Or is it a different TYPE? 
            # Standard practice: Internal Transfer is Type 1.
            # Standard practice: Internal Transfer is Type 1.
            delivery = '1'
            end_location = self.editable_end_location
            buyer_tin = self.company_id.vat or self.env.user.company_id.vat

        if self.return_id:
            delivery = '5'

        # Logic for returns could be added here if needed
        
        # Check service user first
        url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
        headers = {"Content-Type": "text/xml; charset=utf-8"}
        
        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <chek_service_user xmlns="http://tempuri.org/">
              <su>{rs_acc}</su>
              <sp>{rs_pass}</sp>
            </chek_service_user>
          </soap:Body>
        </soap:Envelope>"""

        success, response_text, error_msg = self._safe_soap_request(url, soap_body, headers, "chek_service_user")
        if not success:
            raise UserError(f"Check service user failed: {error_msg}")

        seller_un_id = self._parse_xml_response(response_text, './/ns:un_id', {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 'ns': 'http://tempuri.org/'})
        if not seller_un_id:
            raise UserError("Unable to find 'un_id' in the response")
            
        # Fix -100 Error: Check for negative UN_ID (Auth Failure)
        if seller_un_id.startswith('-'):
             raise UserError(f"RS.GE ავტორიზაციის შეცდომა (კოდი: {seller_un_id}). გთხოვთ შეამოწმოთ მომხმარებელი და პაროლი.")

        # Dynamic Status Logic: If Carrier (7), send as Draft (0). Otherwise Active (1).
        waybill_status = '0' if trans_id == '7' else '1'

        soap_request = f"""
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body>
                <save_waybill xmlns="http://tempuri.org/">
                    <su>{rs_acc}</su>
                    <sp>{rs_pass}</sp>
                    <waybill>
                        <WAYBILL xmlns="">
                            {goods_list_xml}
                            <ID>{waybill_id}</ID>
                            <TYPE>{delivery}</TYPE>
                            <BUYER_TIN>{buyer_tin}</BUYER_TIN>
                            <CHEK_BUYER_TIN>{buyer_type}</CHEK_BUYER_TIN>
                            <BUYER_NAME>{escape(buyer_name) if buyer_name else ''}</BUYER_NAME>
                            <START_ADDRESS>{escape(start_location) if start_location else ''}</START_ADDRESS>
                            <END_ADDRESS>{escape(end_location) if end_location else ''}</END_ADDRESS>
                            <DRIVER_TIN>{driver_id}</DRIVER_TIN>
                            <CHEK_DRIVER_TIN>{driver_type}</CHEK_DRIVER_TIN>
                            <DRIVER_NAME>{escape(driver_name) if driver_name else ''}</DRIVER_NAME>
                            <TRANSPORT_COAST>{transport_cost}</TRANSPORT_COAST>
                            <RECEPTION_INFO></RECEPTION_INFO>
                            <RECEIVER_INFO></RECEIVER_INFO>
                            <DELIVERY_DATE></DELIVERY_DATE>
                            <STATUS>{waybill_status}</STATUS>
                            <SELER_UN_ID>{seller_un_id}</SELER_UN_ID>
                            <PAR_ID>{par_id}</PAR_ID>
                            <CAR_NUMBER>{escape(car_number) if car_number else ''}</CAR_NUMBER>
                            <BEGIN_DATE>{formatted_begin_date}</BEGIN_DATE>
                            <TRAN_COST_PAYER>{transport_cost_payer}</TRAN_COST_PAYER>
                            <TRANS_ID>{trans_id}</TRANS_ID>
                            <TRANS_TXT>{escape(trans_txt) if trans_txt else ''}</TRANS_TXT>
                            <COMMENT>{escape(comment) if comment else ''}</COMMENT>
                            <TRANSPORTER_TIN>{transporter_tin}</TRANSPORTER_TIN>
                        </WAYBILL>
                    </waybill>
                </save_waybill>
            </soap:Body>
        </soap:Envelope>
        """

        url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/save_waybill"
        }

        success, response_text, error_msg = self._safe_soap_request(url, soap_request, headers, "save_waybill")
        if not success:
            raise UserError(f"Save waybill failed: {error_msg}")

        if '<STATUS>' in response_text and '</STATUS>' in response_text:
            Status = response_text.split('<STATUS>')[1].split('</STATUS>')[0]
        else:
            raise UserError(f'Invalid response from server: No STATUS found')

        if Status >= '0':
            # Extract invoice_id and number
            try:
                root = ET.fromstring(response_text)
                id_element = root.find('.//ID')
                invoice_id = id_element.text if id_element is not None else None
                
                waybill_element = root.find('.//WAYBILL_NUMBER')
                invoice_number = waybill_element.text if waybill_element is not None else invoice_id
                
                self.invoice_id = invoice_id
                self.invoice_number = invoice_number
                self.completed_soap = '1'
                
                # Update combined invoice
                combined_invoice = self.env['combined.invoice.model'].search([], limit=1)
                if combined_invoice:
                    combined_invoice.write({
                        'invoice_id': invoice_id,
                        'invoice_number': invoice_number,
                    })
                else:
                    combined_invoice = self.env['combined.invoice.model'].create({
                        'invoice_id': invoice_id,
                        'invoice_number': invoice_number,
                    })
                self.combined_invoice_id = combined_invoice.id
                
            except Exception as e:
                _logger.error(f"Error parsing response: {e}")
                
        elif Status < '0':
            error_text = self._get_error_text_from_code(rs_acc, rs_pass, Status)
            raise UserError(error_text)

    def button_send_soap_request(self):
        """Upload waybills - auto-detects single vs batch mode. Supports correction if invoice_id exists."""
        _logger.info(f'Executing button_send_soap_request for {len(self)} record(s)')
        
        if len(self) == 1:
            for record in self:
                # Allow correction even if invoice_id exists
                record.send_soap_request()
                
                self.env.cr.commit()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {
                        'next': {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('Success'),
                                'message': _('ზედნადები წარმატებით აიტვირთა/დაკორექტირდა'),
                                'type': 'success',
                                'sticky': False,
                            }
                        }
                    }
                }
        else:
            success_records = []
            error_records = []
            skipped_records = []
            
            for record in self:
                try:
                    # Allow correction in batch mode too
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

    def send_soap_request_return(self):
        goods_list_xml = "<GOODS_LIST>"

        for move in self.move_ids_without_package:
            product = move.product_id
            quantity = move.product_uom_qty
            if quantity == 0:
                raise UserError("რაოდენობა ვერ იქნება ნულის ტოლი product: %s" % product.name)
            amount = move.cost_including_tax
            barcode = product.barcode
            unit_id = move.unit_id  # Assuming this is the correct field for unit_id
            tax_id = move.tax_id.name if move.tax_id else ''  # Assuming tax_id is a field in stock.move
            vat_type = -1  # or any other default value
            price_unit = amount / quantity
            unit_txt = move.unit_txt  # Assuming this is the correct field for unit_txt

            if tax_id == '18':
                vat_type = 0
            elif tax_id =='0':
                vat_type = 1

            goods_xml = f"""
                <GOODS>
                    <ID>0</ID>
                    <W_NAME>{escape(product.name)}</W_NAME>
                    <UNIT_ID>{unit_id}</UNIT_ID>
                    <UNIT_TXT>{escape(unit_txt) if unit_txt else ''}</UNIT_TXT>
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
        start_location = self.start_location
        end_location = self.editable_end_location
        driver_id = self.driver_id
        driver_type = self.driver_type
        driver_name = self.driver_name
        transport_cost = self.transport_cost
        car_number = self.car_number
        transport_cost_payer = self.transport_cost_payer
        trans_id = self.trans_id
        comment = self.comment
        trans_txt = self.trans_txt
        now = datetime.now()
        begin_date = self.begin_date
        formatted_begin_date=self.formatted_begin_date
        buyer_name=self.partner_id
        rs_acc = self.rs_acc
        rs_pass = self.rs_pass
        completed_soap = self.completed_soap
        buyer_tin = self.partner_vat
        field5 = self.field5
        if self.combined_invoice_id:
            raise UserError("ზედნადები უკვე ატვირთულია")

        for record in self:
            try:
                usn = record.rs_acc  # Use the rs_acc field of the record
                usp = record.rs_pass  # Use the rs_pass field of the record
                tin = record.driver_id


                soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
                    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                      <soap:Body>
                        <get_name_from_tin xmlns="http://tempuri.org/">
                          <su>{usn}</su>
                          <sp>{usp}</sp>
                          <tin>{tin}</tin>
                        </get_name_from_tin>
                      </soap:Body>
                    </soap:Envelope>"""

                # Define the URL and headers
                url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
                headers = {
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": "http://tempuri.org/get_name_from_tin"
                }

                # Send the request
                response = requests.post(url, data=soap_request, headers=headers)

                # Check for a successful response
                if response.status_code != 200:
                    record.company_review = f"Failed to get response from service. Status code: {response.status_code}"


                # Parse the XML response
                root = ET.fromstring(response.text)

                # Define the namespace (use the appropriate namespace for your SOAP response)
                namespaces = {
                    'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                    'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
                }

                # Find the `name` element in the response
                result_element = root.find('.//ns:get_name_from_tinResult', namespaces)

                # Check if the element was found and assign its text to the company_review field
                self.driver_name=result_element.text
            except Exception as e:
                record.company_review = f"An error occurred: {str(e)}"

        # Define the URL and headers
        url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
        }

        usn = record.rs_acc  # Use the rs_acc field of the record
        usp = record.rs_pass  # Replace with actual password

        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <chek_service_user xmlns="http://tempuri.org/">
              <su>{rs_acc}</su>
              <sp>{rs_pass}</sp>
            </chek_service_user>
          </soap:Body>
        </soap:Envelope>"""

        # Send the request
        response = requests.post(url, data=soap_body, headers=headers)

        # _logger.info the response status code
        _logger.info(response.status_code)

        # Parse the XML response
        root = ET.fromstring(response.text)

        # Define the namespace (use the appropriate namespace for your SOAP response)
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
        }

        # Find the `un_id` element in the response
        un_id_element = root.find('.//ns:un_id', namespaces)
        seller_un_id = un_id_element.text

        soap_request = f"""
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                <soap:Body>
                    <save_waybill xmlns="http://tempuri.org/">
                        <su>{rs_acc}</su>
                        <sp>{rs_pass}</sp>
                        <waybill>
                            <WAYBILL xmlns="">
                                {goods_list_xml}
                                <ID>0</ID>
                                <TYPE>{field5}</TYPE>
                                <BUYER_TIN>{buyer_tin}</BUYER_TIN>
                                <CHEK_BUYER_TIN></CHEK_BUYER_TIN>
                                <BUYER_NAME></BUYER_NAME>
                                <START_ADDRESS>{start_location}</START_ADDRESS>
                                <END_ADDRESS>{end_location}</END_ADDRESS>
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
            </soap:Envelope>
            """

        url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/save_waybill"
        }

        response = requests.post(url, data=soap_request.encode('utf-8'), headers=headers)
        response_text = response.text

        # Extract Status
        Status = response_text.split('<STATUS>')[1].split('</STATUS>')[0]
        if Status >= '0':
            invoice_id = response_text.split('<ID>')[1].split('</ID>')[0]
            invoice_number = response_text.split('<WAYBILL_NUMBER>')[1].split('</WAYBILL_NUMBER>')[0]

            # Update current model fields
            self.invoice_id = invoice_id
            self.invoice_number = invoice_number
            self.completed_soap = '1'

            # Create or update CombinedInvoiceModel record
            combined_invoice = self.env['combined.invoice.model'].search([], limit=1)  # Adjust your search criteria as needed
            if combined_invoice:
                # Update existing record
                combined_invoice.write({
                    'invoice_id': invoice_id,
                    'invoice_number': invoice_number,
                    # Add more fields if needed
                })
            else:
                # Create new record if none exists
                combined_invoice = self.env['combined.invoice.model'].create({
                    'invoice_id': invoice_id,
                    'invoice_number': invoice_number,
                    # Add more fields if needed
                })

            # Link the combined_invoice to current model
            self.combined_invoice_id = combined_invoice.id

        elif Status < '0':
            # Define the SOAP request XML with the provided <su> and <sp> values
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

            # Define the headers
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/get_error_codes"
            }

            # Send the SOAP request
            response = requests.post("http://services.rs.ge/waybillservice/waybillservice.asmx", data=soap_request, headers=headers)

            if response.status_code == 200:
                # Parse the XML response
                root = ET.fromstring(response.content)

                # Define the namespaces
                namespaces = {
                    'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                    'tempuri': 'http://tempuri.org/'
                }

                # Initialize an empty dictionary to store ID and TEXT values
                error_dict = {}

                # Find all ERROR_CODE elements and extract ID and TEXT values
                for error_code in root.findall(".//ERROR_CODE"):
                    id_value = error_code.find("ID").text
                    text_value = error_code.find("TEXT").text
                    error_dict[id_value] = text_value

                # Compare Status to numbers in error_dict and get corresponding error text
                error_text = error_dict.get(Status, "No error found for this status")
                raise UserError(error_text)

    def button_send_soap_request_return(self):
        for record in self:
            if not record.invoice_id:
                record.send_soap_request_return()
            else:
                raise UserError('ზედნადები უკვე ატვირთლია')
