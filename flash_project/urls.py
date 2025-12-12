from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.shortcuts import redirect
from django.conf.urls.static import static
import os


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
else:
    # Opcional: servir mídia em produção sem CDN, controlado por env
    if os.getenv("DJANGO_SERVE_MEDIA", "False") == "True":
        from django.views.static import serve
        from django.urls import re_path
        urlpatterns += [
            re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT})
        ]
