from django import forms
from django.core.validators import RegexValidator
from validate_docbr import CPF, CNPJ
from .models import Supplier

class SupplierForm(forms.ModelForm):
    # Campos de endereço (opcionais)
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
        model = Supplier
        fields = [
            'supplier_type', 'full_name', 'preferred_name', 'tax_id',
            'state_registration', 'municipal_registration',
            'phone', 'email', 'contact_person',
            'bank_name', 'bank_agency', 'bank_account', 'pix_key',
            'is_active', 'notes'
        ]
        widgets = {
            'supplier_type': forms.Select(attrs={
                'class': 'form-select',
                'data-action': 'supplier-type-change'  # Para JavaScript
            }),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'preferred_name': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-control',
                'data-action': 'document-input',
                'placeholder': 'Somente números',
                'pattern': r'\d*',
                'inputmode': 'numeric'
            }),
            'state_registration': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Opcional para PF'
            }),
            'municipal_registration': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Opcional para PF'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 00000-0000'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'exemplo@fornecedor.com'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do responsável'
            }),
            'bank_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Banco do Brasil'
            }),
            'bank_agency': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número da agência'
            }),
            'bank_account': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número da conta'
            }),
            'pix_key': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Chave PIX (CPF/CNPJ, e-mail, telefone)'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observações importantes'
            }),
        }
        labels = {
            'tax_id': 'CPF/CNPJ',
            'pix_key': 'Chave PIX'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ajusta campos obrigatórios dinamicamente
        self.fields['full_name'].required = True
        self.fields['tax_id'].required = True
        
        # Oculta campos fiscais se for PF
        if self.instance and self.instance.supplier_type == 'IND':
            self.fields['state_registration'].widget = forms.HiddenInput()
            self.fields['municipal_registration'].widget = forms.HiddenInput()

    def clean_tax_id(self):
        supplier_type = self.cleaned_data.get('supplier_type')
        tax_id = self.cleaned_data.get('tax_id')

        if not tax_id:
            raise forms.ValidationError("Documento obrigatório!")

        tax_id = tax_id.replace('.', '').replace('-', '').replace('/', '').strip()

        if supplier_type == "IND":
            if len(tax_id) != 11:
                raise forms.ValidationError("CPF inválido! Deve conter 11 números.")
            if not CPF().validate(tax_id):
                raise forms.ValidationError("CPF inválido!")
        else:  # CORP
            if len(tax_id) != 14:
                raise forms.ValidationError("CNPJ inválido! Deve conter 14 números.")
            if not CNPJ().validate(tax_id):
                raise forms.ValidationError("CNPJ inválido!")

        return tax_id

    def clean(self):
        cleaned_data = super().clean()
        supplier_type = cleaned_data.get('supplier_type')

        # Remove obrigatoriedade de campos fiscais para PF
        if supplier_type == "IND":
            for field in ['state_registration', 'municipal_registration']:
                if field in self.errors:
                    del self.errors[field]

        # Validação condicional para nome fantasia (obrigatório para PJ)
        if supplier_type == "CORP" and not cleaned_data.get('preferred_name'):
            self.add_error('preferred_name', "Nome fantasia é obrigatório para PJ.")

    def save(self, commit=True):
        supplier = super().save(commit=False)
        
        # Atualiza endereço se dados forem fornecidos
        address_data = {
            'zip_code': self.cleaned_data.get('zip_code'),
            'street': self.cleaned_data.get('street'),
            'number': self.cleaned_data.get('number'),
            'complement': self.cleaned_data.get('complement'),
            'neighborhood': self.cleaned_data.get('neighborhood'),
            'city': self.cleaned_data.get('city'),
            'state': self.cleaned_data.get('state')
        }
        
        if commit:
            supplier.save()
            supplier._update_or_create_address(address_data)
        
        return supplier