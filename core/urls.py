from django.urls import path, include
from django.contrib import admin
from apps.shop.admin import admin

urlpatterns = [
    path('admin/', admin.site.urls),
]
