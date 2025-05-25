# Decora by Lu - Sistema de Gestão Integrada

## Visão Geral do Projeto

Este projeto é um sistema de gestão integrado desenvolvido para atender às necessidades de uma loja física de móveis e decoração, "Decora by Lu". O objetivo principal é centralizar e otimizar as operações diárias, desde o cadastro e relacionamento com clientes e fornecedores até o controle de estoque, gerenciamento de pedidos e acompanhamento financeiro.

O sistema está sendo construído modularmente, permitindo a implementação e o deploy faseado das funcionalidades.

## Módulos Planejados

O sistema completo abrangerá os seguintes módulos:

1.  **Clientes:** Gerenciamento completo do cadastro de clientes (Pessoa Física e Jurídica), incluindo dados de contato, informações fiscais e endereços.
2.  **Fornecedores:** Cadastro e gestão de fornecedores.
3.  **Produtos:** Cadastro detalhado de produtos, com categorias, subcategorias e informações relevantes.
4.  **Estoque:** Controle de entrada e saída de produtos, inventário e gestão de níveis de estoque.
5.  **Pedidos:** Registro e acompanhamento do ciclo de vida dos pedidos de venda.
6.  **Contas a Pagar:** Gestão de obrigações financeiras a fornecedores e outras despesas.
7.  **Contas a Receber:** Controle de pagamentos de clientes e faturamento.
8.  **Relatórios:** Geração de relatórios gerenciais e operacionais sobre todos os módulos.

## Status Atual do Projeto

Atualmente, o módulo de **Clientes** está implementado e pronto para ser utilizado e testado. Este README detalha as funcionalidades disponíveis neste módulo. Os demais módulos estão em fase de planejamento ou desenvolvimento inicial.

## Módulo Implementado: Clientes

O módulo de Clientes permite o gerenciamento completo do cadastro de clientes da loja.

### Funcionalidades Principais do Módulo de Clientes:

*   **Cadastro de Clientes (Pessoa Física e Jurídica):** Registro de novos clientes com informações como nome/razão social, apelido/nome fantasia, CPF/CNPJ, telefone, e-mail, profissão, interesses, status VIP e observações.
*   **Gerenciamento de Endereços:** Cada cliente pode ter um endereço associado. O sistema integra-se com APIs externas para buscar dados de endereço automaticamente a partir do CEP.
*   **Busca Inteligente de Dados (CNPJ/CEP):**
    *   Ao cadastrar ou editar um cliente Pessoa Jurídica (CNPJ), o sistema pode buscar automaticamente a Razão Social, Nome Fantasia e dados básicos do endereço através de APIs públicas.
    *   Para qualquer tipo de cliente, os campos de endereço podem ser preenchidos automaticamente informando apenas o CEP, consultando APIs de endereços.
*   **Validação Automática:** Validação do formato e dígitos verificadores de CPF e CNPJ de acordo com o tipo de cliente selecionado. Limpeza automática de campos como telefone e CEP (removendo caracteres não numéricos).
*   **Visualização Detalhada:** Página dedicada para exibir todas as informações de um cliente, incluindo seus dados básicos, endereço formatado e informações adicionais.
*   **Listagem de Clientes:** Visualização paginada dos clientes cadastrados e ativos.
*   **Busca e Filtro:** Funcionalidades de busca por nome, CPF/CNPJ ou e-mail, e filtro por tipo de cliente (Pessoa Física / Jurídica) na página de listagem.
*   **Usabilidade:** Formulário de cadastro/edição organizado em abas para facilitar a navegação entre as diferentes seções de informação do cliente.

### Tecnologias Utilizadas no Módulo de Clientes:

*   **Backend:** Python, Django, Django REST Framework (para endpoints de API de busca), `requests` (para consumo de APIs externas), `validate_docbr` (para validação de documentos).
*   **Database:** Utiliza o ORM do Django.
*   **Frontend:** HTML, CSS, Bootstrap 5 (para o layout e componentes), JavaScript (com jQuery para a lógica de busca de dados via API), Máscaras de entrada (para CEP e CPF/CNPJ no frontend).
*   **Estruturas Django Adicionais:** `GenericRelation` e `ContentType` para associar o endereço de forma flexível, `cached_property` para otimizar o acesso a dados formatados, Views baseadas em Classe (`ListView`, `DetailView`, `CreateView`, `UpdateView`).

## Configuração e Execução (WIP)

1.  Clone o repositório.
2.  Crie um ambiente virtual (`python -m venv venv`).
3.  Ative o ambiente virtual (`source venv/bin/activate` no Linux/macOS, `venv\Scripts\activate` no Windows).
4.  Instale as dependências (`pip install -r requirements.txt`). *(Você precisará criar este arquivo com base nas libs usadas)*.
5.  Configure o banco de dados em `settings.py`.
6.  Execute as migrações (`python manage.py migrate`).
7.  Crie um superusuário para acessar a área administrativa (`python manage.py createsuperuser`).
8.  Execute o servidor de desenvolvimento (`python manage.py runserver`).
9.  Acesse a aplicação no navegador (geralmente em `http://127.0.0.1:8000/`).

## Próximos Passos

*   Finalizar a configuração do ambiente para deploy da versão atual.
*   Continuar a implementação dos módulos restantes (Fornecedores, Produtos, Estoque, Pedidos, Financeiro).
*   Desenvolver relatórios mais complexos.
*   Melhorar a interface do usuário e a experiência do usuário.
*   Desenvolver uma documentação técnica e de usuário mais completa.