from django.shortcuts import redirect
from django.urls import reverse

from .models import Membership

# Reachable while waiting for approval: login/logout/sign-up pages, the waiting page and public files.
OPEN_PREFIXES = ("/accounts/", "/pending/", "/static/", "/media/", "/cron/", "/i18n/")


class ApprovalMiddleware:
    """Signed-in people who haven't been approved by an owner only see the 'waiting for approval' page."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            request.membership = Membership.for_user(user)
            if (not request.membership.approved and not request.path.startswith(OPEN_PREFIXES)
                    and request.path != "/links/"):
                return redirect(reverse("pending"))
        else:
            request.membership = None
        return self.get_response(request)
