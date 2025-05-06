from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, UpdateView, CreateView
from apps.addresses.models import Address
from .models import Supplier
from .forms import SupplierForm
import logging

logger = logging.getLogger(__name__)

class SupplierListView(ListView):
    model = Supplier
    template_name = 'suppliers/list.html'
    context_object_name = 'suppliers'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '').strip()
        supplier_type = self.request.GET.get('supplier_type', 'all')
        
        # Aplica o filtro por tipo de fornecedor
        if supplier_type in ['IND', 'CORP']:
            queryset = queryset.filter(supplier_type=supplier_type)
        
        # Aplica a busca geral se houver termo de pesquisa
        if search_query:
            queryset = queryset.filter(
                Q(full_name__icontains=search_query) |
                Q(tax_id__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(contact_person__icontains=search_query))
        
        return queryset

class SupplierCreateView(CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'suppliers/supplier_form.html'
    success_url = reverse_lazy('suppliers:list')

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Salva o fornecedor primeiro para obter um ID
                supplier = form.save()

                # Prepara os dados de endereço do formulário
                address_data = {
                    "zip_code": self.request.POST.get("zip_code", "").strip(),
                    "street": self.request.POST.get("street", "").strip(),
                    "number": self.request.POST.get("number", "").strip(),
                    "complement": self.request.POST.get("complement", "").strip(),
                    "neighborhood": self.request.POST.get("neighborhood", "").strip(),
                    "city": self.request.POST.get("city", "").strip(),
                    "state": self.request.POST.get("state", "").strip().upper(),
                }

                # Remove campos vazios
                address_data = {k: v for k, v in address_data.items() if v}

                # Cria/atualiza o endereço apenas se houver dados
                if address_data:
                    content_type = ContentType.objects.get_for_model(Supplier)
                    Address.objects.update_or_create(
                        content_type=content_type,
                        object_id=supplier.pk,
                        defaults=address_data
                    )

                messages.success(self.request, "Fornecedor cadastrado com sucesso!")
                return super().form_valid(form)

        except Exception as e:
            logger.error(f"Erro ao criar fornecedor: {str(e)}", exc_info=True)
            messages.error(
                self.request,
                "Ocorreu um erro ao cadastrar o fornecedor. "
                "Por favor, verifique os dados e tente novamente."
            )
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adiciona flags para o template controlar os botões de busca
        context['show_cnpj_button'] = True
        context['show_cep_button'] = True
        return context

class SupplierDetailView(DetailView):
    model = Supplier
    template_name = 'suppliers/supplier_detail.html'
    context_object_name = 'supplier'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supplier = self.get_object()
        
        # Adiciona o endereço ao contexto se existir
        context['address'] = supplier.addresses.first()
        
        # Formatações adicionais
        context['formatted_tax_id'] = supplier.formatted_tax_id()
        context['formatted_phone'] = supplier.formatted_phone
        
        return context

class SupplierUpdateView(UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'suppliers/supplier_form.html'
    success_url = reverse_lazy('suppliers:list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supplier = self.get_object()
        
        # Adiciona o endereço ao contexto se existir
        address = supplier.addresses.first()
        if address:
            context['address'] = address
            # Preenche os valores iniciais para os campos de endereço
            self.initial.update({
                'zip_code': address.zip_code,
                'street': address.street,
                'number': address.number,
                'complement': address.complement,
                'neighborhood': address.neighborhood,
                'city': address.city,
                'state': address.state,
            })
        
        # Mantém os botões de busca ativos conforme o tipo de fornecedor
        context['show_cnpj_button'] = supplier.supplier_type == 'CORP'
        context['show_cep_button'] = supplier.supplier_type == 'IND'
        
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Salva o fornecedor primeiro para obter um ID
                supplier = form.save()

                # Prepara os dados de endereço do formulário
                address_data = {
                    "zip_code": self.request.POST.get("zip_code", "").strip(),
                    "street": self.request.POST.get("street", "").strip(),
                    "number": self.request.POST.get("number", "").strip(),
                    "complement": self.request.POST.get("complement", "").strip(),
                    "neighborhood": self.request.POST.get("neighborhood", "").strip(),
                    "city": self.request.POST.get("city", "").strip(),
                    "state": self.request.POST.get("state", "").strip().upper(),
                }

                # Remove campos vazios
                address_data = {k: v for k, v in address_data.items() if v}

                # Cria/atualiza o endereço apenas se houver dados
                if address_data:
                    content_type = ContentType.objects.get_for_model(Supplier)
                    Address.objects.update_or_create(
                        content_type=content_type,
                        object_id=supplier.pk,
                        defaults=address_data
                    )
                else:
                    # Se não houver dados de endereço, remove o existente
                    supplier.addresses.all().delete()

                messages.success(self.request, "Fornecedor atualizado com sucesso!")
                return super().form_valid(form)

        except Exception as e:
            logger.error(f"Erro ao atualizar fornecedor: {str(e)}", exc_info=True)
            messages.error(
                self.request,
                "Ocorreu um erro ao atualizar o fornecedor. "
                "Por favor, verifique os dados e tente novamente."
            )
            return self.form_invalid(form)