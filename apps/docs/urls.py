from django.urls import path
from . import views

app_name = "docs"
urlpatterns = [
    path("", views.tutorial_index_view, name="index"),
    path("authentication/", views.tutorial_authentication_view, name="authentication"),
    path(
        "password-recovery/",
        views.tutorial_password_recovery_view,
        name="password_recovery",
    ),
    path(
        "customers/overview/",
        views.tutorial_customers_overview_view,
        name="customers_overview",
    ),
    path(
        "customers/create/",
        views.tutorial_customers_create_view,
        name="customers_create",
    ),
    path(
        "customers/manage/",
        views.tutorial_customers_manage_view,
        name="customers_manage",
    ),
    path("reports/", views.tutorial_reports_overview_view, name="reports_overview"),
    path(
        "reports/customers/",
        views.tutorial_reports_customers_view,
        name="reports_customers",
    ),
]
