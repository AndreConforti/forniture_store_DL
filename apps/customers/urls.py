from django.urls import path
from .views import (
    CustomerListView, 
    CustomerDetailView, 
    CustomerUpdateView,
    customer_create_view, 
)

app_name = 'customers'  # Namespace para URLs (opcional, mas recomendado)

urlpatterns = [
    path('', CustomerListView.as_view(), name='list'),
    path('create/', customer_create_view, name='create'),	
    path('<int:pk>/', CustomerDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', CustomerUpdateView.as_view(), name='edit'),
]