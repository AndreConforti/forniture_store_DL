from django import forms
from .models import (
    Customer,
)  # Address não precisa ser importado aqui se não for usado diretamente
from apps.addresses.models import (
    Address,
)  # Importar para Address.BRAZILIAN_STATES_CHOICES
from django.core.validators import RegexValidator


class CustomerForm(forms.ModelForm):
    # Campos de endereço definidos no formulário
    zip_code = forms.CharField(
        label="CEP",
        max_length=9,
        required=False,  # max_length 9 para '00000-000'
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
                attrs={  # max_length do widget é herdado do modelo (18)
                    "class": "form-control tax-id-mask",
                    "placeholder": "Digite o CPF ou CNPJ com ou sem máscara",
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
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.address:
            address = self.instance.address
            # Usar zip_code limpo para o initial, a máscara JS deve formatar
            self.fields["zip_code"].initial = address.zip_code
            self.fields["street"].initial = address.street
            self.fields["number"].initial = address.number
            self.fields["complement"].initial = address.complement
            self.fields["neighborhood"].initial = address.neighborhood
            self.fields["city"].initial = address.city
            self.fields["state"].initial = address.state

        if "tax_id" in self.fields:  # Ajustes no widget tax_id
            self.fields["tax_id"].widget.attrs.update(
                {"pattern": r"[\d.\-/]*", "inputmode": "text"}
            )  # Permite máscara

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
        tax_id_value_from_input = self.cleaned_data.get("tax_id")

        if not tax_id_value_from_input:
            raise forms.ValidationError("O CPF/CNPJ é obrigatório.")

        cleaned_tax_id = "".join(filter(str.isdigit, tax_id_value_from_input))

        # A validação de comprimento e algoritmo será feita no `clean()` do modelo.
        # No entanto, podemos adicionar uma verificação de comprimento mínimo/máximo aqui
        # para o valor limpo, se quisermos feedback mais rápido.
        if not (11 <= len(cleaned_tax_id) <= 14 and cleaned_tax_id.isdigit()):
            if len(cleaned_tax_id) < 11:
                raise forms.ValidationError(
                    "Documento muito curto. Verifique o CPF/CNPJ."
                )
            # O modelo vai pegar comprimentos exatos (11 para CPF, 14 para CNPJ).

        # O `clean()` do modelo Customer fará a validação completa (CPF()/CNPJ().validate())
        # e a validação de comprimento exato baseado no customer_type.
        return cleaned_tax_id  # Retorna o valor limpo para o ModelForm

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if phone:
            return "".join(filter(str.isdigit, phone))
        return phone

    def clean_zip_code(self):
        zip_code = self.cleaned_data.get("zip_code")
        if zip_code:
            cleaned_zip = "".join(filter(str.isdigit, zip_code))
            if (
                len(cleaned_zip) != 8 and cleaned_zip
            ):  # Apenas erro se não for vazio e não tiver 8 dígitos
                raise forms.ValidationError("CEP deve conter 8 números.")
            return cleaned_zip
        return zip_code  # Retorna None ou '' se não preenchido

    def clean(self):
        cleaned_data = super().clean()
        # Validações cruzadas entre campos do formulário podem ir aqui,
        # por exemplo, se customer_type e tax_id precisam ser validados juntos
        # no nível do formulário ANTES de ir para o modelo.

        # Exemplo: garantir que customer_type esteja presente se tax_id foi fornecido
        customer_type = cleaned_data.get("customer_type")
        tax_id = cleaned_data.get("tax_id")  # já limpo pelo clean_tax_id()

        if tax_id and not customer_type:
            # Isso geralmente é tratado pela obrigatoriedade do campo customer_type
            self.add_error(
                "customer_type", "Selecione o tipo de cliente para validar o CPF/CNPJ."
            )

        # A validação principal de tax_id (comprimento exato vs tipo, e algoritmo)
        # ocorrerá no `Customer.clean()` que é chamado por `instance.full_clean()`.
        return cleaned_data

    def save(self, commit=True):
        # A instância do modelo é criada/atualizada com os dados de cleaned_data.
        # O `tax_id` em `self.cleaned_data` já foi limpo por `self.clean_tax_id()`.
        # Então, `instance.tax_id` terá o valor limpo antes de `instance.full_clean()` ser chamado.
        instance = super().save(commit=False)

        if commit:
            # Prepara dados de endereço para o método save do modelo Customer.
            # Customer.save() chamará instance.full_clean() internamente.
            address_data = {
                "zip_code": self.cleaned_data.get(
                    "zip_code"
                ),  # Já limpo por clean_zip_code
                "street": self.cleaned_data.get("street"),
                "number": self.cleaned_data.get("number"),
                "complement": self.cleaned_data.get("complement"),
                "neighborhood": self.cleaned_data.get("neighborhood"),
                "city": self.cleaned_data.get("city"),
                "state": self.cleaned_data.get("state"),
            }

            # Passa address_data para o save do Customer.
            # Se todos os campos de endereço estiverem vazios/None, `address_data`
            # conterá chaves com valores None ou ''.
            # O `Customer.save` decide o que fazer com `address_data` (criar, atualizar ou deletar endereço).
            # Se `any(address_data.values())` for falso, todos os valores são None ou '',
            # indicando que nenhum dado de endereço foi fornecido ou foi limpo.
            if any(v for v in address_data.values() if v is not None and v != ""):
                instance.save(address_data=address_data)
            else:
                # Passa um dict vazio para indicar que os campos do form vieram vazios,
                # ou não passa address_data se preferir que o Customer.save trate None.
                # Com a lógica atual do Customer.save, passar um dict vazio é um sinal claro.
                instance.save(address_data={})

        return instance
