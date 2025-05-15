from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils.functional import cached_property
from apps.addresses.models import Address  # Ajuste o caminho se necessário
from core.services import fetch_company_data  # Ajuste o caminho se necessário
from validate_docbr import CPF, CNPJ
import logging

logger = logging.getLogger(__name__)


class Customer(models.Model):
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
        max_length=18,  # Permite entrada com máscara (ex: XX.XXX.XXX/XXXX-XX)
        unique=True,
        # O valor armazenado no BD será o limpo (11 ou 14 dígitos)
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
        super().clean()
        # _validate_and_clean_tax_id depende de customer_type, então é chamado após
        # garantir que customer_type seja válido ou ter um valor padrão.
        self._validate_and_clean_tax_id()
        self._clean_phone()

    def _validate_and_clean_tax_id(self):
        # Este método é chamado pelo full_clean().
        # O tax_id aqui já deve ter sido limpo pelo formulário se veio de um ModelForm.
        # Se o modelo for salvo diretamente, este método fará a limpeza.
        if not self.tax_id:
            raise ValidationError({"tax_id": "Documento (CPF/CNPJ) obrigatório!"})

        cleaned_tax_id = "".join(filter(str.isdigit, self.tax_id))

        # Garante que customer_type é acessível; se não, pode ser um problema de fluxo.
        # No ModelForm, customer_type já estará no self.instance.
        if not self.customer_type:
            # Isso não deve acontecer se o campo tiver um default e for obrigatório
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
            # O choices do campo customer_type já deve validar isso.
            raise ValidationError(
                {"customer_type": "Tipo de cliente inválido para validar documento."}
            )

        self.tax_id = cleaned_tax_id  # Atribui o valor limpo para ser salvo no BD

    def _clean_phone(self):
        if self.phone:
            self.phone = "".join(filter(str.isdigit, self.phone))

    def save(self, *args, **kwargs):
        address_data_from_form = kwargs.pop("address_data", None)

        # full_clean() é chamado para garantir todas as validações do modelo ANTES do save.
        # Isso inclui _validate_and_clean_tax_id, que modificará self.tax_id para a versão limpa.
        self.full_clean()

        with transaction.atomic():
            super().save(*args, **kwargs)  # Salva o Customer (com tax_id já limpo)

            if self.customer_type == "CORP":
                self._handle_corporate_customer_data_and_address()

            if address_data_from_form is not None:  # Checa se a chave foi passada
                if address_data_from_form:  # Se o dict não for vazio
                    self._update_or_create_address_from_data(address_data_from_form)
                else:  # Se o dict for vazio (ex: todos os campos de endereço limpos no form)
                    self._delete_existing_address()

    def _handle_corporate_customer_data_and_address(self):
        # self.tax_id já está limpo aqui devido ao self.full_clean() no save()
        company_api_data = fetch_company_data(self.tax_id)
        if company_api_data:
            updated_fields = []
            # Compara com os valores atuais da instância
            if (
                company_api_data.get("full_name")
                and self.full_name != company_api_data["full_name"]
            ):
                self.full_name = company_api_data["full_name"]
                updated_fields.append("full_name")
            if (
                company_api_data.get("preferred_name")
                and self.preferred_name != company_api_data["preferred_name"]
            ):
                self.preferred_name = company_api_data["preferred_name"]
                updated_fields.append("preferred_name")

            if updated_fields:
                super().save(
                    update_fields=updated_fields
                )  # Salva apenas os campos alterados do Customer

            address_api_data = {
                "zip_code": company_api_data.get("zip_code"),
                "street": company_api_data.get("street"),
                "number": company_api_data.get("number"),
                "complement": company_api_data.get("complement"),
                "neighborhood": company_api_data.get("neighborhood"),
                "city": company_api_data.get("city"),
                "state": company_api_data.get("state"),
            }
            self._update_or_create_address_from_data(address_api_data, from_api=True)

    def _update_or_create_address_from_data(self, address_data, from_api=False):
        cleaned_address_data = {
            k: v for k, v in address_data.items() if v is not None and v != ""
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
            logger.info(
                f"Endereço {action} para Cliente ID {self.pk} com dados: {cleaned_address_data}"
            )
        except ValidationError as e:
            logger.error(
                f"Erro de validação ao salvar endereço para Cliente ID {self.pk}: {e.message_dict if hasattr(e, 'message_dict') else e.messages}"
            )
            raise

    def _delete_existing_address(self):
        existing_address = self.addresses.first()
        if existing_address:
            existing_address.delete()
            logger.info(f"Endereço existente deletado para Cliente ID {self.pk}.")

    @property
    def address(self):
        return self.addresses.first()

    @cached_property
    def display_name(self):
        return self.preferred_name or self.full_name or f"Cliente {self.pk}"

    @cached_property
    def formatted_phone(self):
        if not self.phone:
            return ""
        # self.phone já está limpo (só dígitos) devido ao _clean_phone
        if len(self.phone) == 10:
            return f"({self.phone[:2]}) {self.phone[2:6]}-{self.phone[6:]}"
        if len(self.phone) == 11:
            return f"({self.phone[:2]}) {self.phone[2:7]}-{self.phone[7:]}"
        return self.phone

    @cached_property
    def formatted_tax_id(self):
        if not self.tax_id:
            return ""
        # self.tax_id já está limpo (só dígitos) devido ao _validate_and_clean_tax_id
        # e armazenado limpo no BD.
        current_tax_id = self.tax_id
        if len(current_tax_id) == 11:  # CPF
            return f"{current_tax_id[:3]}.{current_tax_id[3:6]}.{current_tax_id[6:9]}-{current_tax_id[9:]}"
        if len(current_tax_id) == 14:  # CNPJ
            return f"{current_tax_id[:2]}.{current_tax_id[2:5]}.{current_tax_id[5:8]}/{current_tax_id[8:12]}-{current_tax_id[12:]}"
        return current_tax_id  # Retorna como está se não for formato esperado (improvável após validação)
