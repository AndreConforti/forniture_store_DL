from django.urls import path
from .views import (
    CustomerListView, 
    CustomerDetailView, 
    CustomerUpdateView,
    customer_create_view, 
    fetch_company_data
)

app_name = 'customers'  # Namespace para URLs (opcional, mas recomendado)

urlpatterns = [
    path('', CustomerListView.as_view(), name='list'),
    path('create/', customer_create_view, name='create'),	
    path('<int:pk>/', CustomerDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', CustomerUpdateView.as_view(), name='edit'),
    path('search-cnpj/', fetch_company_data, name='search_cnpj')
]