from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),  # ← ЭТО ОБЯЗАТЕЛЬНО ДОЛЖНО БЫТЬ
    path('', include('apps.shop.urls')),  # Твой магазин
]