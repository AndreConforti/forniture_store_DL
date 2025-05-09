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

class Customer(models.Model):
    CUSTOMER_TYPE_CHOICES = [
        ('IND', 'Pessoa Física'),
        ('CORP', 'Pessoa Jurídica'),
    ]

    # Relacionamento genérico com Address
    addresses = GenericRelation(
        Address,
        related_query_name='customer',
        content_type_field='content_type',
        object_id_field='object_id'
    )

    customer_type = models.CharField(
        verbose_name='Tipo de Cliente',
        max_length=6,
        choices=CUSTOMER_TYPE_CHOICES,
        default='IND'
    )
    
    full_name = models.CharField(
        verbose_name='Nome Completo / Razão Social',    
        max_length=100,
        blank=True,
        null=True
    )
    
    preferred_name = models.CharField(
        verbose_name='Apelido / Nome Fantasia',
        max_length=50,
        blank=True,
        null=True
    )

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

    tax_id = models.CharField(
        verbose_name='CPF/CNPJ',
        max_length=18,
        blank=True,
        null=True,
        unique=True,
    )

    is_active = models.BooleanField(
        verbose_name='Ativo',
        default=True
    )
    
    registration_date = models.DateTimeField(
        verbose_name='Data de Cadastro',
        auto_now_add=True
    )
    
    is_vip = models.BooleanField(
        verbose_name='VIP',
        default=False
    )

    profession = models.CharField(
        verbose_name='Profissão',
        max_length=50,
        blank=True,
        null=True
    )
    
    interests = models.TextField(
        verbose_name='Interesses',
        blank=True,
        null=True
    )
    
    notes = models.TextField(
        verbose_name='Observações',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
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

            if self.customer_type == "IND":
                if not CPF().validate(tax_id):
                    raise ValidationError({'tax_id': "CPF inválido!"})
            elif self.customer_type == "CORP":
                if not CNPJ().validate(tax_id):
                    raise ValidationError({'tax_id': "CNPJ inválido!"})

            self.tax_id = tax_id

    def save(self, *args, **kwargs):
        """Consolida a lógica de salvamento do cliente e endereço"""
        with transaction.atomic():
            is_new = self.pk is None  # Verifica se é uma criação ou atualização
            
            # Salva primeiro o cliente para garantir que tem um ID
            super().save(*args, **kwargs)

            # Lógica para Pessoa Jurídica (busca automática de dados)
            if self.customer_type == "CORP" and self.tax_id:
                self._handle_corporate_customer()

            # Lógica para endereço (tanto PJ quanto PF)
            if not is_new or 'address_data' in kwargs:
                self._update_or_create_address(kwargs.pop('address_data', None))

    def _handle_corporate_customer(self):
        """Busca e atualiza dados de PJ automaticamente"""
        data = fetch_company_data(self.tax_id)
        if data:
            self.full_name = data["full_name"]
            self.preferred_name = data["preferred_name"]
            super().save(update_fields=['full_name', 'preferred_name'])
            
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
            content_type = ContentType.objects.get_for_model(Customer)
            address, created = Address.objects.update_or_create(
                content_type=content_type,  # Campo content_type (não content_type__model)
                object_id=self.pk,          # ID do cliente
                defaults=address_data
            )

    @property
    def address(self):
        return self.addresses.first()

    @property
    def display_name(self):
        return self.preferred_name or self.full_name or f"Cliente {self.pk}"

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