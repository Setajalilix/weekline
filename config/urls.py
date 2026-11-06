from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("favicon.ico", RedirectView.as_view(url="/static/favicon.ico", permanent=False)),
    path("admin/", admin.site.urls),
    path("", include("performance.urls")),
]
