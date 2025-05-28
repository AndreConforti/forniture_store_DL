from django.contrib import admin
from django.urls import path, include
from django.conf import settings


urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('apps.employees.urls')),
    path('', include('apps.showroom.urls')),
    path('customers/', include('apps.customers.urls')),
    path('docs/', include('apps.docs.urls')),
    # path('suppliers/', include('apps.suppliers.urls')),
    # path('products', include('apps.products.urls')),
    # path('reports/', include('apps.reports.urls')),
]

# A configuração de servir MEDIA ainda pode ser útil em desenvolvimento,
# mas para arquivos ESTÁTICOS, vamos depender de outra solução em produção.
if settings.DEBUG:
    # Remova a linha de STATIC_URL aqui se for usar WhiteNoise,
    # ou mantenha se for usar Nginx/Apache e quiser testar a coleta localmente.
    # A melhor prática é não depender disso para estáticos com DEBUG=False.
    from django.conf.urls.static import static # Importar apenas se DEBUG for True
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) # Para desenvolvimento
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) # Para desenvolvimento