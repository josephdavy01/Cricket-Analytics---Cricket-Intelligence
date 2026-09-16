"""
URL configuration for ipl_frontend project.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('cricket.urls')),
]
