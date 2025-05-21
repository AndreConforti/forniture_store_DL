from django import forms
from .models import Customer
from apps.addresses.models import (
    Address,
)


class CustomerForm(forms.ModelForm):
    """
    Formulário para criar e atualizar instâncias de `Customer`.

    Este formulário gerencia os dados diretos do cliente e também os campos
    relacionados ao seu endereço. A lógica de persistência do endereço
    (criação, atualização ou exclusão do objeto `Address` associado) é
    delegada ao método `save()` do modelo `Customer`.

    Campos de endereço são declarados explicitamente para permitir personalização
    de widgets, validações e pré-preenchimento.
    """

    zip_code = forms.CharField(
        label="CEP",
        max_length=9,
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
        model = Customer
        fields = [
            "customer_type",
            "full_name",
            "preferred_name",
            "tax_id",
            "phone",
            "email",
            "is_vip",
            "profession",
            "interests",
            "notes",
        ]
        widgets = {
            "customer_type": forms.Select(
                attrs={"class": "form-select", "data-action": "customer-type-change"}
            ),
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "preferred_name": forms.TextInput(attrs={"class": "form-control"}),
            "tax_id": forms.TextInput(
                attrs={
                    "class": "form-control tax-id-mask",
                    "placeholder": "CPF ou CNPJ",
                    "data-action": "document-input",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control phone-mask",
                    "placeholder": "(00) 00000-0000",
                }
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "exemplo@email.com"}
            ),
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
        Inicializa o formulário e pré-preenche os campos de endereço se houver uma instância.

        Se uma instância de `Customer` é passada para o formulário (edição) e
        esta instância possui um objeto `Address` associado, os campos de endereço
        do formulário (`zip_code`, `street`, etc.) são populados com os valores
        correspondentes do endereço do cliente. O CEP é populado com o valor já
        limpo (apenas dígitos) do modelo `Address`.

        Também configura o atributo `autocomplete="off"` para os campos de endereço
        e `inputmode="text"` e `pattern` para `tax_id` para melhor UX em mobile.
        """
        super().__init__(*args, **kwargs)

        if (
            self.instance
            and self.instance.pk
            and hasattr(self.instance, "address")
            and self.instance.address
        ):
            address = self.instance.address
            self.fields["zip_code"].initial = address.zip_code
            self.fields["street"].initial = address.street
            self.fields["number"].initial = address.number
            self.fields["complement"].initial = address.complement
            self.fields["neighborhood"].initial = address.neighborhood
            self.fields["city"].initial = address.city
            self.fields["state"].initial = address.state

        if "tax_id" in self.fields:
            # Melhora a experiência em dispositivos móveis para CPF/CNPJ
            self.fields["tax_id"].widget.attrs.update(
                {"pattern": r"[\d.\-/]*", "inputmode": "text"}
            )

        address_field_names = [
            "zip_code",
            "street",
            "number",
            "complement",
            "neighborhood",
            "city",
            "state",
        ]
        for field_name in address_field_names:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs["autocomplete"] = "off"

    def clean_tax_id(self):
        """
        Limpa o campo CPF/CNPJ, removendo caracteres não numéricos.

        Realiza uma validação preliminar do comprimento (entre 11 e 14 dígitos).
        A validação completa do formato (CPF vs CNPJ, algoritmo de validação)
        é delegada ao modelo `Customer`.

        Raises:
            forms.ValidationError: Se o campo for obrigatório e estiver vazio, ou se
                                   o comprimento após a limpeza for inválido.

        Returns:
            str: O CPF/CNPJ limpo (apenas dígitos).
        """
        tax_id_value = self.cleaned_data.get("tax_id")
        if not tax_id_value:
            raise forms.ValidationError("O CPF/CNPJ é obrigatório.")

        cleaned_tax_id = "".join(filter(str.isdigit, tax_id_value))

        if not (11 <= len(cleaned_tax_id) <= 14 and cleaned_tax_id.isdigit()):
            if len(cleaned_tax_id) == 0 and tax_id_value:
                pass
            elif len(cleaned_tax_id) < 11 and len(cleaned_tax_id) > 0:
                raise forms.ValidationError(
                    "Documento muito curto. Verifique o CPF/CNPJ."
                )
            elif len(cleaned_tax_id) > 14:
                raise forms.ValidationError(
                    "Documento muito longo. Verifique o CPF/CNPJ."
                )
        return cleaned_tax_id

    def clean_phone(self):
        """
        Limpa o campo telefone, mantendo apenas os dígitos.

        Returns:
            str: O número de telefone limpo (apenas dígitos) ou o valor original se vazio.
        """
        phone = self.cleaned_data.get("phone")
        if phone:
            return "".join(filter(str.isdigit, phone))
        return phone

    def clean_zip_code(self):
        """
        Limpa o campo CEP, removendo caracteres não numéricos e validando o comprimento.

        Se o CEP for fornecido, ele é limpo para conter apenas dígitos.
        Se, após a limpeza, o CEP não estiver vazio e não tiver 8 dígitos,
        uma `ValidationError` é levantada.

        Returns:
            str: O CEP limpo (8 dígitos) ou None se o campo estiver vazio.
        """
        zip_code = self.cleaned_data.get("zip_code")
        if zip_code:
            cleaned_zip = "".join(filter(str.isdigit, zip_code))
            if cleaned_zip and len(cleaned_zip) != 8:
                raise forms.ValidationError("CEP deve conter 8 números.")
            return cleaned_zip if cleaned_zip else None
        return None

    def clean(self):
        """
        Realiza validações cruzadas entre campos do formulário.

        Verifica se o `customer_type` (Tipo de Cliente) foi selecionado caso
        um `tax_id` (CPF/CNPJ) tenha sido fornecido. Os valores dos campos
        individuais já foram processados por seus respectivos métodos `clean_<fieldname>()`.

        Raises:
            forms.ValidationError: Se `tax_id` for preenchido mas `customer_type` não.

        Returns:
            dict: O dicionário `cleaned_data` validado.
        """
        cleaned_data = super().clean()
        customer_type = cleaned_data.get("customer_type")
        tax_id = cleaned_data.get("tax_id")

        if tax_id and not customer_type:
            self.add_error(
                "customer_type", "Selecione o tipo de cliente para validar o CPF/CNPJ."
            )
        return cleaned_data

    def save(self, commit=True):
        """
        Salva a instância do cliente e gerencia os dados de endereço.

        Primeiro, a instância do `Customer` é criada (ou obtida, se em edição)
        sem persisti-la no banco de dados (`commit=False`).
        Em seguida, os dados de endereço são coletados dos campos do formulário.
        Esses dados são passados como um dicionário `address_data` para o
        método `save()` da instância do `Customer`. O modelo `Customer` é então
        responsável por utilizar esses dados para criar, atualizar ou excluir
        o objeto `Address` associado.

        Se todos os campos de endereço estiverem vazios no formulário, um dicionário
        vazio é passado para `address_data`, sinalizando ao modelo `Customer` que
        o endereço pode ter sido intencionalmente removido pelo usuário.

        Args:
            commit (bool): Se True (padrão), a instância do cliente e as
                           alterações no endereço são salvas no banco de dados.

        Returns:
            Customer: A instância do cliente salva.
        """
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
        else:
            pass

        return instance
