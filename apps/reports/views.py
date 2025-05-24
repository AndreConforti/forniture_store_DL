# reports/views.py
import os
import pandas as pd
from io import BytesIO, StringIO
from datetime import datetime, date
from django import forms
from django.views import View
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
# --- Importando render ---
from django.shortcuts import render
# --- Fim Importação ---

from .forms import CustomerReportForm
from apps.customers.models import Customer


class CustomerReportView(LoginRequiredMixin, View):
    template_name = 'reports/customer_report_form.html'
    form_class = CustomerReportForm

    def get(self, request, *args, **kwargs):
        # CORRIGIDO: render está importado agora
        form = self.form_class(request.GET)
        return render(request, self.template_name, {'form': form, 'title': 'Gerar Relatório de Clientes'})

    def post(self, request, *args, **kwargs):
        # CORRIGIDO: render está importado agora
        form = self.form_class(request.POST)

        if form.is_valid():
            queryset = form.get_queryset()
            output_format = form.cleaned_data['output_format']

            intermediate_data = self.prepare_data_intermediate(queryset)

            if output_format == 'excel':
                return self.generate_excel(intermediate_data, form)
            elif output_format == 'csv':
                return self.generate_csv(intermediate_data)
            elif output_format == 'json':
                return self.generate_json(intermediate_data)
            else:
                return HttpResponse("Formato de relatório inválido.", status=400)
        else:
            return render(request, self.template_name, {'form': form, 'title': 'Gerar Relatório de Clientes'})


    def prepare_data_intermediate(self, queryset):
        """
        Prepara os dados do QuerySet em um formato intermediário (lista de dicionários)
        com chaves técnicas (inglês/snake_case) para fácil processamento.
        Inclui dados raw e formatados.
        """
        data = []
        for customer in queryset:
            address_info = customer.address
            address_full_formatted = "-"
            if address_info:
                 address_full_formatted = f"{address_info.street}, {address_info.number or 'SN'}"
                 if address_info.complement:
                     address_full_formatted += f" - {address_info.complement}"
                 address_full_formatted += f", {address_info.neighborhood or '-'}, {address_info.city or '-'} - {address_info.state or '-'} / CEP: {address_info.formatted_zip_code or '-'}"


            data.append({
                'id': customer.pk,
                'customer_type': customer.customer_type, # Valor raw ('IND' ou 'CORP')
                'customer_type_display': customer.get_customer_type_display(), # Valor formatado ("Pessoa Física"/"Pessoa Jurídica")
                'full_name': customer.full_name,
                'preferred_name': customer.preferred_name,
                'tax_id': customer.tax_id, # Valor raw (apenas dígitos)
                'tax_id_formatted': customer.formatted_tax_id, # Valor formatado
                'phone': customer.phone, # Valor raw (apenas dígitos)
                'phone_formatted': customer.formatted_phone, # Valor formatado
                'email': customer.email,
                'is_active': customer.is_active, # Booleano True/False
                'is_active_display': 'Sim' if customer.is_active else 'Não', # Valor formatado
                'is_vip': customer.is_vip, # Booleano True/False
                'is_vip_display': 'Sim' if customer.is_vip else 'Não', # Valor formatado
                'profession': customer.profession,
                'interests': customer.interests,
                'notes': customer.notes,
                'registration_date': customer.registration_date.isoformat() if customer.registration_date else None, # Data/Hora raw (ISO)
                'registration_date_formatted': customer.registration_date.strftime('%d/%m/%Y %H:%M') if customer.registration_date else None, # Data/Hora formatada

                'address_id': address_info.pk if address_info else None,
                'address_zip_code': address_info.zip_code if address_info else None,
                'address_zip_code_formatted': address_info.formatted_zip_code if address_info else None,
                'address_street': address_info.street if address_info else None,
                'address_number': address_info.number if address_info else None,
                'address_complement': address_info.complement if address_info else None,
                'address_neighborhood': address_info.neighborhood if address_info else None,
                'address_city': address_info.city if address_info else None,
                'address_state': address_info.state if address_info else None,
                'address_full_formatted': address_full_formatted,
            })
        return data


    def generate_json(self, intermediate_data):
        """Gera o relatório em formato JSON usando dados intermediários (chaves técnicas)."""
        response = JsonResponse(intermediate_data, safe=False, json_dumps_params={'ensure_ascii': False})
        response['Content-Disposition'] = f'attachment; filename="relatorio_clientes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
        return response

    def generate_excel(self, intermediate_data, form):
        """
        Gera o relatório em formato Excel (xlsx) com filtros e data,
        formatando chaves para português.
        """
        # Definir o mapeamento de chaves técnicas para cabeçalhos em português para o Excel
        excel_column_map = {
            'id': 'ID',
            'customer_type_display': 'Tipo', # Usar o valor formatado
            'full_name': 'Nome Completo / Razão Social',
            'preferred_name': 'Apelido / Nome Fantasia',
            'tax_id_formatted': 'CPF/CNPJ', # Usar o valor formatado
            'phone_formatted': 'Telefone', # Usar o valor formatado
            'email': 'E-mail',
            'is_active_display': 'Ativo', # Usar o valor formatado "Sim"/"Não"
            'is_vip_display': 'VIP',     # Usar o valor formatado "Sim"/"Não"
            'profession': 'Profissão',
            'interests': 'Interesses',
            'notes': 'Observações',
            'registration_date_formatted': 'Data Cadastro', # Usar o valor formatado
            'address_zip_code_formatted': 'CEP', # Usar o valor formatado
            'address_street': 'Logradouro',
            'address_number': 'Número',
            'address_complement': 'Complemento',
            'address_neighborhood': 'Bairro',
            'address_city': 'Cidade',
            'address_state': 'UF',
            'address_full_formatted': 'Endereço Completo', # Incluir a string completa também
        }

        # Criar uma nova lista de dicionários para o Excel com chaves e valores formatados
        excel_data = []
        for row in intermediate_data:
            excel_row = {}
            for tech_key, pt_header in excel_column_map.items():
                 # Acessa o valor usando a chave técnica
                 value = row.get(tech_key)
                 # Não precisamos mais converter True/False para Sim/Não aqui,
                 # pois prepare_data_intermediate já fornece is_active_display e is_vip_display
                 excel_row[pt_header] = value if value is not None else '-' # Usa '-' para None/vazio

            excel_data.append(excel_row)

        df = pd.DataFrame(excel_data) # Cria o DataFrame a partir dos dados formatados para Excel

        buffer = BytesIO()

        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            sheet_name = 'Clientes'

            excel_content = []

            excel_content.append(['Relatório de Clientes'])
            excel_content.append([f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}'])
            excel_content.append([])

            applied_filters_info = []
            for field_name, field in form.fields.items():
                if field_name != 'output_format':
                     value = form.cleaned_data.get(field_name)
                     display_value = None

                     if isinstance(field, forms.ChoiceField): # Para RadioSelect (ChoiceField)
                         if value is not None:
                              choices_dict = dict(field.choices)
                              display_value = choices_dict.get(value, value) # Obtém o label ("Todos", "Sim", "Não", etc.)

                     elif isinstance(field, (forms.CharField, forms.EmailField)):
                         if value: # Check if string is not empty
                              display_value = str(value)

                     if display_value is not None:
                          applied_filters_info.append(f'{field.label}: {display_value}')

            if applied_filters_info:
                excel_content.append(['Filtros Aplicados:'])
                for filter_info in applied_filters_info:
                     excel_content.append([filter_info])
            else:
                 excel_content.append(['Nenhum filtro aplicado explicitamente.'])


            excel_content.append([])

            # Adiciona o cabeçalho das colunas dos dados (nomes das colunas do DataFrame excel_data)
            excel_content.append(df.columns.tolist())

            # Adiciona as linhas de dados do DataFrame
            excel_content.extend(df.values.tolist())

            # Criar um único DataFrame a partir do conteúdo completo
            combined_df = pd.DataFrame(excel_content)

            # Escrever o DataFrame combinado para o Excel
            combined_df.to_excel(writer, index=False, header=False, sheet_name=sheet_name, startrow=0)


        excel_value = buffer.getvalue()
        buffer.close()

        response = HttpResponse(excel_value, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="relatorio_clientes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        return response

    def generate_csv(self, intermediate_data):
        """
        Gera o relatório em formato CSV usando dados intermediários,
        formatando chaves para português.
        """
         # O mapeamento para CSV pode ser o mesmo do Excel
        csv_column_map = {
            'id': 'ID',
            'customer_type_display': 'Tipo',
            'full_name': 'Nome Completo / Razão Social',
            'preferred_name': 'Apelido / Nome Fantasia',
            'tax_id_formatted': 'CPF/CNPJ',
            'phone_formatted': 'Telefone',
            'email': 'E-mail',
            'is_active_display': 'Ativo',
            'is_vip_display': 'VIP',
            'profession': 'Profissão',
            'interests': 'Interesses',
            'notes': 'Observações',
            'registration_date_formatted': 'Data Cadastro',
            'address_zip_code_formatted': 'CEP',
            'address_street': 'Logradouro',
            'address_number': 'Número',
            'address_complement': 'Complemento',
            'address_neighborhood': 'Bairro',
            'address_city': 'Cidade',
            'address_state': 'UF',
            'address_full_formatted': 'Endereço Completo',
        }

        # Criar uma nova lista de dicionários para o CSV com chaves e valores formatados
        csv_data = []
        for row in intermediate_data:
            csv_row = {}
            for tech_key, pt_header in csv_column_map.items():
                 value = row.get(tech_key)
                 # Não precisamos mais converter True/False para Sim/Não aqui
                 csv_row[pt_header] = value if value is not None else '-' # Usa '-' para None/vazio

            csv_data.append(csv_row)


        df = pd.DataFrame(csv_data) # Cria o DataFrame a partir dos dados formatados para CSV

        buffer = StringIO()
        df.to_csv(buffer, index=False, encoding='utf-8-sig', sep=';', decimal='.')

        csv_value = buffer.getvalue()
        buffer.close()

        response = HttpResponse(csv_value, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="relatorio_clientes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        return response