from odoo import models, api
from datetime import datetime, timedelta
import requests
import logging
import xml.etree.ElementTree as ET

_logger = logging.getLogger(__name__)


class AttendanceJSONImporter(models.Model):
    _name = 'attendance.json.importer'
    _description = 'Attendance Importer (API XML/JSON, cron-safe)'

    API_URL = "http://192.168.22.12:8050/api/Integration/tabels"

    # ============================================================
    # MAIN ENTRY POINT (called by cron via job)
    # ============================================================
    # ============================================================
    # MAIN ENTRY POINT (called by Job)
    # ============================================================
    @api.model
    def import_employees(self, employees, date_from, date_to):
        """
        :param employees: recordset of hr.employee
        """
        _logger.info(
            "Attendance import started for %s employees",
            len(employees)
        )

        for emp in employees:
            if not emp.identification_id:
                continue
                
            try:
                self._import_employee(emp, date_from, date_to)
                
                # Commit after each employee to save progress
                self.env.cr.commit()
            except Exception:
                _logger.exception(
                    "Attendance import failed for identification %s",
                    emp.identification_id
                )

        _logger.info("Attendance import batch finished")

    # ============================================================
    # IMPORT ONE EMPLOYEE
    # ============================================================
    def _import_employee(self, employee, date_from, date_to):
        params = {
            'dateFrom': date_from,
            'dateTo': date_to,
            'privateNumber': employee.identification_id,
        }

        headers = {
            # API defaults to XML; JSON is supported if backend allows
            'Accept': 'application/xml',
            'User-Agent': 'Odoo/18 Attendance Import',
        }

        response = requests.get(
            self.API_URL,
            params=params,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()

        content = response.text.strip()
        if not content:
            return

        # Detect format
        if content.startswith('<'):
            rows = self._parse_xml(content)
        else:
            # fallback to JSON
            rows = response.json()

        for row in rows:
            self._create_attendance(employee, row)

    # ============================================================
    # XML PARSER
    # ============================================================
    def _parse_xml(self, xml_text):
        """
        Parses:
        <ArrayOfExportTabelDto>
          <ExportTabelDto>
            <PrivateNumber>...</PrivateNumber>
            <EventDate>...</EventDate>
            <EventMark>...</EventMark>
          </ExportTabelDto>
        </ArrayOfExportTabelDto>
        """
        root = ET.fromstring(xml_text)
        result = []

        for node in root.findall('.//ExportTabelDto'):
            result.append({
                'eventDate': (node.findtext('EventDate') or '').strip(),
                'eventMark': (node.findtext('EventMark') or '').strip(),
            })

        return result

    # ============================================================
    # CREATE hr.attendance
    # ============================================================
    def _create_attendance(self, employee, row):
        event_date = row.get('eventDate')
        event_mark = row.get('eventMark')

        if not (event_date and event_mark):
            return

        # Validate mark against your Studio selection field
        selection = dict(
            self.env['hr.attendance']
            ._fields['x_studio_selection_field_99n_1j76jab36']
            .selection or []
        )
        if event_mark not in selection:
            _logger.warning(
                "Unknown eventMark %s for employee %s",
                event_mark,
                employee.identification_id
            )
            return

        date = datetime.strptime(event_date, "%Y-%m-%d").date()

        # Fixed working hours (matches your existing data)
        check_in = datetime.combine(date, datetime.min.time()) + timedelta(hours=9)
        check_out = datetime.combine(date, datetime.min.time()) + timedelta(hours=18)

        # Duplicate protection (one attendance per day)
        exists = self.env['hr.attendance'].search([
            ('employee_id', '=', employee.id),
            ('check_in', '=', check_in),
        ], limit=1)

        if exists:
            return

        self.env['hr.attendance'].create({
            'employee_id': employee.id,
            'check_in': check_in,
            'check_out': check_out,
            'in_mode': 'manual',
            'out_mode': 'manual',
            # Your Studio field
            'x_studio_selection_field_99n_1j76jab36': event_mark,
        })
