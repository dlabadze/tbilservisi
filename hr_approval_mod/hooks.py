import logging
import re

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


APPROVAL_REQUEST_COLUMN_DDL = [
    ("brdzaneba_date", "date"),
    ("brdzaneba_employee_id", "integer"),
    ("brdzaneba_start_date", "date"),
    ("brdzaneba_end_date", "date"),
    ("brdzaneba_department_id", "integer"),
    ("brdzaneba_job_id", "integer"),
    ("brdzaneba_shtati", "varchar"),
    ("brdzaneba_safudzveli", "text"),
    ("brdzaneba_salary", "double precision"),
    ("release_date", "date"),
]


def _extract_cr_env(first_arg):
    if hasattr(first_arg, 'cr'):
        # Odoo 18 passes Environment to hooks.
        return first_arg.cr, first_arg
    # Older hook style may pass cursor directly.
    cr = first_arg
    env = api.Environment(cr, SUPERUSER_ID, {})
    return cr, env


def pre_init_hook(first_arg):
    """Ensure legacy DBs have required columns before FK checks run on install."""
    cr, _env = _extract_cr_env(first_arg)
    for column_name, column_type in APPROVAL_REQUEST_COLUMN_DDL:
        cr.execute(
            f"ALTER TABLE approval_request ADD COLUMN IF NOT EXISTS {column_name} {column_type}"
        )
    _logger.info("Ensured approval_request hr_approval_mod columns exist in pre_init_hook")


def _rewrite_button_invisible(arch, button_name, invisible_expr):
    pattern = rf'(<button[^>]*\bname="{button_name}"[^>]*\binvisible=")([^"]*)(")'
    return re.sub(pattern, rf'\1{invisible_expr}\3', arch)


def post_init_hook(first_arg, registry=None):
    """Force Studio-created approval buttons to map to the correct category by name."""
    _cr, env = _extract_cr_env(first_arg)

    appointment_category = env['approval.category'].sudo().search([
        ('name', '=', 'დანიშვნა')
    ], limit=1)
    temporary_category = env['approval.category'].sudo().search([
        ('name', 'in', ['დანიშვნა დროებით', 'დანიშვნა დროებითი'])
    ], limit=1)

    if not appointment_category or not temporary_category:
        _logger.warning(
            "Could not find both approval categories for Studio button remap. "
            "appointment=%s temporary=%s",
            bool(appointment_category),
            bool(temporary_category),
        )
        return

    views = env['ir.ui.view'].sudo().search([
        ('model', '=', 'approval.request'),
        '|',
        ('arch_db', 'ilike', 'name="1194"'),
        ('arch_db', 'ilike', 'name="1403"'),
    ])

    for view in views:
        original_arch = view.arch_db or ''
        updated_arch = original_arch

        updated_arch = _rewrite_button_invisible(
            updated_arch,
            '1194',
            f'category_id != {appointment_category.id}',
        )
        updated_arch = _rewrite_button_invisible(
            updated_arch,
            '1403',
            f'category_id != {temporary_category.id}',
        )

        if updated_arch != original_arch:
            view.write({'arch_db': updated_arch})
            _logger.info(
                "Updated Studio approval button mapping in view %s (%s)",
                view.id,
                view.name,
            )
