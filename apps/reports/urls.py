# reports/urls.py
from django.urls import path
from .views import CustomerReportView

app_name = 'reports'

urlpatterns = [
    path('customers/', CustomerReportView.as_view(), name='customer_report'),
]