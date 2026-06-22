import logging
import re

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def pre_init_hook(cr):
    """Ensure legacy DBs have the column before FK checks run on install."""
    cr.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'approval_request'
          AND column_name = 'brdzaneba_employee_id'
        """
    )
    if not cr.fetchone():
        cr.execute("ALTER TABLE approval_request ADD COLUMN brdzaneba_employee_id integer")
        _logger.info("Added missing column approval_request.brdzaneba_employee_id in pre_init_hook")


def _rewrite_button_invisible(arch, button_name, invisible_expr):
    pattern = rf'(<button[^>]*\bname="{button_name}"[^>]*\binvisible=")([^"]*)(")'
    return re.sub(pattern, rf'\1{invisible_expr}\3', arch)


def post_init_hook(cr, registry):
    """Force Studio-created approval buttons to map to the correct category by name."""
    env = api.Environment(cr, SUPERUSER_ID, {})

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
