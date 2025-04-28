from django.apps import AppConfig


class CustomersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.customers'
    verbose_name = 'Clientes'  # Nome do app que aparece no admin

    def ready(self):
        import apps.customers.signals