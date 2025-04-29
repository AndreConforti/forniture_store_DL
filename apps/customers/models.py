from django.db import models
from django.core.validators import RegexValidator, EmailValidator
from django.contrib.contenttypes.fields import GenericRelation
from django.forms import ValidationError
from django.db import transaction
from apps.addresses.models import Address
from core.services import fetch_company_data
from validate_docbr import CPF, CNPJ
import logging
import requests
import pprint

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

    # Campos do Customer
    customer_type = models.CharField(
        verbose_name='Tipo de Cliente',
        max_length=6,
        choices=CUSTOMER_TYPE_CHOICES,
        default='IND'
    )
    
    full_name = models.CharField(
        verbose_name='Nome Completo',
        max_length=100,
        blank=True,
        null=True
    )
    
    preferred_name = models.CharField(
        verbose_name='Como gostaria de ser chamado',
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
        unique=True
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
        """Limpa caracteres especiais antes de validar CPF/CNPJ"""
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
        """Aplica a validação antes de salvar"""
        with transaction.atomic():
            super().save(*args, **kwargs)  # Primeiro salva o cliente para garantir que tenha um ID

            # Se for Pessoa Jurídica, busca os dados na API
            if self.customer_type == "CORP" and self.tax_id:
                data = fetch_company_data(self.tax_id)
                if data:
                    self.full_name = data["full_name"]
                    self.preferred_name = data["preferred_name"]
                    super().save()  # Salva novamente com os dados da API

                    # Criando ou atualizando endereço corretamente usando GenericRelation
                    address = self.addresses.first() or Address(content_object=self)
                    address.zip_code = data["zip_code"]
                    address.street = data["street"]
                    address.number = data["number"]
                    address.neighborhood = data["neighborhood"]
                    address.city = data["city"]
                    address.state = data["state"]
                    address.save()

    @property
    def address(self):
        return self.addresses.first()

    @property
    def display_name(self):
        return self.preferred_name or self.full_name or f"Cliente {self.pk}"

    @property
    def formatted_phone(self):
        """Formata o número de telefone corretamente para fixo e celular"""
        if not self.phone:
            return ""

        phone = self.phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")  # Remove caracteres especiais

        if len(phone) == 10:  # Telefone fixo
            return f"({phone[:2]}) {phone[2:6]}-{phone[6:]}"
        elif len(phone) == 11:  # Celular
            return f"({phone[:2]}) {phone[2:7]}-{phone[7:]}"
        
        return phone

    def __str__(self):
        return f"{self.display_name} ({self.tax_id})"

    def formatted_tax_id(self):
        """Retorna o CPF ou CNPJ formatado apenas para exibição"""
        if not self.tax_id:
            return ""

        # Remove caracteres especiais antes de formatar
        tax_id = self.tax_id.replace('.', '').replace('-', '').replace('/', '').strip()

        # Verifica o tamanho original para formatar corretamente
        if len(tax_id) == 11:
            return f"{tax_id[:3]}.{tax_id[3:6]}.{tax_id[6:9]}-{tax_id[9:]}"  # CPF
        elif len(tax_id) == 14:
            return f"{tax_id[:2]}.{tax_id[2:5]}.{tax_id[5:8]}/{tax_id[8:12]}-{tax_id[12:]}"  # CNPJ

        return tax_id