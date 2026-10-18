"""Sign-up handling: decide who is let in automatically and tell owners about new requests."""

import logging

from allauth.account.signals import user_signed_up
from django.conf import settings
from django.core.mail import send_mail
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from .models import Membership

log = logging.getLogger(__name__)


@receiver(user_signed_up)
def on_signed_up(request, user, **kwargs):
    membership = Membership.for_user(user)
    no_owner_yet = not Membership.objects.filter(role=Membership.OWNER, approved=True).exclude(pk=membership.pk).exists()
    if (user.email or "").lower() in settings.OWNER_EMAILS or (not settings.OWNER_EMAILS and no_owner_yet):
        membership.role, membership.approved, membership.approved_at = Membership.OWNER, True, timezone.now()
        membership.save()
        return
    notify_owners(user)


def notify_owners(user):
    owners = Membership.objects.filter(role=Membership.OWNER, approved=True, user__is_active=True)
    recipients = [m.user.email for m in owners.select_related("user") if m.user.email]
    if not recipients:
        return
    who = user.get_full_name() or user.email
    try:
        send_mail(
            _("%(studio)s Posts: %(who)s wants access") % {"studio": settings.STUDIO_NAME, "who": who},
            _("%(who)s (%(email)s) signed up and is waiting for approval.") % {"who": who, "email": user.email}
            + "\n\n" + _("Approve or decline: %(url)s") % {"url": f"{settings.SITE_URL}{reverse('team')}"} + "\n",
            None,
            recipients,
        )
    except Exception:  # an email problem must never break sign-up
        log.exception("Could not email owners about new sign-up")
