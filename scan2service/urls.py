from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Main site + guest
    path("", include("website.urls")),
    path("", include("guest.urls")),

    # Hotel portal
    path("portal/", include("hotelportal.urls")),
]

# 🔸 not in basic Django, but needed for Scan2Service
# serve uploaded files (like hotel logos) in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
