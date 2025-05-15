from django import forms
from .models import Customer
from apps.addresses.models import Address # Para Address.BRAZILIAN_STATES_CHOICES

class CustomerForm(forms.ModelForm):
    """
    Formulário para criar e atualizar instâncias de Customer.

    Inclui campos para os dados do cliente e também para o seu endereço,
    que será gerenciado pelo modelo Customer em seu método save.
    """
    zip_code = forms.CharField(
        label="CEP",
        max_length=9, # Para '00000-000' com máscara
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control cep-mask",
                "placeholder": "00000-000",
                "data-action": "cep-lookup", # Para JavaScript
            }
        ),
    )
    street = forms.CharField(
        label="Logradouro", max_length=100, required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    number = forms.CharField(
        label="Número", max_length=10, required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    complement = forms.CharField(
        label="Complemento", max_length=50, required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    neighborhood = forms.CharField(
        label="Bairro", max_length=50, required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    city = forms.CharField(
        label="Cidade", max_length=50, required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    state = forms.ChoiceField(
        label="UF",
        required=False,
        choices=[("", "----")] + Address.BRAZILIAN_STATES_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Customer
        fields = [
            "customer_type", "full_name", "preferred_name", "tax_id",
            "phone", "email", "is_vip", "profession", "interests", "notes",
        ]
        widgets = {
            "customer_type": forms.Select(attrs={"class": "form-select", "data-action": "customer-type-change"}),
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "preferred_name": forms.TextInput(attrs={"class": "form-control"}),
            "tax_id": forms.TextInput(attrs={"class": "form-control tax-id-mask", "placeholder": "CPF ou CNPJ", "data-action": "document-input"}),
            "phone": forms.TextInput(attrs={"class": "form-control phone-mask", "placeholder": "(00) 00000-0000"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "exemplo@email.com"}),
            "is_vip": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "profession": forms.TextInput(attrs={"class": "form-control"}),
            "interests": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
        labels = {
            "tax_id": "CPF/CNPJ",
            "full_name": "Nome Completo / Razão Social",
            "customer_type": "Tipo de Cliente",
            "is_vip": "Cliente VIP",
            "preferred_name": "Apelido / Nome Fantasia",
        }

    def __init__(self, *args, **kwargs):
        """
        Inicializa o formulário.

        Se uma instância de cliente existente é fornecida e possui um endereço,
        os campos de endereço do formulário são pré-preenchidos.
        Também configura atributos de widget para os campos de endereço.
        """
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.address:
            address = self.instance.address
            self.fields["zip_code"].initial = address.zip_code # CEP já limpo no modelo
            self.fields["street"].initial = address.street
            self.fields["number"].initial = address.number
            self.fields["complement"].initial = address.complement
            self.fields["neighborhood"].initial = address.neighborhood
            self.fields["city"].initial = address.city
            self.fields["state"].initial = address.state

        if "tax_id" in self.fields:
            self.fields["tax_id"].widget.attrs.update({"pattern": r"[\d.\-/]*", "inputmode": "text"})

        address_field_names = ["zip_code", "street", "number", "complement", "neighborhood", "city", "state"]
        for field_name in address_field_names:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs["autocomplete"] = "off"

    def clean_tax_id(self):
        """Limpa e valida preliminarmente o campo CPF/CNPJ."""
        tax_id_value = self.cleaned_data.get("tax_id")
        if not tax_id_value:
            raise forms.ValidationError("O CPF/CNPJ é obrigatório.")
        cleaned_tax_id = "".join(filter(str.isdigit, tax_id_value))

        if not (11 <= len(cleaned_tax_id) <= 14 and cleaned_tax_id.isdigit()):
            if len(cleaned_tax_id) < 11 and len(cleaned_tax_id) > 0 :
                 raise forms.ValidationError("Documento muito curto. Verifique o CPF/CNPJ.")
            elif len(cleaned_tax_id) > 14 :
                 raise forms.ValidationError("Documento muito longo. Verifique o CPF/CNPJ.")
            # A validação completa (algoritmo, tipo vs tamanho) é feita no modelo.
        return cleaned_tax_id

    def clean_phone(self):
        """Limpa o campo telefone, mantendo apenas dígitos."""
        phone = self.cleaned_data.get("phone")
        if phone:
            return "".join(filter(str.isdigit, phone))
        return phone

    def clean_zip_code(self):
        """Limpa o campo CEP, mantendo apenas dígitos e validando o tamanho."""
        zip_code = self.cleaned_data.get("zip_code")
        if zip_code:
            cleaned_zip = "".join(filter(str.isdigit, zip_code))
            if len(cleaned_zip) != 8 and cleaned_zip: # Erro se não vazio e não tiver 8 dígitos
                raise forms.ValidationError("CEP deve conter 8 números.")
            return cleaned_zip
        return None # Retorna None se vazio, para consistência

    def clean(self):
        """
        Validações cruzadas entre campos do formulário.
        Garante que o tipo de cliente seja selecionado se um CPF/CNPJ for fornecido.
        """
        cleaned_data = super().clean()
        customer_type = cleaned_data.get("customer_type")
        tax_id = cleaned_data.get("tax_id") # Já limpo por clean_tax_id()

        if tax_id and not customer_type:
            self.add_error("customer_type", "Selecione o tipo de cliente para validar o CPF/CNPJ.")
        return cleaned_data

    def save(self, commit=True):
        """
        Salva a instância do cliente.

        Coleta os dados de endereço dos campos do formulário e os passa
        para o método save da instância do Customer, que é responsável
        por criar, atualizar ou deletar o objeto Address associado.
        """
        instance = super().save(commit=False) # Cria a instância mas não salva no BD ainda

        # Coleta dados de endereço do formulário para passar ao Customer.save()
        address_data = {
            "zip_code": self.cleaned_data.get("zip_code"), # Já limpo
            "street": self.cleaned_data.get("street", "").strip(),
            "number": self.cleaned_data.get("number", "").strip(),
            "complement": self.cleaned_data.get("complement", "").strip(),
            "neighborhood": self.cleaned_data.get("neighborhood", "").strip(),
            "city": self.cleaned_data.get("city", "").strip(),
            "state": self.cleaned_data.get("state", "").strip().upper(),
        }

        # Se todos os campos de endereço estiverem vazios, passa um dicionário vazio
        # para sinalizar ao Customer.save() que o usuário pode ter limpado o endereço.
        # Se houver algum dado, passa o dicionário populado.
        if not any(v for v in address_data.values() if v is not None and v != ""):
            address_data_to_pass = {}
        else:
            address_data_to_pass = address_data

        if commit:
            # O método save do modelo Customer agora receberá address_data
            # e cuidará da lógica de criar/atualizar/deletar o endereço.
            instance.save(address_data=address_data_to_pass)
        return instance