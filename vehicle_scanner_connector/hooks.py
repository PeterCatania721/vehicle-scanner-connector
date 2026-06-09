import logging

_logger = logging.getLogger(__name__)


def post_init_hook(cr_or_env, registry=None):
    """Load default panel mappings and ensure a single active configuration."""
    if registry is None:
        env = cr_or_env
    else:
        from odoo import api, SUPERUSER_ID
        env = api.Environment(cr_or_env, SUPERUSER_ID, {})

    Config = env['vehicle.scanner.config'].sudo()
    configs = Config.search([])
    if not configs:
        Config.create({
            'name': 'Default Vehicle Scanner API',
            'username': 'ai_scanner',
            'password': 'change-me-on-install',
        })
        configs = Config.search([])

    active = configs.filtered('active')
    if len(active) > 1:
        active[1:].write({'active': False})
        _logger.warning(
            'Multiple active Vehicle Scanner configs found; kept only %s',
            active[0].name,
        )
    elif not active and configs:
        configs[0].write({'active': True})

    config = Config.get_active_config()
    if not config.panel_mapping_ids:
        config.action_load_default_panel_mappings()
        _logger.info('Loaded default BUHDA panel mappings for %s', config.name)