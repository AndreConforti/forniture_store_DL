# reports/forms.py
from django import forms
from django.db.models import Q
from apps.customers.models import Customer
from django.core.validators import RegexValidator
import re

class CustomerReportForm(forms.Form):
    """
    Formulário para filtrar clientes para o relatório e selecionar formato.
    """
    OUTPUT_FORMAT_CHOICES = [
        ('excel', 'Excel (xlsx)'),
        ('csv', 'CSV'),
        ('json', 'JSON'), # <-- CORRIGIDO: Opção JSON adicionada de volta aqui
    ]

    # Campos de Filtro (mantidos os mesmos)
    full_name = forms.CharField(
        label="Nome Completo / Razão Social",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    preferred_name = forms.CharField(
        label="Apelido / Nome Fantasia",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    customer_type = forms.ChoiceField(
        label="Tipo de Cliente",
        choices=[('', 'Todos')] + list(Customer.CUSTOMER_TYPE_CHOICES),
        required=False,
        initial='',
        widget=forms.RadioSelect(attrs={"class": "form-check form-check-inline me-3"})
    )

    tax_id = forms.CharField(
        label="CPF/CNPJ",
        max_length=18,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    phone = forms.CharField(
        label="Telefone",
        max_length=11,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    email = forms.EmailField(
        label="E-mail",
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control"})
    )

    is_active = forms.ChoiceField(
        label="Status",
        choices=[('', 'Todos'), ('True', 'Ativo'), ('False', 'Inativo')],
        required=False,
        initial='True',
        widget=forms.RadioSelect(attrs={"class": "form-check form-check-inline me-3"})
    )

    is_vip = forms.ChoiceField(
        label="Cliente VIP",
        choices=[('', 'Todos'), ('True', 'Sim'), ('False', 'Não')],
        required=False,
        initial='False',
        widget=forms.RadioSelect(attrs={"class": "form-check form-check-inline me-3"})
    )

    # Campo para selecionar o formato de saída
    output_format = forms.ChoiceField(
        label="Formato de Saída",
        choices=OUTPUT_FORMAT_CHOICES, # Agora inclui JSON
        initial='excel',
        widget=forms.Select(attrs={"class": "form-select"})
    )

    # Métodos clean e get_queryset (mantidos os mesmos)
    def clean_tax_id(self):
        tax_id = self.cleaned_data.get('tax_id')
        if tax_id:
            return re.sub(r'\D', '', tax_id)
        return tax_id

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            return "".join(filter(str.isdigit, phone))
        return phone

    def get_queryset(self):
        if not self.is_valid():
             return Customer.objects.none()

        data = self.cleaned_data
        queryset = Customer.objects.all()

        if data.get('full_name'):
            queryset = queryset.filter(full_name__icontains=data['full_name'])
        if data.get('preferred_name'):
            queryset = queryset.filter(preferred_name__icontains=data['preferred_name'])

        customer_type = data.get('customer_type')
        if customer_type != '' and customer_type is not None:
            queryset = queryset.filter(customer_type=customer_type)

        if data.get('tax_id'):
            queryset = queryset.filter(tax_id__icontains=data['tax_id'])
        if data.get('phone'):
            queryset = queryset.filter(phone__icontains=data['phone'])
        if data.get('email'):
            queryset = queryset.filter(email__icontains=data['email'])

        is_active_value = data.get('is_active')
        if is_active_value != '' and is_active_value is not None:
             queryset = queryset.filter(is_active=(is_active_value == 'True'))

        is_vip_value = data.get('is_vip')
        if is_vip_value != '' and is_vip_value is not None:
             queryset = queryset.filter(is_vip=(is_vip_value == 'True'))

        queryset = queryset.order_by('full_name')

        return queryset