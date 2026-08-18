from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


@receiver(user_logged_in)
def record_session_version(sender, request, user, **kwargs):
    if request is not None:
        request.session["auth_session_version"] = user.session_version
