"""Routes package - exposes init helpers for app wiring.

Keeping these functions re-exported allows existing import sites to use
`from routes_pkg import init_routes` (or direct module imports).
"""

from .routes import init_routes  # re-export
from .routes_appointments import init_appointments_routes
from .routes_calendar import init_calendar_routes
from .routes_inventory import init_inventory_routes
from .routes_services import init_services_routes
from .routes_user_documents import init_document_routes

__all__ = [
    'init_routes',
    'init_appointments_routes',
    'init_calendar_routes',
    'init_inventory_routes',
    'init_services_routes',
    'init_document_routes',
]
