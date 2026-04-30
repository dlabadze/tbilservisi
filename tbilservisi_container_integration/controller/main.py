from odoo import http
from odoo.http import request
from odoo import fields
from odoo.exceptions import ValidationError
import json
from datetime import timedelta
import logging
_logger = logging.getLogger(__name__)


class ToContainerApi(http.Controller):
 
    # 1. Get Employee (თანამშრომლები)
    @http.route('/api/GetEmployee/<string:token>', type='http', auth='public', methods=['GET'], csrf=False)
    def get_staff(self, token, **kw): 
        db_name = request.session.db or request.env.cr.dbname
        _logger.info("API accessed for database: %s", db_name)
        if token != '616d61746572617375':
            return request.make_response(json.dumps({'error': 'Invalid token'}), headers=[('Content-Type', 'application/json')])
        fields_lst = [
            'name', 'x_studio_tabeli', 'identification_id',
            'birthday', 'x_studio_fathername', 'gender', 'work_phone', 'work_email',
            'private_street', 'x_studio_address', 'x_studio_country', 'create_date', 'write_date',
        ]
        employees = request.env['hr.employee'].sudo().search_read([], fields_lst)

        result = []
        for emp in employees:
            # Id
            id = emp.get('id', 0)
            # KOD
            tabeli = emp.get('x_studio_tabeli', None)
            if tabeli and ',' in tabeli:
                tabeli = tabeli.replace(',', '')

            
            # Name
            full_name = emp.get('name', None).strip()
            parts = full_name.split()
            first_name = parts[0] if len(parts) > 0 else None
            last_name = " ".join(parts[1:]) if len(parts) > 1 else None

            # PIRADI
            identification_id = emp.get('identification_id', None)

            # Birthday
            birthday = emp.get('birthday', None)
            if birthday:
                birthday = birthday.strftime('%Y-%m-%d')

            # Fathername
            fathername = emp.get('x_studio_fathername', None)

            # Gender
            gender = emp.get('gender', None)

            # Work Phone
            work_phone = emp.get('work_phone', None)

            # Work Email
            work_email = emp.get('work_email', None)

            # Private Street
            private_street = emp.get('private_street', None)

            # X Studio Address
            x_studio_address = emp.get('x_studio_address', None)

            # X Studio Country
            x_studio_country = emp.get('x_studio_country', None)
            if x_studio_country:
                x_studio_country = x_studio_country[1]
            
            # Create Date
            create_date = emp.get('create_date', None)
            if create_date:
                create_date += timedelta(hours=4)
                create_date = create_date.strftime('%Y-%m-%d %H:%M:%S')
            
            # Write Date
            write_date = emp.get('write_date', None)
            if write_date:
                write_date += timedelta(hours=4)
                write_date = write_date.strftime('%Y-%m-%d %H:%M:%S')

            result.append({
                'id': str(id),
                'tabeli': tabeli if tabeli else None,
                'piradi': identification_id if identification_id else None,
                'name': first_name if first_name else None,
                'surname': last_name if last_name else None,
                'birthday': birthday if birthday else None,
                'fatherName': fathername if fathername else None,
                'gender': gender if gender else None,
                'workPhone': work_phone if work_phone else None,
                'workEmail': work_email if work_email else None,
                'privateStreet': private_street if private_street else None,
                'address': x_studio_address if x_studio_address else None,
                'country': x_studio_country if x_studio_country else None,
                'IP_CREATED': create_date if create_date else None,
                'IP_CHANGED': write_date if write_date else None,
            })

        return request.make_response(
            json.dumps(result, ensure_ascii=False), 
            headers=[('Content-Type', 'application/json; charset=utf-8')]
        )

    # 2. Get Positions
    @http.route('/api/GetPositions/<string:token>', type='http', auth='public', methods=['GET'], csrf=False)
    def get_positions(self, token, **kw):
        db_name = request.session.db or request.env.cr.dbname
        _logger.info("API accessed for database: %s", db_name)
        if token != '616d61746572617375':
            return request.make_response(json.dumps({'error': 'Invalid token'}), headers=[('Content-Type', 'application/json')])
        else:
            positions = request.env['hr.job'].sudo().search_read([], ['name', 'department_id'])

            result = []
            for position in positions:
                id = position.get('id', 0)
                name = position.get('name', None)
                department_id = position.get('department_id', None)
                if name == "დირექტორი":
                    _logger.info(f"Department ID: {department_id}")
                if department_id:
                    department_id = department_id[1]
                result.append({
                    'id': str(id) if id else None,
                    'name': name if name else None,
                    'department': department_id if department_id else None,
                })
            # return request.make_response(json.dumps(result), headers=[('Content-Type', 'application/json')])
            return request.make_response(
                json.dumps(result, ensure_ascii=False), 
                headers=[('Content-Type', 'application/json; charset=utf-8')]
            )

    # 3. Get Departments
    @http.route('/api/GetDepartments/<string:token>', type='http', auth='public', methods=['GET'], csrf=False)
    def get_departments(self, token, **kw):
        if token != '616d61746572617375':
            return request.make_response(json.dumps({'error': 'Invalid token'}), headers=[('Content-Type', 'application/json')])
        else:
            departments = request.env['hr.department'].sudo().search_read([], ['name', 'display_name'])
            result = []
            for dep in departments:
                id = dep.get('id', 0)
                name = dep.get('name', None)
                display_name = dep.get('display_name', None)
                empl_recs = request.env['hr.employee'].sudo().search_read([('department_id.display_name', '=', display_name)])
                employee_list = []
                for emp in empl_recs:
                    employee_list.append({
                        'id': str(emp.get('id', 0)),
                        'name': emp.get('name', None),
                    })

                result.append({
                    'id': str(id) if id else None,
                    'name': name if name else None,
                    'employees': employee_list,
                })
            return request.make_response(
                json.dumps(result, ensure_ascii=False), 
                headers=[('Content-Type', 'application/json; charset=utf-8')]
            )
        
    