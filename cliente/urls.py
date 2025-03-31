from django.urls import path
from django.views.generic import TemplateView

app_name = 'cliente'

urlpatterns = [
    # Página temporária - será substituída por views reais no futuro
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('dashboard/', TemplateView.as_view(template_name='home.html'), name='dashboard'),
]