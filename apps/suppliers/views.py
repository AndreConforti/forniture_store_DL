# apps/suppliers/views.py
from django.contrib import messages
# from django.contrib.contenttypes.models import ContentType # Não é mais necessário aqui
# from django.db import transaction # Não é mais necessário aqui, o form/model lidam com isso
from django.db.models import Q
from django.forms import ValidationError as DjangoFormsValidationError # Importado para tratamento de erro
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, UpdateView, CreateView
from django.http import HttpResponseRedirect # Importado para form_valid

# from apps.addresses.models import Address # Não é mais necessário aqui
from .models import Supplier
from .forms import SupplierForm
import logging

logger = logging.getLogger(__name__)

class SupplierListView(ListView):
    """
    View para listar fornecedores com funcionalidades de busca e filtragem.
    """
    model = Supplier
    template_name = 'suppliers/supplier_list.html' # Atualizar para o nome correto do template
    context_object_name = 'suppliers'
    paginate_by = 10

    def get_queryset(self):
        """
        Constrói e retorna o queryset de fornecedores a ser exibido.
        Filtra por `is_active=True` (se desejado, como em Customer) e aplica
        filtros de busca e tipo de fornecedor.
        """
        # Se quiser listar apenas ativos por padrão, como em CustomerListView:
        # queryset = super().get_queryset().filter(is_active=True)
        queryset = super().get_queryset() # Ou liste todos e filtre no template/admin

        search_query = self.request.GET.get('search', '').strip()
        supplier_type = self.request.GET.get('supplier_type', 'all')

        if supplier_type in ['IND', 'CORP']:
            queryset = queryset.filter(supplier_type=supplier_type)

        if search_query:
            # Para tax_id, buscar pelo valor limpo (só números)
            cleaned_search_query_for_tax_id = "".join(filter(str.isdigit, search_query))
            query_conditions = (
                Q(full_name__icontains=search_query) |
                Q(preferred_name__icontains=search_query) | # Adicionado preferred_name à busca
                Q(email__icontains=search_query) |
                Q(contact_person__icontains=search_query)
            )
            if cleaned_search_query_for_tax_id:
                query_conditions |= Q(tax_id__icontains=cleaned_search_query_for_tax_id)
            
            queryset = queryset.filter(query_conditions)
        
        # Prefetch addresses para otimizar, como em Customer
        return queryset.prefetch_related('addresses')

    def get_context_data(self, **kwargs):
        """
        Adiciona parâmetros de filtro e busca ao contexto.
        """
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_supplier_type'] = self.request.GET.get('supplier_type', 'all') # Renomeado para clareza
        return context


class SupplierCreateView(CreateView):
    """
    View para a criação de um novo fornecedor.
    """
    model = Supplier
    form_class = SupplierForm
    template_name = 'suppliers/supplier_form.html' # Atualizar para o nome correto do template
    success_url = reverse_lazy('suppliers:list')

    def form_valid(self, form) -> HttpResponseRedirect:
        """
        Processa o formulário quando válido.
        A lógica de salvar o fornecedor e seu endereço agora está encapsulada
        no SupplierForm e Supplier model.
        """
        try:
            # O form.save() agora lida com a passagem de address_data para o modelo.
            self.object = form.save()
            messages.success(self.request, "Fornecedor cadastrado com sucesso!")
            return super().form_valid(form)
        except DjangoFormsValidationError as e: # Captura erros de validação do modelo/form
            logger.error(
                f"Erro de validação ao criar fornecedor: {e.message_dict if hasattr(e, 'message_dict') else e}",
                exc_info=True
            )
            # Constrói uma mensagem de erro mais detalhada se possível
            error_message = "Erro de validação. Verifique os campos: "
            if hasattr(e, 'message_dict'):
                field_errors = []
                for field, errors in e.message_dict.items():
                    field_label = form.fields.get(field).label if field in form.fields else field
                    field_errors.append(f"{field_label}: {', '.join(errors)}")
                error_message += "; ".join(field_errors)
            else:
                error_message = "Erro de validação. Verifique os campos."

            messages.error(self.request, error_message)
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Erro inesperado ao criar fornecedor: {str(e)}", exc_info=True)
            messages.error(self.request, "Ocorreu um erro inesperado ao cadastrar o fornecedor.")
            return self.form_invalid(form)

    def get_context_data(self, **kwargs) -> dict:
        """
        Adiciona dados de contexto para o template do formulário.
        """
        context = super().get_context_data(**kwargs)
        context['form_title'] = "Cadastrar Novo Fornecedor" # Título do formulário
        # Flags para JS, como em Customer (se necessário para botões CNPJ/CEP)
        context['show_cnpj_button_logic'] = True
        context['show_cep_button_logic'] = True
        return context


