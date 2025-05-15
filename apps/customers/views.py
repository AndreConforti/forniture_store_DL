from django.contrib import messages
from django.db.models import Q
from django.forms import ValidationError
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, UpdateView, CreateView

from .models import Customer
from .forms import CustomerForm
import logging

logger = logging.getLogger(__name__)


class CustomerListView(ListView):
    """
    View para listar clientes ativos com filtros e paginação.
    Permite buscar por nome, CPF/CNPJ, email e filtrar por tipo de cliente.
    Exibe apenas clientes com `is_active=True`.
    """
    model = Customer
    template_name = 'customers/list.html'
    context_object_name = 'customers'
    paginate_by = 30 
    
    def get_queryset(self):
        """
        Retorna o queryset de clientes ativos, filtrado conforme os parâmetros da URL.
        """
        # Começa com o queryset base do modelo, já filtrando por is_active=True
        queryset = super().get_queryset().filter(is_active=True)

        search_query = self.request.GET.get('search', '').strip()
        customer_type = self.request.GET.get('customer_type', 'all')

        # Aplica o filtro por tipo de cliente (IND ou CORP)
        if customer_type in ['IND', 'CORP']:
            queryset = queryset.filter(customer_type=customer_type)

        # Aplica a busca geral se houver termo de pesquisa
        if search_query:
            # Limpa o search_query para busca no tax_id (que é armazenado sem máscara)
            cleaned_search_query_for_tax_id = "".join(filter(str.isdigit, search_query))

            # Constrói as condições de busca
            query_conditions = (
                Q(full_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(preferred_name__icontains=search_query) # Adicionado preferred_name aqui para cobrir todos os casos
            )

            if cleaned_search_query_for_tax_id:
                query_conditions |= Q(tax_id__icontains=cleaned_search_query_for_tax_id)
            # Não precisamos de um 'else' aqui para preferred_name, pois ele já está incluído nas condições base.

            queryset = queryset.filter(query_conditions)

        # Aplica otimizações de queryset (prefetch_related para endereços, se necessário na lista)
        # select_related(None) não é tipicamente usado, a menos que você queira explicitamente
        # limpar quaisquer select_related definidos anteriormente.
        # Se você não precisa dos endereços na listagem, pode remover o prefetch_related('addresses').
        # Se precisar, mantenha-o.
        return queryset.prefetch_related('addresses')

    def get_context_data(self, **kwargs):
        """Adiciona os parâmetros de filtro atuais ao contexto para uso no template."""
        # É uma boa prática chamar o método da superclasse primeiro.
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_customer_type'] = self.request.GET.get('customer_type', 'all')
        return context


class CustomerCreateView(CreateView):
    """
    View para criar um novo cliente.
    Utiliza CustomerForm para validação e Customer.save() para persistência,
    incluindo o gerenciamento do endereço.
    """
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:list')

    def form_valid(self, form):
        """
        Processa o formulário válido.
        O método save do CustomerForm e do Customer model já lidam com
        a criação do cliente e do seu endereço, incluindo chamadas à API.
        """
        try:
            # O form.save() agora passa 'address_data' para Customer.save()
            self.object = form.save()
            messages.success(self.request, "Cliente cadastrado com sucesso!")
            return super().form_valid(form)
        except ValidationError as e:
            # Erros de validação do modelo (incluindo do Address) podem ser capturados aqui
            # e adicionados ao formulário, se não forem já tratados pelo full_clean do form.
            # O full_clean do ModelForm já deve adicionar a maioria dos erros de modelo.
            logger.error(f"Erro de validação ao criar cliente: {e.message_dict if hasattr(e, 'message_dict') else e}", exc_info=True)
            messages.error(self.request, "Erro de validação. Verifique os campos.")
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Erro inesperado ao criar cliente: {str(e)}", exc_info=True)
            messages.error(self.request, "Ocorreu um erro inesperado ao cadastrar o cliente.")
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        """Adiciona dados ao contexto do template."""
        context = super().get_context_data(**kwargs)
        context['form_title'] = "Cadastrar Novo Cliente"
        # Flags para controlar botões de busca no template, se necessário.
        # A lógica de quando mostrar pode ser mais dinâmica no template (JS)
        # baseado no tipo de cliente selecionado.
        context['show_cnpj_button_logic'] = True # JS pode esconder/mostrar
        context['show_cep_button_logic'] = True  # JS pode esconder/mostrar
        return context


class CustomerDetailView(DetailView):
    """View para exibir os detalhes de um cliente."""
    model = Customer
    template_name = 'customers/customer_detail.html'
    context_object_name = 'customer'

    def get_context_data(self, **kwargs):
        """Adiciona o endereço formatado e outros dados ao contexto."""
        context = super().get_context_data(**kwargs)
        customer = self.get_object()
        context['address'] = customer.address # Usa a property do modelo
        # Campos formatados já são properties no modelo (formatted_tax_id, formatted_phone)
        return context


class CustomerUpdateView(UpdateView):
    """
    View para atualizar um cliente existente.
    Similar à CustomerCreateView, utiliza CustomerForm e a lógica de save do modelo.
    """
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:list')

    def form_valid(self, form):
        """Processa o formulário válido para atualização."""
        try:
            # O form.save() passa 'address_data' para Customer.save()
            self.object = form.save()
            messages.success(self.request, "Cliente atualizado com sucesso!")
            return super().form_valid(form)
        except ValidationError as e:
            logger.error(f"Erro de validação ao atualizar cliente: {e.message_dict if hasattr(e, 'message_dict') else e}", exc_info=True)
            messages.error(self.request, "Erro de validação. Verifique os campos.")
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Erro inesperado ao atualizar cliente: {str(e)}", exc_info=True)
            messages.error(self.request, "Ocorreu um erro inesperado ao atualizar o cliente.")
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        """Adiciona dados ao contexto, incluindo título e flags para botões."""
        context = super().get_context_data(**kwargs)
        context['form_title'] = "Editar Cliente"
        # O formulário já é inicializado com dados do endereço no seu __init__
        # Flags para botões de busca (JS pode controlar a visibilidade)
        customer = self.get_object()
        context['show_cnpj_button_logic'] = True # Default true, JS ajusta
        context['show_cep_button_logic'] = True  # Default true, JS ajusta
        return context
