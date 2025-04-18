from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from core.views import home_view, perfil,logout_view


from scripts.debug_views import debug_search_view


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Views de autenticação compartilhadas
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    #path('logout/', auth_views.LogoutView.as_view(next_page='gestor:home'), name='logout'),
    path('perfil/', perfil, name='perfil'),
    path('logout/', logout_view, name='logout'),  # Alterado para usar sua própria view

    # Página inicial do site
    path('', home_view, name='home'),

    path('debug-search/', debug_search_view, name='debug-search'),
    
    # Portais específicos
    path('gestor/', include('gestor.urls')),
    path('cliente/', include('cliente.urls', namespace='cliente')),
    path('projetista/', include('projetista.urls', namespace='projetista')),
    
    # APIs e outros apps
    path('api/', include('api.urls', namespace='api')),
]

# Adicionar URLs para servir mídia durante o desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)