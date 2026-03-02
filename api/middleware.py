from django.http import JsonResponse
from django.conf import settings
from .models import ServiceConfiguration


class MaintenanceModeMiddleware:
    """
    Middleware pour gérer le mode maintenance.
    Bloque toutes les requêtes sauf celles de l'admin si le mode maintenance est activé.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Chemins exemptés du mode maintenance
        exempt_paths = [
            '/admin/',
            '/api/docs/',
            '/api/schema/',
            '/static/',
            '/media/',
        ]

        # Vérifier si le chemin est exempté
        is_exempt = any(request.path.startswith(path) for path in exempt_paths)

        if not is_exempt:
            # Vérifier le mode maintenance depuis la base de données
            try:
                maintenance_config = ServiceConfiguration.get_maintenance_config()
                if maintenance_config and maintenance_config.is_active:
                    # Mode maintenance activé
                    message = maintenance_config.maintenance_message or settings.MAINTENANCE_MESSAGE

                    return JsonResponse({
                        'error': 'Maintenance en cours',
                        'message': message,
                        'status': 'maintenance'
                    }, status=503)

            except Exception:
                # En cas d'erreur, vérifier le settings.py en fallback
                if getattr(settings, 'MAINTENANCE_MODE', False):
                    return JsonResponse({
                        'error': 'Maintenance en cours',
                        'message': settings.MAINTENANCE_MESSAGE,
                        'status': 'maintenance'
                    }, status=503)

        response = self.get_response(request)
        return response
