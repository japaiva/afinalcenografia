from django.urls import path
from ..core import views

app_name = 'cliente'

urlpatterns = [
    path('', views.index, name='index'),
]