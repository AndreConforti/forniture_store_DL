# docs/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def tutorial_index_view(request):
    """
    Renderiza a página inicial do tutorial do sistema.

    Esta página serve como um ponto de entrada para as diversas seções
    da documentação, apresentando um resumo do que o usuário pode aprender.
    """
    context = {'current_page': 'index'}
    return render(request, 'docs/index.html', context)

@login_required
def tutorial_authentication_view(request):
    """
    Renderiza a seção do tutorial sobre autenticação e personalização.

    Explica como os usuários podem fazer login, logout e alterar o tema
    visual da interface do sistema.
    """
    context = {'current_page': 'authentication'}
    return render(request, 'docs/authentication.html', context)

@login_required
def tutorial_password_recovery_view(request):
    """
    Renderiza a seção do tutorial sobre recuperação de senha.

    Detalha o processo passo a passo para usuários que esqueceram suas
    senhas, desde a solicitação de redefinição até a criação de uma nova senha.
    """
    context = {'current_page': 'password_recovery'}
    return render(request, 'docs/password_recovery.html', context)

@login_required
def tutorial_customers_overview_view(request):
    """
    Renderiza a seção do tutorial que fornece uma visão geral do módulo de clientes.

    Apresenta as principais funcionalidades relacionadas ao gerenciamento de
    clientes, como cadastro, consulta e edição.
    """
    context = {'current_page': 'customers_overview'}
    return render(request, 'docs/customers_overview.html', context)

@login_required
def tutorial_customers_create_view(request):
    """
    Renderiza a seção do tutorial sobre como cadastrar um novo cliente.

    Guia o usuário através do preenchimento do formulário de cadastro de
    clientes, explicando cada campo e as funcionalidades de busca automática
    de dados (CEP, CNPJ).
    """
    context = {'current_page': 'customers_create'}
    return render(request, 'docs/customers_create.html', context)

@login_required
def tutorial_customers_manage_view(request):
    """
    Renderiza a seção do tutorial sobre como consultar e editar clientes existentes.

    Explica como utilizar a lista de clientes para buscar, visualizar detalhes
    e modificar as informações de clientes já cadastrados no sistema.
    """
    context = {'current_page': 'customers_manage'}
    return render(request, 'docs/customers_manage.html', context)