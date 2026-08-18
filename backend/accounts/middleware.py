from django.contrib.auth import logout


class SessionVersionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            current = request.session.get("auth_session_version")
            if current != request.user.session_version:
                logout(request)
        return self.get_response(request)
