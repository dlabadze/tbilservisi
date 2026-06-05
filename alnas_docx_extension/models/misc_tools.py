# -*- coding: utf-8 -*-
from datetime import datetime, date
import base64
import binascii
from PIL import Image
import io
import logging

_logger = logging.getLogger(__name__)

# Georgian month names
GEORGIAN_MONTHS = {
    1: 'იანვარი',
    2: 'თებერვალი',
    3: 'მარტი',
    4: 'აპრილი',
    5: 'მაისი',
    6: 'ივნისი',
    7: 'ივლისი',
    8: 'აგვისტო',
    9: 'სექტემბერი',
    10: 'ოქტომბერი',
    11: 'ნოემბერი',
    12: 'დეკემბერი',
}

# Georgian month name forms with postposition suffixes
GEORGIAN_MONTH_FORMS = {
    'დან': {
        1: 'იანვრიდან',
        2: 'თებერვლიდან',
        3: 'მარტიდან',
        4: 'აპრილიდან',
        5: 'მაისიდან',
        6: 'ივნისიდან',
        7: 'ივლისიდან',
        8: 'აგვისტოდან',
        9: 'სექტემბრიდან',
        10: 'ოქტომბრიდან',
        11: 'ნოემბრიდან',
        12: 'დეკემბრიდან',
    },
    'მდე': {
        1: 'იანვრამდე',
        2: 'თებერვლამდე',
        3: 'მარტამდე',
        4: 'აპრილამდე',
        5: 'მაისამდე',
        6: 'ივნისამდე',
        7: 'ივლისამდე',
        8: 'აგვისტომდე',
        9: 'სექტემბრამდე',
        10: 'ოქტომბრამდე',
        11: 'ნოემბრამდე',
        12: 'დეკემბრამდე',
    },
    'ის': {
        1: 'იანვრის',
        2: 'თებერვლის',
        3: 'მარტის',
        4: 'აპრილის',
        5: 'მაისის',
        6: 'ივნისის',
        7: 'ივლისის',
        8: 'აგვისტოს',
        9: 'სექტემბრის',
        10: 'ოქტომბრის',
        11: 'ნოემბრის',
        12: 'დეკემბრის',
    },
}


def field1(value):
    """
    Convert False values to empty string
    Returns the value as-is if it's not False
    """
    if value is False:
        return ''
    return value


def date1(date_value):
    """
    Format date as dd/mm/yyyy
    Args:
        date_value: datetime, date object, or string
    Returns:
        Formatted date string as dd/mm/yyyy or empty string if value is False/None
    """
    if not date_value or date_value is False:
        return ''
    
    try:
        # If it's already a datetime object
        if isinstance(date_value, datetime):
            return date_value.strftime('%d/%m/%Y')
        
        # If it's a date object
        if isinstance(date_value, date):
            return date_value.strftime('%d/%m/%Y')
        
        # If it's a string, try to parse it
        if isinstance(date_value, str):
            # Try common date formats
            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y', '%m/%d/%Y']:
                try:
                    parsed_date = datetime.strptime(date_value, fmt)
                    return parsed_date.strftime('%d/%m/%Y')
                except ValueError:
                    continue
            
            # If parsing failed, return the original value
            return date_value
        
    except Exception:
        pass
    
    return ''


def date2(date_value, format_type='full'):
    """
    Format date with Georgian month names
    Args:
        date_value: datetime, date object, or string
        format_type: 'full' (16 იანვარი 2025), 'short' (16 იანვარი), 'month_year' (იანვარი 2025)
    Returns:
        Formatted date string with Georgian month name or empty string if value is False/None
    """
    if not date_value or date_value is False:
        return ''
    
    try:
        # Convert to datetime object if needed
        parsed_date = None
        
        # If it's already a datetime object
        if isinstance(date_value, datetime):
            parsed_date = date_value
        
        # If it's a date object
        elif isinstance(date_value, date):
            parsed_date = datetime.combine(date_value, datetime.min.time())
        
        # If it's a string, try to parse it
        elif isinstance(date_value, str):
            # Try common date formats
            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y', '%m/%d/%Y']:
                try:
                    parsed_date = datetime.strptime(date_value, fmt)
                    break
                except ValueError:
                    continue
        
        if not parsed_date:
            return ''
        
        # Get day, month, year
        day = parsed_date.day
        month = parsed_date.month
        year = parsed_date.year
        
        # Get Georgian month name
        month_name = GEORGIAN_MONTHS.get(month, '')
        
        # Format based on type
        if format_type == 'short':
            return f'{day} {month_name}'
        elif format_type == 'month_year':
            return f'{month_name} {year}'
        else:  # full
            return f'{day} {month_name} {year}'
        
    except Exception:
        pass
    
    return ''


