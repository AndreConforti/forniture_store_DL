from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils.functional import cached_property
from apps.addresses.models import Address
from core.services import fetch_company_data
from validate_docbr import CPF, CNPJ
import logging

logger = logging.getLogger(__name__)


class Customer(models.Model):
    """
    Representa um cliente, que pode ser uma Pessoa Física ou Jurídica.

    Este modelo armazena informações cadastrais básicas, de contato e fiscais.
    Utiliza uma `GenericRelation` com o modelo `Address` para permitir que um
    cliente possa ter um endereço associado. A lógica de validação de CPF/CNPJ
    é implementada no método `clean()`, e a busca de dados de empresas
    (para Pessoa Jurídica) a partir de uma API externa ocorre no método `save()`.
    O gerenciamento do endereço (criação, atualização, exclusão) também é
    centralizado no método `save()`.
    """

    CUSTOMER_TYPE_CHOICES = [("IND", "Pessoa Física"), ("CORP", "Pessoa Jurídica")]

    addresses = GenericRelation(
        Address,
        related_query_name="customer",
        content_type_field="content_type",
        object_id_field="object_id",
        verbose_name="Endereços",
    )
    customer_type = models.CharField(
        verbose_name="Tipo de Cliente",
        max_length=6,
        choices=CUSTOMER_TYPE_CHOICES,
        default="IND",
    )
    full_name = models.CharField(
        verbose_name="Nome Completo / Razão Social", max_length=100
    )
    preferred_name = models.CharField(
        verbose_name="Apelido / Nome Fantasia", max_length=50, blank=True, null=True
    )
    phone = models.CharField(
        verbose_name="Telefone",
        max_length=11,
        validators=[
            RegexValidator(r"^\d{10,11}$", "Telefone deve ter 10 ou 11 dígitos.")
        ],
        blank=True,
        null=True,
    )
    email = models.EmailField(verbose_name="E-mail", blank=True, null=True)
    tax_id = models.CharField(
        verbose_name="CPF/CNPJ",
        max_length=18,
        unique=True,
    )
    is_active = models.BooleanField(verbose_name="Ativo", default=True)
    registration_date = models.DateTimeField(
        verbose_name="Data de Cadastro", auto_now_add=True
    )
    is_vip = models.BooleanField(verbose_name="VIP", default=False)
    profession = models.CharField(
        verbose_name="Profissão", max_length=50, blank=True, null=True
    )
    interests = models.TextField(verbose_name="Interesses", blank=True, null=True)
    notes = models.TextField(verbose_name="Observações", blank=True, null=True)

    _fetched_api_data_this_save = None

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["-registration_date", "full_name"]
        indexes = [
            models.Index(fields=["full_name"]),
            models.Index(fields=["tax_id"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        """Retorna a representação textual do cliente."""
        return f"{self.display_name} ({self.formatted_tax_id})"

    def clean(self):
        """
        Executa validações e limpeza dos dados do cliente antes de salvar.

        Este método é chamado automaticamente pelo Django durante a validação do modelo
        (e.g., em `full_clean`).
        - Valida o formato e os dígitos verificadores do CPF/CNPJ, de acordo com o
          `customer_type` (Tipo de Cliente).
        - Limpa o campo `phone`, removendo caracteres não numéricos.
        """
        super().clean()
        self._validate_and_clean_tax_id()
        self._clean_phone()

    def _validate_and_clean_tax_id(self):
        """
        Valida o formato e os dígitos verificadores do CPF/CNPJ e armazena apenas os números.

        Levanta `ValidationError` se:
        - `tax_id` estiver vazio.
        - `customer_type` não estiver definido.
        - O `tax_id` não corresponder ao tipo de cliente (CPF para Pessoa Física,
          CNPJ para Pessoa Jurídica) em termos de comprimento ou validade.
        """
        if not self.tax_id:
            raise ValidationError({"tax_id": "Documento (CPF/CNPJ) obrigatório!"})

        cleaned_tax_id = "".join(filter(str.isdigit, self.tax_id))

        if not self.customer_type:
            raise ValidationError({"customer_type": "Tipo de cliente não definido."})

        validator_map = {
            "IND": {"len": 11, "validator": CPF(), "msg": "CPF inválido!"},
            "CORP": {"len": 14, "validator": CNPJ(), "msg": "CNPJ inválido!"},
        }

        config = validator_map.get(self.customer_type)
        if not config:
            raise ValidationError(
                {"customer_type": "Tipo de cliente inválido para validar documento."}
            )

        if len(cleaned_tax_id) != config["len"]:
            raise ValidationError(
                {"tax_id": f"{config['msg']} Deve conter {config['len']} números."}
            )
        if not config["validator"].validate(cleaned_tax_id):
            raise ValidationError({"tax_id": config["msg"]})

        self.tax_id = cleaned_tax_id

    def _clean_phone(self):
        """Remove caracteres não numéricos do campo telefone e armazena apenas os dígitos."""
        if self.phone:
            self.phone = "".join(filter(str.isdigit, self.phone))

    def save(self, *args, **kwargs):
        """
        Salva a instância do Cliente e gerencia seu endereço associado.

        Este método é sobrescrito para incorporar lógica adicional antes e depois
        da persistência do cliente:
        1.  **Busca de Dados Externos (PJ):** Se o cliente for Pessoa Jurídica (CORP),
            tenta buscar dados da empresa (Razão Social, Nome Fantasia, Endereço)
            usando o CNPJ através do serviço `fetch_company_data`.
            Os campos `full_name` e `preferred_name` podem ser atualizados com
            os dados da API.
        2.  **Validação Completa:** Executa `self.full_clean()` para garantir que
            todas as validações do modelo (incluindo as do método `clean()`)
            sejam aplicadas.
        3.  **Persistência do Cliente:** Salva a instância do cliente no banco de dados.
        4.  **Gerenciamento do Endereço:**
            -   Utiliza o argumento `address_data` (um dicionário opcional, geralmente
                vindo de um formulário) para determinar a ação sobre o endereço.
            -   Se `address_data` contiver dados válidos, um endereço é criado/atualizado.
            -   Se `address_data` for um dicionário vazio (`{}`), o endereço existente
                (se houver) é removido.
            -   Se `address_data` não for fornecido (`None`) e o cliente for PJ,
                os dados de endereço obtidos da API (se houver) são usados para
                criar/atualizar o endereço.
            -   Se nenhuma das condições acima for atendida, o endereço existente
                (ou a ausência de um) é mantido.
        Toda a operação de salvamento do cliente e gerenciamento do endereço ocorre
        dentro de uma transação atômica para garantir a consistência dos dados.

        Args:
            *args: Argumentos posicionais passados para o método `save` original.
            **kwargs: Argumentos nomeados passados para o método `save` original.
                      Pode incluir `address_data` (dict, opcional) para controle
                      explícito do endereço.
        """
        address_data_from_form = kwargs.pop("address_data", None)
        self._fetched_api_data_this_save = False

        company_api_data = None
        if self.customer_type == "CORP":
            temp_cleaned_tax_id = "".join(filter(str.isdigit, self.tax_id or ""))
            if len(temp_cleaned_tax_id) == 14:
                company_api_data = fetch_company_data(temp_cleaned_tax_id)
                self._fetched_api_data_this_save = True

            if company_api_data:
                if company_api_data.get("full_name"):
                    self.full_name = company_api_data["full_name"]
                if company_api_data.get("preferred_name"):
                    self.preferred_name = company_api_data["preferred_name"]

        self.full_clean()

        with transaction.atomic():
            super().save(*args, **kwargs)

            # Determina os dados finais do endereço a serem persistidos
            final_address_data_to_persist = None
            address_source_is_api = False
            perform_delete_address = False

            form_provided_data = address_data_from_form is not None
            form_has_valid_address_fields = (
                form_provided_data
                and isinstance(address_data_from_form, dict)
                and address_data_from_form
                and any(
                    v for v in address_data_from_form.values() if v not in [None, ""]
                )
            )
            form_requested_clear_address = (
                form_provided_data
                and isinstance(address_data_from_form, dict)
                and not address_data_from_form  # É {}
            )

            if form_has_valid_address_fields:
                final_address_data_to_persist = address_data_from_form
            elif form_requested_clear_address:
                perform_delete_address = True
            elif self.customer_type == "CORP" and not form_provided_data:
                if not self._fetched_api_data_this_save and not company_api_data:
                    company_api_data = fetch_company_data(self.tax_id)

                if company_api_data:
                    api_address_payload = {
                        k: company_api_data.get(k)
                        for k in [
                            "zip_code",
                            "street",
                            "number",
                            "complement",
                            "neighborhood",
                            "city",
                            "state",
                        ]
                    }
                    if any(
                        v for v in api_address_payload.values() if v not in [None, ""]
                    ):
                        final_address_data_to_persist = api_address_payload
                        address_source_is_api = True

            # Executa a ação no endereço
            if final_address_data_to_persist:
                self._update_or_create_address_from_data(
                    final_address_data_to_persist, from_api=address_source_is_api
                )
            elif perform_delete_address:
                self._delete_existing_address()

        # Limpa o atributo temporário após o save
        if hasattr(self, "_fetched_api_data_this_save"):
            delattr(self, "_fetched_api_data_this_save")

    def _update_or_create_address_from_data(
        self, address_data: dict, from_api: bool = False
    ):
        """
        Cria ou atualiza o endereço associado ao cliente com os dados fornecidos.

        Filtra chaves com valores `None` ou string vazia dos dados de endereço
        antes de passá-los para `Address.objects.update_or_create`.
        Loga a ação realizada (criação/atualização) e a origem dos dados (API/formulário).

        Args:
            address_data: Dicionário contendo os dados do endereço.
            from_api: Booleano indicando se os dados vieram da API (True) ou do formulário (False).

        Raises:
            ValidationError: Se ocorrer um erro de validação ao salvar o objeto `Address`.
                             Isso permite que a transação seja revertida e o erro
                             seja tratado (e.g., exibido no formulário).
        """
        cleaned_address_data = {
            k: v for k, v in address_data.items() if v not in [None, ""]
        }

        if not cleaned_address_data:
            source = "API" if from_api else "formulário"
            logger.info(
                f"Nenhum dado de endereço válido da {source} para Cliente ID {self.pk}."
            )
            return

        content_type = ContentType.objects.get_for_model(self)
        try:
            addr_obj, created = Address.objects.update_or_create(
                content_type=content_type,
                object_id=self.pk,
                defaults=cleaned_address_data,
            )
            action = "criado" if created else "atualizado"
            source_log = "API" if from_api else "formulário"
            logger.info(
                f"Endereço {action} para Cliente ID {self.pk} via {source_log} com dados: {cleaned_address_data}"
            )
        except ValidationError as e:
            logger.error(
                f"Erro de validação ao salvar endereço para Cliente ID {self.pk}: {e.message_dict if hasattr(e, 'message_dict') else e.messages}"
            )
            raise  # Propaga o erro para reverter a transação e permitir tratamento

    def _delete_existing_address(self):
        """Deleta o primeiro endereço associado a este cliente, se existir."""
        existing_address = self.addresses.first()
        if existing_address:
            existing_address.delete()
            logger.info(f"Endereço existente deletado para Cliente ID {self.pk}.")

    @property
    def address(self) -> Address | None:
        """
        Retorna o primeiro endereço associado ao cliente, ou `None` se não houver.

        A `GenericRelation` `addresses` pode, teoricamente, conter múltiplos endereços.
        Esta propriedade simplifica o acesso ao "endereço principal" ou único,
        assumindo que, para muitos casos de uso, um cliente terá no máximo um endereço
        gerenciado desta forma. Se múltiplos endereços forem uma realidade comum,
        o acesso direto a `self.addresses.all()` seria mais apropriado em outros contextos.
        """
        return self.addresses.first()

    @cached_property
    def display_name(self) -> str:
        """
        Retorna o nome de exibição do cliente.

        Prioriza o `preferred_name` (Apelido / Nome Fantasia). Se não estiver
        disponível, usa `full_name` (Nome Completo / Razão Social).
        Como fallback, retorna "Cliente [ID]".
        """
        return self.preferred_name or self.full_name or f"Cliente {self.pk}"

    @cached_property
    def formatted_phone(self) -> str:
        """
        Retorna o número de telefone formatado com máscara (e.g., (XX) XXXXX-XXXX).

        O campo `phone` já é armazenado apenas com dígitos.
        """
        if not self.phone:
            return ""
        if len(self.phone) == 10:  # Formato (XX) XXXX-XXXX
            return f"({self.phone[:2]}) {self.phone[2:6]}-{self.phone[6:]}"
        if len(self.phone) == 11:  # Formato (XX) XXXXX-XXXX
            return f"({self.phone[:2]}) {self.phone[2:7]}-{self.phone[7:]}"
        return self.phone  # Retorna sem formatação se não se encaixar nos padrões

    @cached_property
    def formatted_tax_id(self) -> str:
        """
        Retorna o CPF/CNPJ formatado com máscara.

        O campo `tax_id` já é armazenado apenas com dígitos.
        Formata como XXX.XXX.XXX-XX para CPF e XX.XXX.XXX/XXXX-XX para CNPJ.
        """
        current_tax_id = self.tax_id
        if not current_tax_id:
            return ""
        if len(current_tax_id) == 11:  # CPF
            return f"{current_tax_id[:3]}.{current_tax_id[3:6]}.{current_tax_id[6:9]}-{current_tax_id[9:]}"
        if len(current_tax_id) == 14:  # CNPJ
            return f"{current_tax_id[:2]}.{current_tax_id[2:5]}.{current_tax_id[5:8]}/{current_tax_id[8:12]}-{current_tax_id[12:]}"
        return current_tax_id  # Retorna sem formatação se não se encaixar