class SupplierDetailView(DetailView):
    """
    View para exibir os detalhes de um fornecedor específico.
    """
    model = Supplier
    template_name = 'suppliers/supplier_detail.html' # Atualizar para o nome correto do template
    context_object_name = 'supplier'

    def get_context_data(self, **kwargs) -> dict:
        """
        Adiciona o endereço e outros dados formatados ao contexto.
        """
        context = super().get_context_data(**kwargs)
        supplier = self.get_object()
        context['address'] = supplier.address # Usando a property do modelo
        # As properties formatadas (formatted_tax_id, formatted_phone) já estão no modelo
        # e podem ser acessadas diretamente no template como {{ supplier.formatted_tax_id }}
        # Não precisa adicionar explicitamente ao contexto se o nome do objeto é 'supplier'.
        return context


class SupplierUpdateView(UpdateView):
    """
    View para atualizar os dados de um fornecedor existente.
    """
    model = Supplier
    form_class = SupplierForm
    template_name = 'suppliers/supplier_form.html' # Atualizar para o nome correto do template
    success_url = reverse_lazy('suppliers:list')

    def form_valid(self, form) -> HttpResponseRedirect:
        """
        Processa o formulário quando válido para atualização.
        """
        try:
            self.object = form.save()
            messages.success(self.request, "Fornecedor atualizado com sucesso!")
            return super().form_valid(form)
        except DjangoFormsValidationError as e: # Captura erros de validação do modelo/form
            logger.error(
                f"Erro de validação ao atualizar fornecedor: {e.message_dict if hasattr(e, 'message_dict') else e}",
                exc_info=True
            )
            error_message = "Erro de validação. Verifique os campos: "
            if hasattr(e, 'message_dict'):
                field_errors = []
                for field, errors in e.message_dict.items():
                    field_label = form.fields.get(field).label if field in form.fields else field
                    field_errors.append(f"{field_label}: {', '.join(errors)}")
                error_message += "; ".join(field_errors)
            else:
                error_message = "Erro de validação. Verifique os campos."
            messages.error(self.request, error_message)
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Erro inesperado ao atualizar fornecedor: {str(e)}", exc_info=True)
            messages.error(self.request, "Ocorreu um erro inesperado ao atualizar o fornecedor.")
            return self.form_invalid(form)

    def get_context_data(self, **kwargs) -> dict:
        """
        Adiciona dados de contexto para o template do formulário de edição.
        """
        context = super().get_context_data(**kwargs)
        context['form_title'] = "Editar Fornecedor" # Título do formulário
        # O SupplierForm.__init__ já lida com o preenchimento dos campos de endereço
        # e a lógica de mostrar/esconder campos fiscais baseada no tipo.
        context['show_cnpj_button_logic'] = True # (self.object.supplier_type == 'CORP' if self.object else True)
        context['show_cep_button_logic'] = True  # (self.object.supplier_type == 'IND' if self.object else True)
        # O JS no template (supplier_form.js) deve lidar com a habilitação/desabilitação dinâmica
        # desses botões com base no tipo de fornecedor selecionado.
        return context