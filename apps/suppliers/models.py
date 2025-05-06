from django.db import models
from django.core.validators import RegexValidator, EmailValidator
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.forms import ValidationError
from django.db import transaction
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

    # Relacionamento genérico com Address
    addresses = GenericRelation(
        Address,
        related_query_name='supplier',
        content_type_field='content_type',
        object_id_field='object_id'
    )

    # Informações básicas
    supplier_type = models.CharField(
        verbose_name='Tipo de Fornecedor',
        max_length=6,
        choices=SUPPLIER_TYPE_CHOICES,
        default='CORP'
    )
    full_name = models.CharField(
        verbose_name='Razão Social / Nome Completo',
        max_length=100,
        blank=False,  
        null=False,  
        default="",
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
        max_length=18,
        unique=True
    )

    # Informações fiscais
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

    # Contato
    phone = models.CharField(
        verbose_name='Telefone',
        max_length=11,
        validators=[RegexValidator(r'^\d{10,11}$')],
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

    # Dados bancários
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

    # Status e metadados
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

    class Meta:
        verbose_name = 'Fornecedor'
        verbose_name_plural = 'Fornecedores'
        ordering = ['-registration_date', 'full_name']
        indexes = [
            models.Index(fields=['full_name']),
            models.Index(fields=['tax_id']),
            models.Index(fields=['is_active']),
        ]

    def clean(self):
        """Validação de CPF/CNPJ"""
        super().clean()

        if self.tax_id:
            tax_id = self.tax_id.replace('.', '').replace('-', '').replace('/', '').strip()

            if self.supplier_type == "IND":
                if not CPF().validate(tax_id):
                    raise ValidationError({'tax_id': "CPF inválido!"})
            elif self.supplier_type == "CORP":
                if not CNPJ().validate(tax_id):
                    raise ValidationError({'tax_id': "CNPJ inválido!"})

            self.tax_id = tax_id

    def save(self, *args, **kwargs):
        """Consolida a lógica de salvamento do fornecedor e endereço"""
        with transaction.atomic():
            is_new = self.pk is None  # Verifica se é uma criação ou atualização
            
            # Salva primeiro o fornecedor para garantir que tem um ID
            super().save(*args, **kwargs)

            # Lógica para Pessoa Jurídica (busca automática de dados)
            if self.supplier_type == "CORP" and self.tax_id:
                self._handle_corporate_supplier()

            # Lógica para endereço (tanto PJ quanto PF)
            if not is_new or 'address_data' in kwargs:
                self._update_or_create_address(kwargs.pop('address_data', None))

    def _handle_corporate_supplier(self):
        """Busca e atualiza dados de PJ automaticamente"""
        data = fetch_company_data(self.tax_id)
        if data:
            self.full_name = data["full_name"]
            self.preferred_name = data["preferred_name"]
            self.state_registration = data.get("state_registration", "")
            super().save(update_fields=['full_name', 'preferred_name', 'state_registration'])
            
            # Prepara dados de endereço da API
            address_data = {
                "zip_code": data["zip_code"],
                "street": data["street"],
                "number": data["number"],
                "neighborhood": data["neighborhood"],
                "city": data["city"],
                "state": data["state"],
            }
            self._update_or_create_address(address_data)

    def _update_or_create_address(self, address_data=None):
        if not address_data:
            return

        # Filtra valores vazios
        address_data = {k: v for k, v in address_data.items() if v}
        
        if address_data:
            content_type = ContentType.objects.get_for_model(Supplier)
            address, created = Address.objects.update_or_create(
                content_type=content_type,
                object_id=self.pk,
                defaults=address_data
            )

    @property
    def address(self):
        return self.addresses.first()

    @property
    def display_name(self):
        return self.preferred_name or self.full_name or f"Fornecedor {self.pk}"

    @property
    def formatted_phone(self):
        if not self.phone:
            return ""
        phone = self.phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if len(phone) == 10:
            return f"({phone[:2]}) {phone[2:6]}-{phone[6:]}"
        elif len(phone) == 11:
            return f"({phone[:2]}) {phone[2:7]}-{phone[7:]}"
        return phone

    def __str__(self):
        return f"{self.display_name} ({self.tax_id})"

    def formatted_tax_id(self):
        if not self.tax_id:
            return ""
        tax_id = self.tax_id.replace('.', '').replace('-', '').replace('/', '').strip()
        if len(tax_id) == 11:
            return f"{tax_id[:3]}.{tax_id[3:6]}.{tax_id[6:9]}-{tax_id[9:]}"
        elif len(tax_id) == 14:
            return f"{tax_id[:2]}.{tax_id[2:5]}.{tax_id[5:8]}/{tax_id[8:12]}-{tax_id[12:]}"
        return tax_id