from django.urls import path
from . import auth_views_custom

app_name = "auth"

urlpatterns = [
    path("login/", auth_views_custom.login_view, name="login"),
    path("register/", auth_views_custom.register_view, name="register"),
    path("logout/", auth_views_custom.logout_view, name="logout"),
]
