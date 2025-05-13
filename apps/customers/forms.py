from django import forms
from .models import Customer
from django.core.validators import RegexValidator
from validate_docbr import CPF, CNPJ


class CustomerForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # Chamar super() primeiro

        # Ajusta o widget do tax_id
        if 'tax_id' in self.fields:
            self.fields['tax_id'].widget.attrs.update({
                'pattern': r'\d*',
                'inputmode': 'numeric'
            })

        # Adicionar autocomplete="off" aos campos de endereço
        address_fields = ['zip_code', 'street', 'number', 'complement', 'neighborhood', 'city', 'state']
        for field_name in address_fields:
            if field_name in self.fields: 
                self.fields[field_name].widget.attrs['autocomplete'] = 'off'


    # Campos de endereço
    zip_code = forms.CharField(
        max_length=8,
        required=False,
        label='CEP',
        validators=[RegexValidator(r'^\d{8}$', 'CEP deve ter 8 dígitos')],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite o CEP',
            'data-action': 'cep-lookup'
        })
    )
    
    street = forms.CharField(
        max_length=100,
        required=False,
        label='Logradouro',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    number = forms.CharField(
        max_length=10,
        required=False,
        label='Número',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    complement = forms.CharField(
        max_length=50,
        required=False,
        label='Complemento',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    neighborhood = forms.CharField(
        max_length=50,
        required=False,
        label='Bairro',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    city = forms.CharField(
        max_length=50,
        required=False,
        label='Cidade',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    state = forms.CharField(
        max_length=2,
        required=False,
        label='UF',
        widget=forms.TextInput(attrs={
            'class': 'form-control text-uppercase',
            'maxlength': '2'
        })
    )

    class Meta:
        model = Customer
        fields = [
            'customer_type', 'full_name', 'preferred_name',
            'tax_id', 'phone', 'email', 'is_vip',
            'profession', 'interests', 'notes'
        ]
        widgets = {
            'customer_type': forms.Select(attrs={
                'class': 'form-select',
                'data-action': 'customer-type-change'
            }),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'preferred_name': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-control',
                'data-action': 'document-input',
                'placeholder': 'Somente números'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 00000-0000'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'exemplo@email.com'
            }),
            'is_vip': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'profession': forms.TextInput(attrs={'class': 'form-control'}),
            'interests': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
        labels = {
            'tax_id': 'CPF/CNPJ',
            'full_name': 'Nome Completo / Razão Social',
            'customer_type': 'Tipo de Cliente',
            'is_vip': 'Cliente VIP'
        }


    def clean_tax_id(self):
        customer_type = self.cleaned_data.get('customer_type')
        tax_id = self.cleaned_data.get('tax_id')

        if not tax_id:
            raise forms.ValidationError("Documento obrigatório!")

        # Removendo caracteres especiais antes da validação
        tax_id = tax_id.replace('.', '').replace('-', '').replace('/', '').strip()

        # Verificando tamanho correto antes da validação
        if customer_type == "IND" and len(tax_id) != 11:
            raise forms.ValidationError("CPF inválido! Deve conter exatamente 11 números.")
        elif customer_type == "CORP" and len(tax_id) != 14:
            raise forms.ValidationError("CNPJ inválido! Deve conter exatamente 14 números.")

        # Validação usando validate-docbr
        if customer_type == "IND" and not CPF().validate(tax_id):
            raise forms.ValidationError("CPF inválido!")
        elif customer_type == "CORP" and not CNPJ().validate(tax_id):
            raise forms.ValidationError("CNPJ inválido!")

        return tax_id  # Retorna CPF/CNPJ limpo e validado