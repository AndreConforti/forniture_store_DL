from django import forms
from .models import Supplier
from apps.addresses.models import Address # Importar para BRAZILIAN_STATES_CHOICES

class SupplierForm(forms.ModelForm):
    # Campos de endereço declarados explicitamente para consistência com CustomerForm
    zip_code = forms.CharField(
        label="CEP",
        max_length=9, # Para acomodar o hífen da máscara
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control cep-mask",
                "placeholder": "00000-000",
                "data-action": "cep-lookup",
            }
        ),
    )
    street = forms.CharField(
        label="Logradouro",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    number = forms.CharField(
        label="Número",
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    complement = forms.CharField(
        label="Complemento",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    neighborhood = forms.CharField(
        label="Bairro",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    city = forms.CharField(
        label="Cidade",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    state = forms.ChoiceField(
        label="UF",
        required=False,
        choices=[("", "----")] + Address.BRAZILIAN_STATES_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Supplier
        fields = [
            'supplier_type', 'full_name', 'preferred_name', 'tax_id',
            'state_registration', 'municipal_registration',
            'phone', 'email', 'contact_person',
            'bank_name', 'bank_agency', 'bank_account', 'pix_key',
            # 'is_active',  # REMOVIDO para espelhar CustomerForm
            'notes'
        ]
        widgets = {
            'supplier_type': forms.Select(attrs={
                'class': 'form-select',
                'data-action': 'supplier-type-change'
            }),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'preferred_name': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-control tax-id-mask',
                'placeholder': 'CPF ou CNPJ',
                'data-action': 'document-input'
            }),
            'state_registration': forms.TextInput(attrs={'class': 'form-control'}),
            'municipal_registration': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={
                'class': 'form-control phone-mask',
                'placeholder': '(00) 00000-0000',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'exemplo@email.com'
            }),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_agency': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account': forms.TextInput(attrs={'class': 'form-control'}),
            'pix_key': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'tax_id': 'CPF/CNPJ',
            'full_name': 'Nome Completo / Razão Social',
            'preferred_name': 'Apelido / Nome Fantasia',
            'supplier_type': 'Tipo de Fornecedor',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if (self.instance and self.instance.pk and hasattr(self.instance, "address") and self.instance.address):
            address = self.instance.address
            self.fields["zip_code"].initial = address.zip_code
            self.fields["street"].initial = address.street
            self.fields["number"].initial = address.number
            self.fields["complement"].initial = address.complement
            self.fields["neighborhood"].initial = address.neighborhood
            self.fields["city"].initial = address.city
            self.fields["state"].initial = address.state
        
        if "tax_id" in self.fields:
            self.fields["tax_id"].widget.attrs.update(
                {"pattern": r"[\d.\-/]*", "inputmode": "text"}
            )

        address_field_names = [
            "zip_code", "street", "number", "complement",
            "neighborhood", "city", "state",
        ]
        for field_name in address_field_names:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs["autocomplete"] = "off"

        supplier_type_val = self.initial.get('supplier_type', self.instance.supplier_type if self.instance.pk else None)
        
        # Garante que os campos de widget sejam os corretos no __init__
        # Se o tipo for IND, esconde os campos. Se for CORP, garante que são TextInput.
        default_text_input = forms.TextInput(attrs={'class': 'form-control'}) # Widget padrão

        if supplier_type_val == 'IND':
            if 'state_registration' in self.fields:
                self.fields['state_registration'].widget = forms.HiddenInput()
            if 'municipal_registration' in self.fields:
                self.fields['municipal_registration'].widget = forms.HiddenInput()
        else: # CORP ou Nenhum (para criação, onde o JS vai atuar)
            if 'state_registration' in self.fields:
                 current_widget_sr = self.fields['state_registration'].widget
                 # Se o widget já for o correto (TextInput), não faz nada.
                 # Se por algum motivo for HiddenInput (ex: form recarregado com erro após mudar tipo), reverte.
                 if isinstance(current_widget_sr, forms.HiddenInput):
                    self.fields['state_registration'].widget = self.Meta.widgets.get('state_registration', default_text_input)

            if 'municipal_registration' in self.fields:
                current_widget_mr = self.fields['municipal_registration'].widget
                if isinstance(current_widget_mr, forms.HiddenInput):
                    self.fields['municipal_registration'].widget = self.Meta.widgets.get('municipal_registration', default_text_input)

    def clean_tax_id(self):
        tax_id_value = self.cleaned_data.get("tax_id")
        if not tax_id_value:
            # Deixa a validação de obrigatoriedade para o modelo,
            # pois 'tax_id' é obrigatório no modelo Supplier.
            return tax_id_value
        cleaned_tax_id = "".join(filter(str.isdigit, tax_id_value))
        return cleaned_tax_id

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if phone:
            return "".join(filter(str.isdigit, phone))
        return phone

    def clean_zip_code(self):
        zip_code = self.cleaned_data.get("zip_code")
        if zip_code:
            cleaned_zip = "".join(filter(str.isdigit, zip_code))
            if cleaned_zip and len(cleaned_zip) != 8:
                raise forms.ValidationError("CEP deve conter 8 números.")
            return cleaned_zip if cleaned_zip else None # Permite CEP vazio
        return None

    def clean(self):
        cleaned_data = super().clean()
        supplier_type = cleaned_data.get("supplier_type")
        tax_id = cleaned_data.get("tax_id") # Já deve estar limpo

        if tax_id and not supplier_type:
            self.add_error(
                "supplier_type", "Selecione o tipo de fornecedor para validar o CNPJ/CPF."
            )
        
        if supplier_type == "CORP" and not cleaned_data.get('preferred_name'):
            self.add_error('preferred_name', "Nome Fantasia é obrigatório para Pessoa Jurídica.")
        
        # Limpar erros de campos HiddenInput se eles foram validados como required
        # Isso é mais relevante se os campos HiddenInput tivessem required=True no modelo, o que não é o caso.
        if supplier_type == "IND":
            if 'state_registration' in self.errors:
                del self.errors['state_registration']
            if 'municipal_registration' in self.errors:
                del self.errors['municipal_registration']
                
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        address_data = {
            "zip_code": self.cleaned_data.get("zip_code"),
            "street": self.cleaned_data.get("street", "").strip(),
            "number": self.cleaned_data.get("number", "").strip(),
            "complement": self.cleaned_data.get("complement", "").strip(),
            "neighborhood": self.cleaned_data.get("neighborhood", "").strip(),
            "city": self.cleaned_data.get("city", "").strip(),
            "state": self.cleaned_data.get("state", "").strip().upper(),
        }
        is_any_address_data_present = any(
            value for value in address_data.values() if value not in [None, ""]
        )
        address_data_to_pass = address_data if is_any_address_data_present else {}

        if commit:
            instance.save(address_data=address_data_to_pass)
            # self._save_m2m() # Descomente se tiver campos ManyToMany
        else:
            # Usado principalmente pelo admin ou quando se quer manipular a instância antes do save final
            self.saved_address_data = address_data_to_pass 
        return instance