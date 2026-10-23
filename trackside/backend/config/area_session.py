"""
Trackside — One sign-in per role area, so two roles can be signed in at once in one browser.

A browser keeps one cookie jar for the whole site, so with a single session cookie, signing in as the coach in
one tab turns every other tab into the coach too (a driver tab would suddenly be acting as the coach). Here each
role has its own session cookie (sessionid_driver, sessionid_coach, sessionid_admin). The page says which area it
belongs to with the X-Trackside-Area header (WebSocket: ?area=), and the server reads and writes only that
area's cookie. Rights still come from the account's own role on every request; the area only picks which of the
browser's own cookies is used, so it cannot give anyone more than their account already has.

No header: the old single cookie is used exactly as before (tests, scripts, older pages).
Header "auto" on the login request: the cookie is chosen by the role of the account that signed in.
"""

import time
from urllib.parse import parse_qs

from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.sessions.backends.base import UpdateError
from django.contrib.sessions.exceptions import SessionInterrupted
from django.utils.cache import patch_vary_headers
from django.utils.http import http_date

AREAS = ("admin", "coach", "driver")
AREA_HEADER = "HTTP_X_TRACKSIDE_AREA"
AUTO = "auto"
PENDING_COOKIE_NAME = "sessionid_pending"   # never sent by a browser: a login that has not chosen its cookie yet


def clean_area(value):
    """The area if it is one of the three role areas, otherwise None."""
    return value if value in AREAS else None


def cookie_name_for(area) -> str:
    """The session cookie name of an area (the old single name when there is no area)."""
    return f"{settings.SESSION_COOKIE_NAME}_{area}" if area in AREAS else settings.SESSION_COOKIE_NAME


class AreaSessionMiddleware(SessionMiddleware):
    """Django's session middleware, reading and writing the cookie of the page's role area."""

    def process_request(self, request):
        """Open the session stored under the area's own cookie (a login with "auto" starts a fresh session)."""
        header = request.META.get(AREA_HEADER)
        if header == AUTO:
            # The login view picks the cookie once it knows the account's role; until then nothing is read or deleted
            request.session_cookie_name = PENDING_COOKIE_NAME
            request.session = self.SessionStore(None)
            return
        request.session_cookie_name = cookie_name_for(clean_area(header))
        request.session = self.SessionStore(request.COOKIES.get(request.session_cookie_name))

    def process_response(self, request, response):
        """Save the session and set (or delete) the area's cookie; the same steps as Django's own middleware."""
        try:
            accessed = request.session.accessed
            modified = request.session.modified
            empty = request.session.is_empty()
        except AttributeError:
            return response
        name = getattr(request, "session_cookie_name", settings.SESSION_COOKIE_NAME)
        if name in request.COOKIES and empty:
            response.delete_cookie(
                name,
                path=settings.SESSION_COOKIE_PATH,
                domain=settings.SESSION_COOKIE_DOMAIN,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )
            need_vary_cookie = True
        else:
            need_vary_cookie = accessed
            if (modified or settings.SESSION_SAVE_EVERY_REQUEST) and not empty:
                if request.session.get_expire_at_browser_close():
                    max_age = None
                    expires = None
                else:
                    max_age = request.session.get_expiry_age()
                    expires = http_date(time.time() + max_age)
                if response.status_code < 500:
                    try:
                        request.session.save()
                    except UpdateError:
                        raise SessionInterrupted(
                            "The request's session was deleted before the request completed. "
                            "The user may have logged out in a concurrent request, for example."
                        )
                    response.set_cookie(
                        name,
                        request.session.session_key,
                        max_age=max_age,
                        expires=expires,
                        domain=settings.SESSION_COOKIE_DOMAIN,
                        path=settings.SESSION_COOKIE_PATH,
                        secure=settings.SESSION_COOKIE_SECURE or None,
                        httponly=settings.SESSION_COOKIE_HTTPONLY or None,
                        samesite=settings.SESSION_COOKIE_SAMESITE,
                    )
                    need_vary_cookie = True
        if need_vary_cookie:
            patch_vary_headers(response, ("Cookie",))
        return response


class AreaCookieMiddleware:
    """
    For WebSockets: when the address says ?area=driver, hand the inner session middleware that area's cookie as
    the session cookie, and hide the others. Without ?area= nothing changes.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        """Swap in the chosen area's cookie, then pass the connection on."""
        wanted = parse_qs(scope.get("query_string", b"").decode("latin1")).get("area", [None])[0]
        area = clean_area(wanted)
        if area:
            cookies = dict(scope.get("cookies", {}))
            chosen = cookies.get(cookie_name_for(area))
            cookies.pop(settings.SESSION_COOKIE_NAME, None)
            if chosen:
                cookies[settings.SESSION_COOKIE_NAME] = chosen
            scope = dict(scope, cookies=cookies)
        return await self.inner(scope, receive, send)
