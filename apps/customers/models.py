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
    Modelo para representar um Cliente, seja Pessoa Física ou Jurídica.

    Armazena informações básicas, de contato e fiscais do cliente.
    Utiliza GenericRelation para associar-se a um ou mais endereços.
    Inclui lógica para validar CPF/CNPJ e para buscar dados de empresas
    (Pessoa Jurídica) de APIs externas ao salvar.
    """

    CUSTOMER_TYPE_CHOICES = [("IND", "Pessoa Física"), ("CORP", "Pessoa Jurídica")]

    addresses = GenericRelation(
        Address,
        related_query_name="customer",
        content_type_field="content_type",
        object_id_field="object_id",
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
        max_length=11,  # Apenas dígitos
        validators=[
            RegexValidator(r"^\d{10,11}$", "Telefone deve ter 10 ou 11 dígitos.")
        ],
        blank=True,
        null=True,
    )
    email = models.EmailField(verbose_name="E-mail", blank=True, null=True)
    tax_id = models.CharField(
        verbose_name="CPF/CNPJ",
        max_length=18,  # Armazena apenas dígitos
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

    _fetched_api_data_this_save = (
        None  # Para evitar chamadas duplicadas à API em um save
    )

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["-registration_date", "full_name"]
        indexes = [
            models.Index(fields=["full_name"]),
            models.Index(fields=["tax_id"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.formatted_tax_id})"

    def clean(self):
        """
        Realiza validações e limpeza dos dados do cliente antes de salvar.
        Valida CPF/CNPJ de acordo com o tipo de cliente e limpa o telefone.
        """
        super().clean()
        self._validate_and_clean_tax_id()
        self._clean_phone()

    def _validate_and_clean_tax_id(self):
        """Valida o CPF/CNPJ (formato, dígitos verificadores) e armazena apenas os números."""
        if not self.tax_id:
            raise ValidationError({"tax_id": "Documento (CPF/CNPJ) obrigatório!"})

        cleaned_tax_id = "".join(filter(str.isdigit, self.tax_id))

        if not self.customer_type:
            raise ValidationError({"customer_type": "Tipo de cliente não definido."})

        if self.customer_type == "IND":
            if len(cleaned_tax_id) != 11:
                raise ValidationError(
                    {"tax_id": "CPF inválido! Deve conter 11 números."}
                )
            if not CPF().validate(cleaned_tax_id):
                raise ValidationError({"tax_id": "CPF inválido!"})
        elif self.customer_type == "CORP":
            if len(cleaned_tax_id) != 14:
                raise ValidationError(
                    {"tax_id": "CNPJ inválido! Deve conter 14 números."}
                )
            if not CNPJ().validate(cleaned_tax_id):
                raise ValidationError({"tax_id": "CNPJ inválido!"})
        else:
            raise ValidationError(
                {"customer_type": "Tipo de cliente inválido para validar documento."}
            )
        self.tax_id = cleaned_tax_id

    def _clean_phone(self):
        """Armazena apenas os dígitos do número de telefone."""
        if self.phone:
            self.phone = "".join(filter(str.isdigit, self.phone))

    def save(self, *args, **kwargs):
        """
        Salva a instância do Cliente e gerencia seu endereço.

        Argumentos:
            address_data (dict, opcional): Um dicionário contendo os dados do endereço
                provenientes de um formulário. Se for um dicionário vazio `{}`,
                indica uma intenção de remover o endereço existente. Se for `None`,
                nenhuma ação explícita do formulário sobre o endereço é considerada,
                e para clientes PJ, dados da API podem ser usados.

        Lógica:
        1. Atualiza nome/fantasia de clientes PJ com dados da API, se disponíveis.
        2. Valida todos os campos do cliente (`full_clean`).
        3. Salva o cliente.
        4. Determina a ação para o endereço:
           - Usar dados do `address_data` do formulário (maior prioridade).
           - Se `address_data` for `{}`, deletar endereço.
           - Se `address_data` for `None` e cliente for PJ, usar dados da API.
           - Se nenhuma das anteriores, manter endereço existente ou nenhum endereço.
        5. Executa a ação de criar/atualizar ou deletar o endereço.
        """
        address_data_from_form = kwargs.pop("address_data", None)
        self._fetched_api_data_this_save = None  # Reseta o flag

        # Etapa 1: Atualizar campos do cliente (nome/fantasia) com dados da API para PJ
        # Esta etapa acontece ANTES do full_clean para que os valores da API (se usados)
        # sejam validados e salvos corretamente.
        company_api_data = None
        if self.customer_type == "CORP":
            # O self.tax_id ainda pode ter máscara aqui se o save for chamado diretamente.
            # O full_clean() abaixo limpará o tax_id. Para a API, passamos o tax_id já limpo.
            # No entanto, se o form chamou, tax_id já está limpo na instância.
            # Se chamado direto, _validate_and_clean_tax_id ainda não rodou.
            # Então, limpamos localmente para a API.
            temp_cleaned_tax_id = "".join(filter(str.isdigit, self.tax_id or ""))
            if len(temp_cleaned_tax_id) == 14:  # Apenas busca se parecer um CNPJ válido
                company_api_data = fetch_company_data(temp_cleaned_tax_id)
                self._fetched_api_data_this_save = True  # Marca que buscou

            if company_api_data:
                # Decide se atualiza baseado nos dados da API.
                # Poderia haver lógica aqui para não sobrescrever dados do formulário.
                # Por ora, a API tem preferência para nome/fantasia se retornar dados.
                if company_api_data.get("full_name"):
                    self.full_name = company_api_data["full_name"]
                if company_api_data.get("preferred_name"):
                    self.preferred_name = company_api_data["preferred_name"]

        # Etapa 2: Validação completa do cliente
        self.full_clean()  # Garante que tax_id seja limpo e validado, entre outros.

        with transaction.atomic():
            # Etapa 3: Salvar o cliente
            super().save(*args, **kwargs)

            # Etapa 4: Lógica de decisão para o endereço
            final_address_data_to_persist = None
            address_source_is_api = False
            perform_delete_address = False

            form_provided_data = address_data_from_form is not None
            form_has_valid_address_fields = (
                form_provided_data
                and address_data_from_form  # Não é um dicionário vazio
                and any(
                    v
                    for v in address_data_from_form.values()
                    if v is not None and v != ""
                )
            )
            form_requested_clear_address = (
                form_provided_data and not address_data_from_form
            )  # É um {}

            if form_has_valid_address_fields:
                final_address_data_to_persist = address_data_from_form
            elif form_requested_clear_address:
                perform_delete_address = True
            elif (
                self.customer_type == "CORP"
            ):  # Sem instrução do form, tenta API para PJ
                if (
                    not self._fetched_api_data_this_save and not company_api_data
                ):  # Evita buscar novamente
                    company_api_data = fetch_company_data(
                        self.tax_id
                    )  # self.tax_id já limpo

                if company_api_data:
                    api_address_payload = {
                        "zip_code": company_api_data.get("zip_code"),
                        "street": company_api_data.get("street"),
                        "number": company_api_data.get("number"),
                        "complement": company_api_data.get("complement"),
                        "neighborhood": company_api_data.get("neighborhood"),
                        "city": company_api_data.get("city"),
                        "state": company_api_data.get("state"),
                    }
                    if any(
                        v
                        for v in api_address_payload.values()
                        if v is not None and v != ""
                    ):
                        final_address_data_to_persist = api_address_payload
                        address_source_is_api = True
                    # Se API não tem dados e form não disse nada, endereço existente é mantido.

            # Etapa 5: Executar ação no endereço
            if final_address_data_to_persist:
                self._update_or_create_address_from_data(
                    final_address_data_to_persist, from_api=address_source_is_api
                )
            elif perform_delete_address:
                self._delete_existing_address()

        if hasattr(self, "_fetched_api_data_this_save"):  # Limpa o atributo temporário
            delattr(self, "_fetched_api_data_this_save")

    def _update_or_create_address_from_data(self, address_data, from_api=False):
        """Cria ou atualiza o endereço associado ao cliente com os dados fornecidos."""
        # Filtra chaves com valores None ou string vazia dos dados de endereço
        # para evitar passar chaves vazias para o Address.objects.update_or_create defaults.
        # O modelo Address já define blank=True para a maioria dos campos.
        cleaned_address_data = {
            k: v for k, v in address_data.items() if v is not None and v != ""
        }

        if not cleaned_address_data:  # Não faz nada se não houver dados válidos
            source = "API" if from_api else "formulário"
            logger.info(
                f"Nenhum dado de endereço válido da {source} para Cliente ID {self.pk}."
            )
            # Se havia uma intenção de deletar (form vazio), isso é tratado por _delete_existing_address.
            # Se chegou aqui, é porque os dados (da API ou form) eram insuficientes.
            # Poderia deletar se source_is_api=False e dados insuficientes, mas
            # a lógica de deleção já está separada.
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
            # Propagar o erro para que a transação seja revertida e o formulário possa exibi-lo.
            raise

    def _delete_existing_address(self):
        """Deleta o primeiro endereço associado a este cliente, se existir."""
        existing_address = self.addresses.first()
        if existing_address:
            existing_address.delete()
            logger.info(f"Endereço existente deletado para Cliente ID {self.pk}.")

    @property
    def address(self):
        """Retorna o primeiro endereço associado ao cliente, ou None."""
        return self.addresses.first()

    @cached_property
    def display_name(self):
        """Retorna o nome preferido ou o nome completo do cliente."""
        return self.preferred_name or self.full_name or f"Cliente {self.pk}"

    @cached_property
    def formatted_phone(self):
        """Retorna o número de telefone formatado."""
        if not self.phone:
            return ""
        # self.phone já está limpo (só dígitos)
        if len(self.phone) == 10:
            return f"({self.phone[:2]}) {self.phone[2:6]}-{self.phone[6:]}"
        if len(self.phone) == 11:
            return f"({self.phone[:2]}) {self.phone[2:7]}-{self.phone[7:]}"
        return self.phone

    @cached_property
    def formatted_tax_id(self):
        """Retorna o CPF/CNPJ formatado."""
        # self.tax_id é armazenado limpo (só dígitos)
        current_tax_id = self.tax_id
        if not current_tax_id:
            return ""
        if len(current_tax_id) == 11:  # CPF
            return f"{current_tax_id[:3]}.{current_tax_id[3:6]}.{current_tax_id[6:9]}-{current_tax_id[9:]}"
        if len(current_tax_id) == 14:  # CNPJ
            return f"{current_tax_id[:2]}.{current_tax_id[2:5]}.{current_tax_id[5:8]}/{current_tax_id[8:12]}-{current_tax_id[12:]}"
        return current_tax_id
