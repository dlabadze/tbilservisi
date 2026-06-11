import logging

_logger = logging.getLogger(__name__)

# Models that were historically deleted with raw SQL while their FK
# constraints were missing, leaving orphan references behind. Any orphan
# pointing to these models blocks check_foreign_keys() during the upgrade
# of a module that touches account.move.
TARGET_MODELS = (
    'account.move',
    'account.move.line',
    'account.payment',
    'account.bank.statement',
    'account.bank.statement.line',
    'account.full.reconcile',
    'account.partial.reconcile',
)


def _table_exists(cr, table):
    cr.execute("SELECT to_regclass(%s)", (table,))
    return cr.fetchone()[0] is not None


def _column_exists(cr, table, column):
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return bool(cr.fetchone())


def _cleanup(cr, table, column, ref_table, action):
    """Backup then remove/null orphan references in table.column -> ref_table.id."""
    orphan_condition = (
        f't."{column}" IS NOT NULL AND NOT EXISTS '
        f'(SELECT 1 FROM "{ref_table}" r WHERE r.id = t."{column}")'
    )

    cr.execute(f'SELECT count(*) FROM "{table}" t WHERE {orphan_condition}')
    count = cr.fetchone()[0]
    if not count:
        return

    # Backup table names stay under PG's 63 char identifier limit
    backup = f'_orphan_bak__{table}'[:63]
    cr.execute(
        f'CREATE TABLE IF NOT EXISTS "{backup}" AS SELECT t.* FROM "{table}" t WHERE false'
    )
    cr.execute(
        f'INSERT INTO "{backup}" SELECT t.* FROM "{table}" t WHERE {orphan_condition}'
    )

    if action == 'set null':
        cr.execute(f'UPDATE "{table}" t SET "{column}" = NULL WHERE {orphan_condition}')
        _logger.warning(
            "account_kveba migration: set %s.%s to NULL on %s orphan rows "
            "(backup in table %s)", table, column, count, backup,
        )
    else:
        cr.execute(f'DELETE FROM "{table}" t WHERE {orphan_condition}')
        _logger.warning(
            "account_kveba migration: deleted %s orphan rows from %s "
            "referencing missing %s records (backup in table %s)",
            count, table, ref_table, backup,
        )


def migrate(cr, version):
    if not version:
        return

    # Many2one columns pointing to one of the target models
    cr.execute(
        """
        SELECT replace(m.model, '.', '_') AS table,
               f.name AS column,
               replace(f.relation, '.', '_') AS ref_table,
               coalesce(f.on_delete, 'set null') AS on_delete
        FROM ir_model_fields f
        JOIN ir_model m ON m.id = f.model_id
        WHERE f.ttype = 'many2one' AND f.store AND f.relation IN %s
        """,
        (TARGET_MODELS,),
    )
    for table, column, ref_table, on_delete in cr.fetchall():
        if not (_table_exists(cr, table) and _table_exists(cr, ref_table)
                and _column_exists(cr, table, column)):
            continue
        action = 'set null' if on_delete == 'set null' else 'delete'
        _cleanup(cr, table, column, ref_table, action)

    # Many2many relation tables: orphan rows are deleted on either side
    cr.execute(
        """
        SELECT f.relation_table AS table,
               f.column2 AS column,
               replace(f.relation, '.', '_') AS ref_table
        FROM ir_model_fields f
        WHERE f.ttype = 'many2many' AND f.store
          AND f.relation_table IS NOT NULL AND f.column2 IS NOT NULL
          AND f.relation IN %s
        UNION
        SELECT f.relation_table, f.column1, replace(m.model, '.', '_')
        FROM ir_model_fields f
        JOIN ir_model m ON m.id = f.model_id
        WHERE f.ttype = 'many2many' AND f.store
          AND f.relation_table IS NOT NULL AND f.column1 IS NOT NULL
          AND m.model IN %s
        """,
        (TARGET_MODELS, TARGET_MODELS),
    )
    for table, column, ref_table in cr.fetchall():
        if not (_table_exists(cr, table) and _table_exists(cr, ref_table)
                and _column_exists(cr, table, column)):
            continue
        _cleanup(cr, table, column, ref_table, 'delete')
