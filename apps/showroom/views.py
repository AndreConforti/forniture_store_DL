from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.customers.models import Customer


def dashboard(request):
    customers = Customer.objects.all()  
    cards_data = [
        {
            'title': 'Pedidos Hoje',
            'value': '12',
            'icon': 'bi-cart3',
            'color': 'primary'
        },
        {
            'title': 'Produtos em Falta',
            'value': '5',
            'icon': 'bi-exclamation-triangle',
            'color': 'warning'
        },
        {
            'title': 'Receita Mensal',
            'value': 'R$ 28,540',
            'icon': 'bi-currency-dollar',
            'color': 'success'
        },
        {
            'title': 'Clientes',
            'value': customers.count(),
            'icon': 'bi-person-plus',
            'color': 'info'
        }
    ]
    
    return render(request, 'showroom/dashboard.html', {'cards': cards_data})