from django.contrib import messages
from django.db.models import Q
from django.forms import ValidationError as DjangoFormsValidationError 
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, UpdateView, CreateView
from django.http import HttpResponseRedirect 

from .models import Customer
from .forms import CustomerForm
import logging

logger = logging.getLogger(__name__)


class CustomerListView(ListView):
    """
    View para listar clientes ativos com funcionalidades de busca e filtragem.

    Exibe uma lista paginada de clientes que estão marcados como `is_active=True`.
    Permite aos usuários buscar clientes por nome completo, nome fantasia,
    e-mail ou CPF/CNPJ. Adicionalmente, oferece a opção de filtrar a lista
    por tipo de cliente (Pessoa Física - IND, ou Pessoa Jurídica - CORP).

    Atributos:
        model (Model): O modelo `Customer` a ser listado.
        template_name (str): Caminho para o template HTML usado para renderizar a lista.
        context_object_name (str): Nome da variável de contexto para a lista de clientes.
        paginate_by (int): Número de clientes a serem exibidos por página.
    """
    model = Customer
    template_name = 'customers/list.html'
    context_object_name = 'customers'
    paginate_by = 10

    def get_queryset(self):
        """
        Constrói e retorna o queryset de clientes a ser exibido na lista.

        O queryset inicial inclui apenas clientes com `is_active=True`.
        Filtros são aplicados com base nos parâmetros GET da requisição:
        - `customer_type`: Filtra por tipo de cliente ('IND' ou 'CORP').
        - `search`: Realiza uma busca case-insensitive nos campos `full_name`,
          `preferred_name`, `email` e `tax_id` (após limpar o termo de busca
          para conter apenas dígitos para `tax_id`).

        Utiliza `prefetch_related('addresses')` para otimizar o acesso aos
        endereços dos clientes, caso sejam necessários no template da lista,
        evitando múltiplas consultas ao banco de dados.

        Returns:
            QuerySet: O queryset filtrado e otimizado de clientes.
        """
        queryset = super().get_queryset().filter(is_active=True)

        search_query = self.request.GET.get('search', '').strip()
        customer_type = self.request.GET.get('customer_type', 'all')

        if customer_type in ['IND', 'CORP']:
            queryset = queryset.filter(customer_type=customer_type)

        if search_query:
            cleaned_search_query_for_tax_id = "".join(filter(str.isdigit, search_query))
            query_conditions = (
                Q(full_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(preferred_name__icontains=search_query)
            )
            if cleaned_search_query_for_tax_id:
                query_conditions |= Q(tax_id__icontains=cleaned_search_query_for_tax_id)
            queryset = queryset.filter(query_conditions)

        return queryset.prefetch_related('addresses')

    def get_context_data(self, **kwargs):
        """
        Adiciona os parâmetros de filtro e busca atuais ao contexto do template.

        Isso permite que o template possa exibir os valores de filtro selecionados
        e manter o estado da busca/filtragem entre as requisições.

        Returns:
            dict: O dicionário de contexto com os dados adicionais.
        """
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_customer_type'] = self.request.GET.get('customer_type', 'all')
        return context


class CustomerCreateView(CreateView):
    """
    View para a criação de um novo cliente.

    Utiliza o `CustomerForm` para entrada de dados e validação. A lógica de
    salvamento, incluindo a criação do cliente e o gerenciamento de seu endereço
    (com potencial busca de dados via API para CNPJ e CEP), é encapsulada nos
    métodos `save()` do `CustomerForm` e do modelo `Customer`.

    Atributos:
        model (Model): O modelo `Customer` a ser criado.
        form_class (Form): O formulário `CustomerForm` para este modelo.
        template_name (str): Caminho para o template do formulário.
        success_url (str): URL para redirecionar após a criação bem-sucedida.
    """
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:list')

    def form_valid(self, form) -> HttpResponseRedirect:
        """
        Processa o formulário quando ele é considerado válido.

        Chama `form.save()` para persistir a nova instância do cliente e seu
        endereço. Exibe uma mensagem de sucesso e redireciona para a `success_url`.
        Captura `DjangoFormsValidationError` (que pode ser levantada pelo `full_clean`
        do modelo ou do endereço) e outras exceções genéricas para fornecer feedback
        ao usuário e logar o erro.

        Args:
            form (Form): A instância do formulário validado.

        Returns:
            HttpResponseRedirect: Redireciona para a `success_url` em caso de sucesso,
                                 ou renderiza novamente o formulário com erros em caso de falha.
        """
        try:
            self.object = form.save()
            messages.success(self.request, "Cliente cadastrado com sucesso!")
            return super().form_valid(form)
        except DjangoFormsValidationError as e:
            logger.error(
                f"Erro de validação ao criar cliente: {e.message_dict if hasattr(e, 'message_dict') else e}",
                exc_info=True
            )
            messages.error(self.request, "Erro de validação. Verifique os campos.")
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Erro inesperado ao criar cliente: {str(e)}", exc_info=True)
            messages.error(self.request, "Ocorreu um erro inesperado ao cadastrar o cliente.")
            return self.form_invalid(form)

    def get_context_data(self, **kwargs) -> dict:
        """
        Adiciona dados de contexto para o template do formulário de criação.

        Inclui um título para o formulário e flags que podem ser usadas
        pelo JavaScript no frontend para controlar a visibilidade de botões
        auxiliares (e.g., busca de CNPJ, busca de CEP).

        Returns:
            dict: O dicionário de contexto com os dados adicionais.
        """
        context = super().get_context_data(**kwargs)
        context['form_title'] = "Cadastrar Novo Cliente"
        context['show_cnpj_button_logic'] = True
        context['show_cep_button_logic'] = True
        return context


class CustomerDetailView(DetailView):
    """
    View para exibir os detalhes de um cliente específico.

    Mostra informações detalhadas do cliente, incluindo seu endereço (se houver).
    Os dados formatados, como CPF/CNPJ e telefone, são obtidos através das
    properties do modelo `Customer`.

    Atributos:
        model (Model): O modelo `Customer` a ser detalhado.
        template_name (str): Caminho para o template de detalhes.
        context_object_name (str): Nome da variável de contexto para o cliente.
    """
    model = Customer
    template_name = 'customers/customer_detail.html'
    context_object_name = 'customer'

    def get_context_data(self, **kwargs) -> dict:
        """
        Adiciona o endereço do cliente ao contexto do template.

        Utiliza a property `address` do modelo `Customer` para obter o
        primeiro endereço associado.

        Returns:
            dict: O dicionário de contexto com o endereço e outros dados do cliente.
        """
        context = super().get_context_data(**kwargs)
        customer = self.get_object()
        context['address'] = customer.address 
        return context


class CustomerUpdateView(UpdateView):
    """
    View para atualizar os dados de um cliente existente.

    Funciona de forma similar à `CustomerCreateView`, utilizando o `CustomerForm`
    para entrada e validação dos dados. A lógica de salvamento, incluindo a
    atualização do cliente e o gerenciamento de seu endereço (criação,
    atualização ou exclusão), é tratada pelos métodos `save()` do `CustomerForm`
    e do modelo `Customer`.

    Atributos:
        model (Model): O modelo `Customer` a ser atualizado.
        form_class (Form): O formulário `CustomerForm` para este modelo.
        template_name (str): Caminho para o template do formulário.
        success_url (str): URL para redirecionar após a atualização bem-sucedida.
    """
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:list')

    def form_valid(self, form) -> HttpResponseRedirect:
        """
        Processa o formulário quando ele é considerado válido para atualização.

        Chama `form.save()` para persistir as alterações no cliente e seu endereço.
        Exibe uma mensagem de sucesso e redireciona para a `success_url`.
        Captura `DjangoFormsValidationError` e outras exceções genéricas para fornecer
        feedback ao usuário e logar o erro.

        Args:
            form (Form): A instância do formulário validado.

        Returns:
            HttpResponseRedirect: Redireciona para a `success_url` em caso de sucesso,
                                 ou renderiza novamente o formulário com erros em caso de falha.
        """
        try:
            self.object = form.save()
            messages.success(self.request, "Cliente atualizado com sucesso!")
            return super().form_valid(form)
        except DjangoFormsValidationError as e:
            logger.error(
                f"Erro de validação ao atualizar cliente: {e.message_dict if hasattr(e, 'message_dict') else e}",
                exc_info=True
            )
            messages.error(self.request, "Erro de validação. Verifique os campos.")
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Erro inesperado ao atualizar cliente: {str(e)}", exc_info=True)
            messages.error(self.request, "Ocorreu um erro inesperado ao atualizar o cliente.")
            return self.form_invalid(form)

    def get_context_data(self, **kwargs) -> dict:
        """
        Adiciona dados de contexto para o template do formulário de edição.

        Inclui um título para o formulário. O `CustomerForm` já é inicializado
        com os dados do cliente existente, incluindo seu endereço, através de
        sua lógica interna (`__init__`). Flags para controle de botões auxiliares
        via JavaScript também podem ser fornecidas.

        Returns:
            dict: O dicionário de contexto com os dados adicionais.
        """
        context = super().get_context_data(**kwargs)
        context['form_title'] = "Editar Cliente"
        context['show_cnpj_button_logic'] = True
        context['show_cep_button_logic'] = True
        return context