def date3(date_value, suffix=''):
    """
    Format date as "YYYY წლის DD MonthName[suffix]" with Georgian month names.
    Args:
        date_value: datetime, date object, or string
        suffix: optional postposition suffix - 'დან', 'მდე', or 'ის'
    Returns:
        Formatted date string or empty string if value is False/None

    Examples:
        date3(field)        → "2026 წლის 01 იანვარი"
        date3(field, 'დან') → "2026 წლის 01 იანვრიდან"
        date3(field, 'მდე') → "2026 წლის 01 იანვრამდე"
        date3(field, 'ის')  → "2026 წლის 01 იანვრიის"
    """
    if not date_value or date_value is False:
        return ''

    try:
        parsed_date = None

        if isinstance(date_value, datetime):
            parsed_date = date_value
        elif isinstance(date_value, date):
            parsed_date = datetime.combine(date_value, datetime.min.time())
        elif isinstance(date_value, str):
            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y', '%m/%d/%Y']:
                try:
                    parsed_date = datetime.strptime(date_value, fmt)
                    break
                except ValueError:
                    continue

        if not parsed_date:
            return ''

        day = f'{parsed_date.day:02d}'
        month = parsed_date.month
        year = parsed_date.year

        if suffix and suffix in GEORGIAN_MONTH_FORMS:
            month_name = GEORGIAN_MONTH_FORMS[suffix].get(month, '')
            if suffix == 'ის':
                return f'{year} წლის {day} {month_name}'
            return f'{year} წლის {day} {month_name}'

        month_name = GEORGIAN_MONTHS.get(month, '')
        return f'{year} წლის {day} {month_name}'

    except Exception:
        pass

    return ''


def format_value(value):
    """
    Universal value formatter:
    - Returns empty string for False
    - Formats dates as dd/mm/yyyy
    - Returns other values as-is
    """
    if value is False:
        return ''
    
    if isinstance(value, (datetime, date)):
        return date1(value)
    
    return value


def get_record(recordset, index=0):
    """
    Get a specific record from a recordset by index
    Args:
        recordset: Odoo recordset (One2many, Many2many, or any recordset)
        index: Index of the record to retrieve (0-based, default: 0)
    Returns:
        Single record at the specified index or empty recordset if index is out of range
    
    Usage in template:
        {{get_record(docs.employee_line_ids, 0).employee_id.name}}
        {{get_record(docs.employee_line_ids, 1).employee_id.name}}
    """
    if not recordset:
        return recordset.browse()  # Return empty recordset of the same model
    
    try:
        if 0 <= index < len(recordset):
            return recordset[index]
        return recordset.browse()  # Return empty recordset if index out of range
    except Exception:
        return recordset.browse()


def get_first(recordset):
    """
    Get the first record from a recordset
    Args:
        recordset: Odoo recordset
    Returns:
        First record or empty recordset if empty
    
    Usage in template:
        {{get_first(docs.employee_line_ids).employee_id.name}}
    """
    return get_record(recordset, 0)


def get_last(recordset):
    """
    Get the last record from a recordset
    Args:
        recordset: Odoo recordset
    Returns:
        Last record or empty recordset if empty
    
    Usage in template:
        {{get_last(docs.employee_line_ids).employee_id.name}}
    """
    if not recordset:
        return recordset.browse()
    return get_record(recordset, len(recordset) - 1)


def join_field(recordset, field_name, separator=', '):
    """
    Join values from a specific field across all records in a recordset
    Args:
        recordset: Odoo recordset
        field_name: Name of the field to extract values from
        separator: String to join values with (default: ', ')
    Returns:
        Joined string of all field values
    
    Usage in template:
        {{join_field(docs.employee_line_ids, 'employee_id.name')}}
        {{join_field(docs.employee_line_ids, 'employee_id.name', ' | ')}}
    """
    if not recordset:
        return ''
    
    try:
        values = []
        for record in recordset:
            # Handle nested field access (e.g., 'employee_id.name')
            value = record
            for field_part in field_name.split('.'):
                if value:
                    value = getattr(value, field_part, None)
                else:
                    break
            
            # Add the value if it's not False or None
            if value not in (False, None):
                values.append(str(value))
        
        return separator.join(values)
    except Exception as e:
        _logger.error(f"Error in join_field: {e}")
        return ''


