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

    is_active = forms.BooleanField(
        required=False,  # Não é obrigatório
        initial=True,   # Marcado por padrão
        label='Fornecedor ativo',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_is_active'
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
                'data-action': 'supplier-type-change'
            }),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'preferred_name': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-control',
                'data-action': 'document-input',
                'placeholder': 'Somente números'
            }),
            'state_registration': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Inscrição Estadual'
            }),
            'municipal_registration': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Inscrição Municipal'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 00000-0000'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'exemplo@email.com'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do contato principal'
            }),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_agency': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account': forms.TextInput(attrs={'class': 'form-control'}),
            'pix_key': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
        labels = {
            'tax_id': 'CPF/CNPJ',
            'is_active': 'Fornecedor ativo'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ajusta campos obrigatórios
        self.fields['full_name'].required = True
        self.fields['tax_id'].required = True
        
        # Se for pessoa física, esconde campos de inscrição
        if self.instance and self.instance.supplier_type == 'IND':
            self.fields['state_registration'].widget = forms.HiddenInput()
            self.fields['municipal_registration'].widget = forms.HiddenInput()

    def clean_tax_id(self):
        supplier_type = self.cleaned_data.get('supplier_type')
        tax_id = self.cleaned_data.get('tax_id')

        if not tax_id:
            raise forms.ValidationError("Documento obrigatório!")

        # Remove caracteres especiais
        tax_id = tax_id.replace('.', '').replace('-', '').replace('/', '').strip()

        # Validação de CPF/CNPJ
        if supplier_type == "IND":
            if len(tax_id) != 11:
                raise forms.ValidationError("CPF inválido! Deve conter 11 números.")
            if not CPF().validate(tax_id):
                raise forms.ValidationError("CPF inválido!")
        elif supplier_type == "CORP":
            if len(tax_id) != 14:
                raise forms.ValidationError("CNPJ inválido! Deve conter 14 números.")
            if not CNPJ().validate(tax_id):
                raise forms.ValidationError("CNPJ inválido!")

        return tax_id

    def clean(self):
        cleaned_data = super().clean()
        supplier_type = cleaned_data.get('supplier_type')

        # Validações específicas para PJ
        if supplier_type == "CORP":
            if not cleaned_data.get('preferred_name'):
                self.add_error('preferred_name', "Nome fantasia é obrigatório para PJ.")
            
            # Remove erros de campos não obrigatórios para PF
            if 'state_registration' in self.errors:
                del self.errors['state_registration']
            if 'municipal_registration' in self.errors:
                del self.errors['municipal_registration']