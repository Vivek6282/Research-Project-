"""
Trackside — Never let anything store private API replies.

Every answer under /api/ belongs to the signed-in person who asked. The browser, a proxy or a service
worker must not keep it, or the next person using the same browser could be shown it (for example the
wrong account's /api/auth/me/ answer). This adds Cache-Control: no-store and Vary: Cookie to those answers.
"""

from django.utils.cache import patch_cache_control, patch_vary_headers

API_PREFIX = "/api/"


class NoStoreApiMiddleware:
    """Marks every /api/ answer as private and not to be stored."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """Run the request, then add the no-store headers when the path is under /api/."""
        response = self.get_response(request)
        if request.path.startswith(API_PREFIX):
            patch_cache_control(response, no_store=True, private=True)
            patch_vary_headers(response, ("Cookie",))
        return response
