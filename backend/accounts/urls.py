from django.urls import path

from .views import LoginView, LogoutAllView, LogoutView, MeView, PasswordChangeView, csrf

urlpatterns = [
    path("csrf/", csrf, name="csrf"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("logout-all/", LogoutAllView.as_view(), name="logout-all"),
    path("password/", PasswordChangeView.as_view(), name="password-change"),
    path("me/", MeView.as_view(), name="me"),
]
