from django.urls import path
from .views import custom_login, custom_logout

app_name = 'employees'

urlpatterns = [
    path('login/', custom_login, name='login'),
    path('logout/', custom_logout, name='logout'),
]