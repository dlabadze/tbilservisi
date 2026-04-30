import requests
import xml.etree.ElementTree as ET
import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    status = fields.Char('Status')
    combined_invoice_id = fields.Many2one('combined.invoice.model', string='Combined Invoice Model')
    invoice_number = fields.Char(related='combined_invoice_id.invoice_number', string='ზედნადების ნომერი')
    invoice_id = fields.Char(related='combined_invoice_id.invoice_id', string='ზედნადების ID')
    start_location = fields.Char('ტრანსპორტირების დაწყების ადგილი')
    end_location = fields.Char(string="End Location")
    editable_end_location = fields.Char(string="ტრანსპორტირების დასრულების ადგილი")
    error_field = fields.Char(string="error_field")
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    warehouse_address = fields.Char(related='warehouse_id.partner_id.name', string='Warehouse Address', readonly=True)
    begin_date = fields.Datetime(string='დაწყების დრო', default=fields.Datetime.now)
    show_all_fields = fields.Boolean(string='რს-ის ველები')

    formatted_begin_date = fields.Char(compute='_compute_formatted_begin_date', string='Formatted Begin Date')

    delivery = fields.Selection([
        ('2', 'მიწოდება ტრანსპორტირებით'),
        ('3', 'ტრანსპორტირების გარეშე'),
    ], 'მიწოდების სახე', default='2')

    is_start_location_required = fields.Boolean(string="Is Start Location Required", compute="_compute_is_start_location_required")
    is_editable_end_location_required = fields.Boolean(
        string="Is Editable End Location Required", compute="_compute_is_editable_end_location_required"
    )

    TRANSPORT_TYPES = [
        ('1', 'საავტომობილო'),
        ('2', 'სარკინიგზო'),
        ('3', 'საავიაციო'),
        ('4', 'სხვა'),
        ('6', 'საავტომობილო - უცხო ქვეყნის'),
        ('7', 'გადამზიდავი'),
        ('8', 'მოპედი/მოტოციკლი'),
    ]
    trans_id = fields.Selection(TRANSPORT_TYPES, string='ტრანსპორტირების სახე', default='1')
    trans_txt = fields.Char('ტრანსპორტირების ტექსტი')
    is_trans_id_4 = fields.Boolean(compute='_compute_is_trans_id_4')

    BUYER_TYPES = [
        ('1', 'საქართველოს მოქალაქე'),
        ('0', 'უცხოეთის მოქალაქე'),
    ]

    DRIVER_TYPES = [
        ('1', 'საქართველოს მოქალაქე'),
        ('0', 'უცხოეთის მოქალაქე'),
    ]

    TRANSPORT_COST_PAYER_TYPES = [
        ('1', 'მყიდველი'),
        ('2', 'გამყიდველი'),
    ]
    buyer_type = fields.Selection(BUYER_TYPES, string='მყიდველი', default='1')
    driver_type = fields.Selection(DRIVER_TYPES, string='მძღოლის ტიპი', default='1')
    transport_cost_payer = fields.Selection(TRANSPORT_COST_PAYER_TYPES, string='ტრანსპორტირების ღირებულების გადამხდელი', default='1')

    car_number = fields.Char('მანქანის ნომერი')
    driver_id = fields.Char('მძღოლის პირადი ნომერი')
    driver_name = fields.Char('მძღოლის სახელი')
    transport_cost = fields.Float('ტრანსპორტირების ღირებულება')
    comment = fields.Text('კომენტარი')

    rs_acc = fields.Char(compute='_compute_rs_acc', string='rs.ge ექაუნთი', readonly=True)
    rs_pass = fields.Char(compute='_compute_rs_pass', string='rs.ge პაროლი', readonly=True)
    partner_vat = fields.Char(related='partner_id.vat', string='Customer VAT', readonly=True, store=True)

    completed_soap = fields.Char(string='გაგზავნილია')
    is_soap_completed = fields.Boolean(compute='_compute_is_soap_completed')

    @api.depends('completed_soap')
    def _compute_is_soap_completed(self):
        for record in self:
            record.is_soap_completed = record.completed_soap == '1'

    @api.depends('begin_date')
    def _compute_formatted_begin_date(self):
        for record in self:
            if record.begin_date:
                # Convert the Datetime field to a datetime object
                begin_date_datetime = fields.Datetime.from_string(record.begin_date)
                # Format the datetime object to a string in the desired format
                record.formatted_begin_date = begin_date_datetime.strftime("%Y-%m-%dT%H:%M:%S")
            else:
                record.formatted_begin_date = False

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.end_location = self.partner_id.street
            if not self.editable_end_location:
                self.editable_end_location = self.partner_id.street

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        if self.warehouse_id:
            self.start_location = self.warehouse_id.additional_address
        else:
            self.start_location = False

    @api.depends('delivery')
    def _compute_is_start_location_required(self):
        for record in self:
            record.is_start_location_required = record.delivery == '2'

    @api.depends('delivery')
    def _compute_is_editable_end_location_required(self):
        for record in self:
            record.is_editable_end_location_required = record.delivery == '2'

    @api.onchange('delivery')
    def _onchange_delivery(self):
        if self.delivery == '3':
            self.editable_end_location = self.start_location

    @api.depends('trans_id')
    def _compute_is_trans_id_4(self):
        for record in self:
            record.is_trans_id_4 = record.trans_id == '4'

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

        # Define the URL and headers
        url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_name_from_tin"
        }

        # Send the request
        response = requests.post(url, data=soap_request, headers=headers)

        # Comprehensive logging for get_name_from_tin
        _logger.info(f'=== GET_NAME_FROM_TIN REQUEST DETAILS ===')
        _logger.info(f'URL: {url}')
        _logger.info(f'Headers: {headers}')
        _logger.info(f'TIN: {tin}')
        _logger.info(f'Request Status Code: {response.status_code}')
        _logger.info(f'Response Headers: {dict(response.headers)}')
        _logger.info(f'Full SOAP Response Text: {response.text}')
        _logger.info(f'Response Length: {len(response.text)} characters')

        # Check if the request was successful
        if response.status_code == 200:
            # Extract the content of the get_name_from_tinResult element from the response
            start_tag = "<get_name_from_tinResult>"
            end_tag = "</get_name_from_tinResult>"
            start_index = response.text.find(start_tag) + len(start_tag)
            end_index = response.text.find(end_tag)
            name = response.text[start_index:end_index]
            # Fill the name field with the response
            _logger.info(f'✅ Successfully extracted name: {name}')
            return name
        else:
            _logger.error(f'❌ Failed to get name from TIN. Status code: {response.status_code}')
            _logger.error(f'Response: {response.text}')
            return False

    def generate_goods_list_xml(self, record):
        goods_list_xml = "<GOODS_LIST>"

        for line in self.order_line:
            product = line.product_id
            quantity = line.product_uom_qty
            if quantity == 0:
                raise UserError("რაოდენობა ვერ იქნება ნულის ტოლი product: %s" % product.name)
            amount = line.price_total
            barcode = line.barcode if line.barcode else ''  # Use empty string if barcode is missing
            unit_id = line.unit_id
            if not unit_id:  # Check if the unit_id is empty
                raise UserError(_('დამატეთ rs.ge-ს ერთეული პროდუქციაზე'))
            tax_id = line.tax_id.name
            # Initialize vat_type to a default value
            vat_type = -1  # or any other default value
            if quantity != 0:
                price_unit = amount / quantity
            else:
                price_unit = 0
            unit_txt = line.unit_txt

            if tax_id == '18%':
                vat_type = 0
            elif tax_id =='0%':
                vat_type = 1
            else:
                # raise UserError(_('დაბეგვრა უნდა იყოს ან 18 ან 0'))
                # Allowing other taxes or handling them as needed, or uncomment above
                pass

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
            goods_list_xml = self.generate_goods_list_xml(self)
            _logger.info('Goods List XML: %s', goods_list_xml)

            # Extracting required fields
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
            now = datetime.now()
            begin_date = self.begin_date
            formatted_begin_date = self.formatted_begin_date
            buyer_name = self.partner_id.name
            buyer_tin = self.partner_vat
            rs_acc = self.rs_acc
            rs_pass = self.rs_pass

            _logger.info('Buyer Type: %s, Start Location: %s, End Location: %s', buyer_type, start_location, end_location)
            # ... (logging continues)

            # First SOAP request to check service user
            url_check_service_user = "http://services.rs.ge/WayBillService/WayBillService.asmx"
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
            }
            soap_body_check_service_user = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <chek_service_user xmlns="http://tempuri.org/">
                  <su>{rs_acc}</su>
                  <sp>{rs_pass}</sp>
                </chek_service_user>
              </soap:Body>
            </soap:Envelope>"""

            # Send the request
            response_check_service_user = requests.post(url_check_service_user, data=soap_body_check_service_user.encode('utf-8'), headers=headers)
            
            # Parse the XML response
            root_check_service_user = ET.fromstring(response_check_service_user.text)
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns': 'http://tempuri.org/'
            }

            un_id_element = root_check_service_user.find('.//ns:un_id', namespaces)
            if un_id_element is not None:
                seller_un_id = un_id_element.text
            else:
                raise UserError("Unable to find 'un_id' in the response")

            # Second SOAP request to save waybill
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

            # Send the request
            response_save_waybill = requests.post(url_save_waybill, data=soap_request_save_waybill.encode('utf-8'), headers=headers)
            
            # Parse the response
            if response_save_waybill.status_code == 200:
                response_text = response_save_waybill.text
                try:
                    if '<STATUS>' in response_text and '</STATUS>' in response_text:
                        Status = response_text.split('<STATUS>')[1].split('</STATUS>')[0]
                    else:
                        raise UserError(f'Invalid response from server: No STATUS found')
                except IndexError:
                    raise UserError(f'Error parsing server response')

                if Status >= '0':
                    # Success logic (commented out in original, but might need to be active?)
                    # invoice_id = response_text.split('<ID>')[1].split('</ID>')[0]
                    # invoice_number = response_text.split('<WAYBILL_NUMBER>')[1].split('</WAYBILL_NUMBER>')[0]
                    pass

                elif Status < '0':
                    # Error handling
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
                    response = requests.post("http://services.rs.ge/waybillservice/waybillservice.asmx", data=soap_request, headers=headers)

                    if response.status_code == 200:
                        root = ET.fromstring(response.content)
                        error_dict = {}
                        for error_code in root.findall(".//ERROR_CODE"):
                            id_value = error_code.find("ID").text
                            text_value = error_code.find("TEXT").text
                            error_dict[id_value] = text_value
                        
                        error_text = error_dict.get(Status, "ამ სტატუსისთვის ერორი არ მოიძებნა შეამოწმე ექაუნთი და პაროლი rs.ge")
                        self.error_field = error_text
                        raise UserError(error_text)
        except Exception as e:
            _logger.exception("Error occurred while sending SOAP request")
            raise UserError(f"Error: {e}")

    def button_send_soap_request(self):
        for record in self:
            record.send_soap_request()
