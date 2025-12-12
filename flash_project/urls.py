from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.shortcuts import redirect
from django.conf.urls.static import static


def home_redirect(request):
    return redirect("/login/")

urlpatterns = [
    path("admin/", admin.site.urls),

    # Primeiras rotas: login, register, logout
    path("", include("editor.auth_urls")),     

    # Rotas do editor (inclui a rota "/")
    path("", include("editor.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
