from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView, UpdateView
from core.services import fetch_company_data
from .models import Customer
from .forms import CustomerForm
import logging
import requests


logger = logging.getLogger(__name__)


class CustomerListView(ListView):
    model = Customer
    template_name = 'customers/list.html'
    context_object_name = 'customers'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '').strip()
        
        if search_query:
            queryset = queryset.filter(
                Q(full_name__icontains=search_query) |
                Q(tax_id__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        return queryset
 

def customer_create_view(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Cliente salvo com sucesso!")
                logger.info(f"Cliente {form.instance} salvo com sucesso.")
                return redirect('customers:list')
            except Exception as e:
                messages.error(request, "Erro ao salvar cliente.")
                logger.error(f"Erro ao salvar cliente: {e}")
        else:
            messages.warning(request, "Dados inválidos no formulário.")
            logger.warning(f"Formulário inválido: {form.errors}")

    else:
        form = CustomerForm()

    return render(request, 'customers/customer_form.html', {'form': form})


class CustomerDetailView(DetailView):
    pass

class CustomerUpdateView(UpdateView):
    pass


def fetch_company_data_view(request):
    """Endpoint para buscar dados da empresa via CNPJ"""
    tax_id = request.GET.get('tax_id', '').replace('.', '').replace('-', '').replace('/', '').strip()

    if not tax_id:
        return JsonResponse({'error': 'CNPJ não informado'}, status=400)

    data = fetch_company_data(tax_id)
    if data:
        return JsonResponse(data)

    return JsonResponse({'error': 'Não foi possível obter os dados'}, status=500)