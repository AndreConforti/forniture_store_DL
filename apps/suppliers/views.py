from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.http import JsonResponse
from .models import Supplier
from .forms import SupplierForm
from core.services import fetch_company_data, fetch_address_data


class SupplierListView(ListView):
    model = Supplier
    template_name = 'suppliers/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 20
    ordering = ['-registration_date']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filtro por tipo (opcional)
        supplier_type = self.request.GET.get('type')
        if supplier_type in ['IND', 'CORP']:
            queryset = queryset.filter(supplier_type=supplier_type)
        return queryset


class SupplierCreateView(SuccessMessageMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'suppliers/supplier_form.html'
    success_url = reverse_lazy('suppliers:list')
    success_message = "Fornecedor cadastrado com sucesso!"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, self.success_message)
        return response


class SupplierUpdateView(SuccessMessageMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'suppliers/supplier_form.html'
    success_url = reverse_lazy('suppliers:list')
    success_message = "Fornecedor atualizado com sucesso!"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, self.success_message)
        return response


class SupplierDetailView(DetailView):
    model = Supplier
    template_name = 'suppliers/supplier_detail.html'
    context_object_name = 'supplier'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['address'] = self.object.address  # Acessa o endereço via GenericRelation
        return context

