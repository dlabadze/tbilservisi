import requests
import xml.etree.ElementTree as ET
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'hr.employee'

    rs_acc = fields.Char(compute='_compute_rs_acc', string='rs.ge ექაუნთი', readonly=True)
    rs_pass = fields.Char(compute='_compute_rs_pass', string='rs.ge პაროლი', readonly=True)
    buyer_tin = fields.Char(string='buyer_tin')
    company_review = fields.Char(string='company_name')

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

    def button_send_soap_request(self):
        for record in self:
            # Define the URL and headers
            url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
            }

            # Define the SOAP body
            usn = record.rs_acc  # Use the rs_acc field of the record
            usp = record.rs_pass  # Use the rs_pass field of the record

            soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <chek_service_user xmlns="http://tempuri.org/">
                  <su>{usn}</su>
                  <sp>{usp}</sp>
                </chek_service_user>
              </soap:Body>
            </soap:Envelope>"""

            # Send the request
            response = requests.post(url, data=soap_body, headers=headers)

            # Parse the XML response
            root = ET.fromstring(response.text)

            # Define the namespace (use the appropriate namespace for your SOAP response)
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
            }

            # Find the `un_id` element in the response
            un_id_element = root.find('.//ns:un_id', namespaces)

            # Check if the element was found and assign its text to the buyer_tin field
            if un_id_element is not None:
                record.buyer_tin = un_id_element.text

    @api.onchange('identification_id')
    def _onchange_identification_id(self):
        if self.identification_id:
            try:
                # Use current environment user credentials if record doesn't have them yet
                usn = self.rs_acc or self.env.user.rs_acc
                usp = self.rs_pass or self.env.user.rs_pass
                tin = self.identification_id

                if not usn or not usp:
                    return

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

                url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
                headers = {
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": "http://tempuri.org/get_name_from_tin"
                }

                # Added a 5-second timeout so the UI doesn't freeze indefinitely if the service is down
                response = requests.post(url, data=soap_request, headers=headers, timeout=5)

                if response.status_code == 200:
                    root = ET.fromstring(response.text)
                    namespaces = {
                        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                        'ns': 'http://tempuri.org/'
                    }
                    result_element = root.find('.//ns:get_name_from_tinResult', namespaces)

                    if result_element is not None and result_element.text:
                        # This automatically populates the Name field in the UI
                        self.name = result_element.text
                        self.company_review = "Name fetched successfully"
                    else:
                        self.company_review = "Could not find name for this TIN"
                else:
                    self.company_review = f"Service returned error code: {response.status_code}"

            except requests.exceptions.Timeout:
                self.company_review = "Request to rs.ge timed out."
            except Exception as e:
                self.company_review = f"An error occurred: {str(e)}"

    def button_get_name_from_tin(self):
        for record in self:
            try:
                usn = record.rs_acc  # Use the rs_acc field of the record
                usp = record.rs_pass  # Use the rs_pass field of the record
                tin = record.identification_id

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
                    continue

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
                if result_element is not None:
                    record.name = result_element.text
                else:
                    _logger.error(f'Could not find get_name_from_tinResult in response')
                    record.company_review = "Could not find name in response"

            except Exception as e:
                record.company_review = f"An error occurred: {str(e)}"
