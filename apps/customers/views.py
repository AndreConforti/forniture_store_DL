from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, UpdateView, CreateView
from apps.addresses.models import Address
from .models import Customer
from .forms import CustomerForm
import logging


logger = logging.getLogger(__name__)


class CustomerListView(ListView):
    model = Customer
    template_name = 'customers/list.html'
    context_object_name = 'customers'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '').strip()
        customer_type = self.request.GET.get('customer_type', 'all')
        
        # Aplica o filtro por tipo de cliente
        if customer_type in ['IND', 'CORP']:
            queryset = queryset.filter(customer_type=customer_type)
        
        # Aplica a busca geral se houver termo de pesquisa
        if search_query:
            queryset = queryset.filter(
                Q(full_name__icontains=search_query) |
                Q(tax_id__icontains=search_query) |
                Q(email__icontains=search_query))
        
        return queryset
 

class CustomerCreateView(CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:list')

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Salva o cliente primeiro para obter um ID
                customer = form.save()

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
                    content_type = ContentType.objects.get_for_model(Customer)
                    Address.objects.update_or_create(
                        content_type=content_type,
                        object_id=customer.pk,
                        defaults=address_data
                    )

                messages.success(self.request, "Cliente cadastrado com sucesso!")
                return super().form_valid(form)

        except Exception as e:
            logger.error(f"Erro ao criar cliente: {str(e)}", exc_info=True)
            messages.error(
                self.request,
                "Ocorreu um erro ao cadastrar o cliente. "
                "Por favor, verifique os dados e tente novamente."
            )
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adiciona flags para o template controlar os botões de busca
        context['show_cnpj_button'] = True
        context['show_cep_button'] = True
        return context


class CustomerDetailView(DetailView):
    model = Customer
    template_name = 'customers/customer_detail.html'
    context_object_name = 'customer'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.get_object()
        
        # Adiciona o endereço ao contexto se existir
        context['address'] = customer.addresses.first()
        
        # Formatações adicionais
        context['formatted_tax_id'] = customer.formatted_tax_id()
        context['formatted_phone'] = customer.formatted_phone
        
        return context


class CustomerUpdateView(UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.get_object()
        
        # Adiciona o endereço ao contexto se existir
        address = customer.addresses.first()
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
        
        # Mantém os botões de busca ativos conforme o tipo de cliente
        context['show_cnpj_button'] = customer.customer_type == 'CORP'
        context['show_cep_button'] = customer.customer_type == 'IND'
        
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Salva o cliente primeiro para obter um ID
                customer = form.save()

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
                    content_type = ContentType.objects.get_for_model(Customer)
                    Address.objects.update_or_create(
                        content_type=content_type,
                        object_id=customer.pk,
                        defaults=address_data
                    )
                else:
                    # Se não houver dados de endereço, remove o existente
                    customer.addresses.all().delete()

                messages.success(self.request, "Cliente atualizado com sucesso!")
                return super().form_valid(form)

        except Exception as e:
            logger.error(f"Erro ao atualizar cliente: {str(e)}", exc_info=True)
            messages.error(
                self.request,
                "Ocorreu um erro ao atualizar o cliente. "
                "Por favor, verifique os dados e tente novamente."
            )
            return self.form_invalid(form)
