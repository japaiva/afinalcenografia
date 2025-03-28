from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from core.views import redirect_by_user_level

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('cliente/', include('cliente.urls')),
    path('projetista/', include('projetista.urls')),
    path('gestor/', include('gestor.urls')),
    path('admin-portal/', include('admin_portal.urls')),
    
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    
    # Redireciona a raiz para o app apropriado com base no nível do usuário
    path('', redirect_by_user_level, name='index'),
]

# Para servir arquivos estáticos no modo dev
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)