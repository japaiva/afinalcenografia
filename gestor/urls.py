from django.urls import path
from . import views

app_name = 'gestor'

urlpatterns = [
    path('', views.index, name='index'),
]