from django.urls import path
from apps.shop.views import index

urlpatterns = [
    path('', index, name='index'),
]