def count_records(recordset):
    """
    Count the number of records in a recordset
    Args:
        recordset: Odoo recordset
    Returns:
        Integer count of records
    
    Usage in template:
        {{count_records(docs.employee_line_ids)}}
    """
    if not recordset:
        return 0
    return len(recordset)


def num_to_words(amount, part='full'):
    """
    Convert a number to Georgian words.

    Modes:
    - full (default): "<lari> ლარი და <tetri> თეთრი" (when tetri > 0)
    - lari: only lari words
    - tetri: only tetri words

    Usage in template:
        {{ num_to_words(docs.amount_total) }}           # full
        {{ num_to_words(docs.amount_total, 'lari') }}   # only lari words
        {{ num_to_words(docs.amount_total, 'tetri') }}  # only tetri words
    """
    if amount is False or amount is None or amount == '':
        amount = 0
    try:
        amount = abs(float(amount))
    except (TypeError, ValueError):
        amount = 0

    # Separate integer and decimal parts
    lari = int(amount)
    tetri = int(round((amount - lari) * 100))

    # Handle edge-case like 1.999 -> tetri 100
    if tetri == 100:
        lari += 1
        tetri = 0

    # Georgian number words
    ones = ['', 'ერთი', 'ორი', 'სამი', 'ოთხი', 'ხუთი', 'ექვსი', 'შვიდი', 'რვა', 'ცხრა']
    teens = ['ათი', 'თერთმეტი', 'თორმეტი', 'ცამეტი', 'თოთხმეტი', 'თხუთმეტი',
             'თექვსმეტი', 'ჩვიდმეტი', 'თვრამეტი', 'ცხრამეტი']
    tens = ['', '', 'ოცი', 'ოცდაათი', 'ორმოცი', 'ორმოცდაათი', 'სამოცი', 'სამოცდაათი',
            'ოთხმოცი', 'ოთხმოცდაათი']
    tens_combined = ['', '', 'ოც', 'ოცდაათ', 'ორმოც', 'ორმოცდაათ', 'სამოც', 'სამოცდაათ',
                     'ოთხმოც', 'ოთხმოცდაათ']
    hundreds_alone = ['', 'ასი', 'ორასი', 'სამასი', 'ოთხასი', 'ხუთასი', 'ექვსასი', 'შვიდასი',
                      'რვაასი', 'ცხრაასი']
    hundreds_combined = ['', 'ას', 'ორას', 'სამას', 'ოთხას', 'ხუთას', 'ექვსას', 'შვიდას',
                         'რვაას', 'ცხრაას']

    def convert_under_thousand(n):
        if n == 0:
            return ''
        elif n < 10:
            return ones[n]
        elif n < 20:
            return teens[n - 10]
        elif n < 100:
            decade = n // 10
            ones_part = n % 10
            if ones_part == 0:
                return tens[decade]
            elif decade in [2, 4, 6, 8]:
                return tens_combined[decade] + 'და' + ones[ones_part]
            else:
                return tens_combined[decade - 1] + 'და' + teens[ones_part]
        else:
            remainder = n % 100
            if remainder != 0:
                return hundreds_combined[n // 100] + ' ' + convert_under_thousand(remainder)
            else:
                return hundreds_alone[n // 100]

    def convert_number(n):
        if n == 0:
            return "ნული"
        elif n < 1000:
            return convert_under_thousand(n)
        elif n < 1000000:
            thousands = n // 1000
            remainder = n % 1000
            if thousands == 1:
                if remainder > 0:
                    return "ათას " + convert_under_thousand(remainder)
                return "ათასი"
            if remainder > 0:
                return convert_under_thousand(thousands) + " ათას " + convert_under_thousand(remainder)
            return convert_under_thousand(thousands) + " ათასი"
        else:
            millions = n // 1000000
            thousands = (n % 1000000) // 1000
            remainder = n % 1000
            result = convert_under_thousand(millions) + " მილიონი"
            if thousands > 0:
                if remainder > 0:
                    result += " " + convert_under_thousand(thousands) + " ათას"
                else:
                    result += " " + convert_under_thousand(thousands) + " ათასი"
            if remainder > 0:
                result += " " + convert_under_thousand(remainder)
            return result

    lari_words = convert_number(lari)
    tetri_words = convert_number(tetri)

    part = (part or 'full').lower()
    if part == 'lari':
        return lari_words
    if part == 'tetri':
        return tetri_words

    result = lari_words + " ლარი"
    if tetri > 0:
        result += " და " + tetri_words + " თეთრი"
    return result
