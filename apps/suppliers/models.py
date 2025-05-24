# apps/suppliers/models.py
from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError # Alterado de django.forms para django.core.exceptions
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils.functional import cached_property # Adicionado
from apps.addresses.models import Address
from core.services import fetch_company_data
from validate_docbr import CPF, CNPJ
import logging

logger = logging.getLogger(__name__)

class Supplier(models.Model):
    SUPPLIER_TYPE_CHOICES = [
        ('IND', 'Pessoa Física'),
        ('CORP', 'Pessoa Jurídica'),
    ]

    addresses = GenericRelation(
        Address,
        related_query_name='supplier',
        content_type_field='content_type',
        object_id_field='object_id',
        verbose_name="Endereços", # Adicionado verbose_name
    )
    supplier_type = models.CharField(
        verbose_name='Tipo de Fornecedor',
        max_length=6,
        choices=SUPPLIER_TYPE_CHOICES,
        default='CORP' # Mantido CORP como default, diferente de Customer (IND)
    )
    full_name = models.CharField(
        verbose_name='Razão Social / Nome Completo',
        max_length=100,
        # Removido blank=False, null=False, default="" pois CharField já é não nulo e não branco por padrão
        # Se precisar de default, pode manter, mas não é estritamente necessário se o form sempre envia.
        help_text="Nome completo (PF) ou Razão Social (PJ)"
    )
    preferred_name = models.CharField(
        verbose_name='Nome Fantasia / Apelido',
        max_length=50,
        blank=True,
        null=True
    )
    tax_id = models.CharField(
        verbose_name='CNPJ/CPF',
        max_length=18, # Aumentado para acomodar máscaras no BD, mas limparemos para 11/14
        unique=True
    )
    state_registration = models.CharField(
        verbose_name='Inscrição Estadual',
        max_length=20,
        blank=True,
        null=True
    )
    municipal_registration = models.CharField(
        verbose_name='Inscrição Municipal',
        max_length=20,
        blank=True,
        null=True
    )
    phone = models.CharField(
        verbose_name='Telefone',
        max_length=11,
        validators=[RegexValidator(r'^\d{10,11}$', "Telefone deve ter 10 ou 11 dígitos.")], # Mantido validador
        blank=True,
        null=True
    )
    email = models.EmailField(
        verbose_name='E-mail',
        blank=True,
        null=True
    )
    contact_person = models.CharField(
        verbose_name='Pessoa de Contato',
        max_length=100,
        blank=True,
        null=True
    )
    bank_name = models.CharField(
        verbose_name='Banco',
        max_length=50,
        blank=True,
        null=True
    )
    bank_agency = models.CharField(
        verbose_name='Agência',
        max_length=10,
        blank=True,
        null=True
    )
    bank_account = models.CharField(
        verbose_name='Conta',
        max_length=20,
        blank=True,
        null=True
    )
    pix_key = models.CharField(
        verbose_name='Chave PIX',
        max_length=100,
        blank=True,
        null=True
    )
    is_active = models.BooleanField(
        verbose_name='Ativo',
        default=True
    )
    registration_date = models.DateTimeField(
        verbose_name='Data de Cadastro',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        verbose_name='Última Atualização',
        auto_now=True
    )
    notes = models.TextField(
        verbose_name='Observações',
        blank=True,
        null=True
    )

    _fetched_api_data_this_save = None # Adicionado, como em Customer

    class Meta:
        verbose_name = 'Fornecedor'
        verbose_name_plural = 'Fornecedores'
        ordering = ['-registration_date', 'full_name']
        indexes = [
            models.Index(fields=['full_name']),
            models.Index(fields=['tax_id']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.formatted_tax_id})" # Alinhado com Customer

    def clean(self):
        super().clean()
        self._validate_and_clean_tax_id()
        self._clean_phone()
        # Validação de preferred_name para PJ (pode ser mantida aqui ou no form)
        if self.supplier_type == 'CORP' and not self.preferred_name:
            # Se for obrigatório apenas no contexto do form, pode ser removido daqui
            # e tratado no Form.clean() se a API não preencher.
            # Por ora, mantendo a lógica do Customer, que não tem essa validação no model.
            pass


    def _validate_and_clean_tax_id(self):
        if not self.tax_id:
            raise ValidationError({"tax_id": "Documento (CNPJ/CPF) obrigatório!"})

        cleaned_tax_id = "".join(filter(str.isdigit, self.tax_id))

        if not self.supplier_type:
            raise ValidationError({"supplier_type": "Tipo de fornecedor não definido."})

        validator_map = {
            "IND": {"len": 11, "validator": CPF(), "msg": "CPF inválido!"},
            "CORP": {"len": 14, "validator": CNPJ(), "msg": "CNPJ inválido!"},
        }

        config = validator_map.get(self.supplier_type)
        if not config:
            raise ValidationError(
                {"supplier_type": "Tipo de fornecedor inválido para validar documento."}
            )

        if len(cleaned_tax_id) != config["len"]:
            raise ValidationError(
                {"tax_id": f"{config['msg']} Deve conter {config['len']} números."}
            )
        if not config["validator"].validate(cleaned_tax_id):
            raise ValidationError({"tax_id": config["msg"]})

        self.tax_id = cleaned_tax_id

    def _clean_phone(self):
        if self.phone:
            self.phone = "".join(filter(str.isdigit, self.phone))

    def save(self, *args, **kwargs):
        address_data_from_form = kwargs.pop("address_data", None)
        self._fetched_api_data_this_save = False # Flag para controlar busca na API

        company_api_data = None
        if self.supplier_type == "CORP":
            # Limpa o tax_id para a busca na API, caso venha com máscara
            temp_cleaned_tax_id = "".join(filter(str.isdigit, self.tax_id or ""))
            if len(temp_cleaned_tax_id) == 14: # Garante que só busca se for um CNPJ "limpável"
                company_api_data = fetch_company_data(temp_cleaned_tax_id)
                self._fetched_api_data_this_save = True # Marca que a API foi consultada

            if company_api_data:
                if company_api_data.get("full_name"):
                    self.full_name = company_api_data["full_name"]
                if company_api_data.get("preferred_name"):
                    self.preferred_name = company_api_data["preferred_name"]
                # Específico de Supplier:
                if company_api_data.get("state_registration"):
                    self.state_registration = company_api_data["state_registration"]
                # municipal_registration não costuma vir de APIs de CNPJ comuns

        self.full_clean() # Chama full_clean ANTES de salvar o objeto principal

        with transaction.atomic():
            super().save(*args, **kwargs) # Salva o Supplier

            # Lógica para determinar os dados do endereço a serem persistidos
            final_address_data_to_persist = None
            address_source_is_api = False
            perform_delete_address = False

            form_provided_data = address_data_from_form is not None
            form_has_valid_address_fields = (
                form_provided_data
                and isinstance(address_data_from_form, dict)
                and address_data_from_form # Garante que não é {}
                and any(v for v in address_data_from_form.values() if v not in [None, ""])
            )
            form_requested_clear_address = (
                form_provided_data and isinstance(address_data_from_form, dict) and not address_data_from_form # É {}
            )

            if form_has_valid_address_fields:
                final_address_data_to_persist = address_data_from_form
            elif form_requested_clear_address:
                perform_delete_address = True
            elif self.supplier_type == "CORP" and not form_provided_data:
                # Se o form não enviou dados de endereço e é PJ, tenta usar da API
                if not self._fetched_api_data_this_save and not company_api_data : # Se não buscou API ainda
                    company_api_data = fetch_company_data(self.tax_id) # self.tax_id já está limpo aqui

                if company_api_data:
                    api_address_payload = {
                        k: company_api_data.get(k)
                        for k in ["zip_code", "street", "number", "complement", "neighborhood", "city", "state"]
                        if company_api_data.get(k) # Inclui apenas se a API retornou algo para a chave
                    }
                    if any(v for v in api_address_payload.values() if v not in [None, ""]): # Se há algum dado de endereço da API
                        final_address_data_to_persist = api_address_payload
                        address_source_is_api = True
            
            # Ação no endereço
            if final_address_data_to_persist:
                self._update_or_create_address_from_data(
                    final_address_data_to_persist, from_api=address_source_is_api
                )
            elif perform_delete_address:
                self._delete_existing_address()

        # Limpa a flag temporária
        if hasattr(self, '_fetched_api_data_this_save'):
            delattr(self, '_fetched_api_data_this_save')

    def _update_or_create_address_from_data(self, address_data: dict, from_api: bool = False):
        cleaned_address_data = {
            k: v for k, v in address_data.items() if v not in [None, ""]
        }

        if not cleaned_address_data:
            source = "API" if from_api else "formulário"
            logger.info(
                f"Nenhum dado de endereço válido da {source} para Fornecedor ID {self.pk}."
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
                f"Endereço {action} para Fornecedor ID {self.pk} via {source_log} com dados: {cleaned_address_data}"
            )
        except ValidationError as e: # Captura ValidationError do Django Core
            logger.error(
                f"Erro de validação ao salvar endereço para Fornecedor ID {self.pk}: {e.message_dict if hasattr(e, 'message_dict') else e.messages}"
            )
            raise

    def _delete_existing_address(self):
        existing_address = self.addresses.first()
        if existing_address:
            existing_address.delete()
            logger.info(f"Endereço existente deletado para Fornecedor ID {self.pk}.")

    @property
    def address(self) -> Address | None:
        return self.addresses.first()

    @cached_property
    def display_name(self) -> str:
        return self.preferred_name or self.full_name or f"Fornecedor {self.pk}"

    @cached_property
    def formatted_phone(self) -> str:
        if not self.phone:
            return ""
        # self.phone já deve estar limpo pelo _clean_phone
        if len(self.phone) == 10:
            return f"({self.phone[:2]}) {self.phone[2:6]}-{self.phone[6:]}"
        if len(self.phone) == 11:
            return f"({self.phone[:2]}) {self.phone[2:7]}-{self.phone[7:]}"
        return self.phone

    @cached_property # Adicionado cached_property
    def formatted_tax_id(self) -> str: # Alterado nome do método para consistência
        # self.tax_id já deve estar limpo pelo _validate_and_clean_tax_id
        current_tax_id = self.tax_id 
        if not current_tax_id:
            return ""
        if len(current_tax_id) == 11:  # CPF
            return f"{current_tax_id[:3]}.{current_tax_id[3:6]}.{current_tax_id[6:9]}-{current_tax_id[9:]}"
        if len(current_tax_id) == 14:  # CNPJ
            return f"{current_tax_id[:2]}.{current_tax_id[2:5]}.{current_tax_id[5:8]}/{current_tax_id[8:12]}-{current_tax_id[12:]}"
        return current_tax_id