from django.db import models, transaction
from django.core.validators import RegexValidator, EmailValidator
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericRelation
from apps.addresses.models import Address
from validate_docbr import CNPJ, CPF
import logging
import requests
import pprint
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class Supplier(models.Model):
    """
    Modelo para cadastro de fornecedores (pessoa jurídica ou profissional autônomo).
    Realiza validação de documentos (CNPJ/CPF) e busca automática de dados na Receita Federal/BrasilAPI.
    """

    DOCUMENT_TYPE_CHOICES = [
        ('CNPJ', 'CNPJ (Pessoa Jurídica)'),
        ('CPF', 'CPF (Profissional)'),
        ('NI', 'Sem documento (Informal)'),
    ]

    CNPJ_API_ENDPOINTS = [
        {
            'name': 'BrasilAPI',
            'url': 'https://brasilapi.com.br/api/cnpj/v1/{cnpj}',
            'timeout': 3,
            'parser': lambda data: {
                'legal_name': data.get('razao_social', '').upper(),
                'trade_name': data.get('nome_fantasia', '').title(),
                'email': data.get('email', ''),
                'cep': data.get('cep', ''),
                'numero': data.get('numero', '')
            }
        },
        {
            'name': 'ReceitaWS',
            'url': 'https://receitaws.com.br/v1/cnpj/{cnpj}',
            'timeout': 4,
            'parser': lambda data: {
                'legal_name': data.get('nome', '').upper(),
                'trade_name': data.get('fantasia', '').title(),
                'email': data.get('email', ''),
                'cep': data.get('cep', ''),
                'numero': data.get('numero', '')
            }
        }
    ]

    # Relacionamento genérico com Address
    addresses = GenericRelation(
        Address,
        related_query_name='supplier',
        content_type_field='content_type',
        object_id_field='object_id'
    )

    # Campos do modelo
    document_type = models.CharField(
        verbose_name='Tipo de Documento',
        max_length=4,
        choices=DOCUMENT_TYPE_CHOICES,
        default='CNPJ'
    )
    document = models.CharField(
        verbose_name='CNPJ/CPF',
        max_length=14,
        blank=True,
        null=True,
        unique=True,
        validators=[RegexValidator(r'^\d{11,14}$', "CNPJ (14 dígitos) ou CPF (11 dígitos)")],
        help_text="Digite apenas números (14 dígitos para CNPJ, 11 para CPF)"
    )
    is_informal = models.BooleanField(
        verbose_name='Cadastro Informal',
        default=False,
        help_text="Marque para fornecedores sem documento formal"
    )
    legal_name = models.CharField(
        verbose_name='Razão Social',
        max_length=100,
        blank=True,
        null=True
    )
    trade_name = models.CharField(
        verbose_name='Nome Fantasia',
        max_length=80,
        blank=True
    )
    email = models.EmailField(
        verbose_name='E-mail',
        blank=True,
        null=True,
        validators=[EmailValidator()]
    )
    phone = models.CharField(
        verbose_name='Telefone',
        max_length=11,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^\d{10,11}$', "Use DDD + número (10 ou 11 dígitos)")]
    )
    registration_date = models.DateTimeField(
        'Data de Cadastro',
        auto_now_add=True
    )
    is_active = models.BooleanField(
        'Ativo',
        default=True
    )

    class Meta:
        verbose_name = 'Fornecedor'
        verbose_name_plural = 'Fornecedores'
        ordering = ['legal_name']
        indexes = [
            models.Index(fields=['document']),
            models.Index(fields=['legal_name']),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cnpj_validator = CNPJ()
        self._cpf_validator = CPF()

    def __str__(self) -> str:
        return f"{self.trade_name or self.legal_name or 'Fornecedor sem nome'} ({self.get_document_type_display()})"

    def clean(self):
        """Validações completas do modelo."""
        super().clean()
        self._validate_registration_config()
        
        if not self.is_informal:
            self._validate_document()
            if self.document_type == 'CNPJ':
                self._fetch_cnpj_data()
        
        self._validate_required_fields()

    def save(self, *args, **kwargs):
        """Salva o Supplier e cria endereço automaticamente se for CNPJ"""
        with transaction.atomic():
            is_new = self._state.adding
            super().save(*args, **kwargs)
            
            if is_new and self.document_type == 'CNPJ':
                self.create_address_from_cnpj()

    def _validate_registration_config(self):
        """Garante que cadastros informais não tenham documento."""
        if self.is_informal:
            self.document_type = 'NI'
            self.document = None
        elif not self.document:
            raise ValidationError({'document': 'Informe o CNPJ/CPF ou marque como cadastro informal'})

    def _validate_document(self):
        """Valida CNPJ/CPF com a biblioteca validate_docbr."""
        if self.document_type == 'CNPJ' and not self._cnpj_validator.validate(self.document):
            raise ValidationError({'document': 'CNPJ inválido'})
        elif self.document_type == 'CPF' and not self._cpf_validator.validate(self.document):
            raise ValidationError({'document': 'CPF inválido'})

    def _validate_required_fields(self):
        """Valida campos obrigatórios conforme tipo de documento."""
        errors = {}
        if self.document_type == 'CNPJ' and not self.legal_name:
            errors['legal_name'] = 'Razão social é obrigatória para CNPJ'
        elif self.document_type == 'CPF' and not self.trade_name:
            errors['trade_name'] = 'Nome fantasia é obrigatório para CPF'
        
        if errors:
            raise ValidationError(errors)

    def _fetch_cnpj_data(self):
        """Busca dados do CNPJ em APIs prioritárias."""
        if not self.document or len(self.document) != 14:
            return

        for api in self.CNPJ_API_ENDPOINTS:
            try:
                logger.debug(f"Consultando CNPJ {self.document} na API {api['name']}")
                response = requests.get(
                    api['url'].format(cnpj=self.document),
                    timeout=api['timeout']
                )
                data = response.json()
                
                if not data.get('erro'):
                    parsed_data = api['parser'](data)
                    logger.debug(f"Dados obtidos: {pprint.pformat(parsed_data)}")
                    self._update_supplier_data(parsed_data)
                    return
                    
            except (requests.RequestException, ValueError, KeyError) as e:
                logger.warning(f"Falha na API {api['name']}: {str(e)}")
                continue

        logger.error(f"Todas as APIs falharam para o CNPJ {self.document}")

    def _update_supplier_data(self, parsed_data: Dict):
        """Preenche campos vazios com dados da API."""
        if not self.legal_name:
            self.legal_name = parsed_data.get('legal_name', '')
        if not self.trade_name:
            self.trade_name = parsed_data.get('trade_name', '')
        if not self.email:
            self.email = parsed_data.get('email', '')

    def create_address_from_cnpj(self):
        """Cria endereço automaticamente a partir dos dados do CNPJ."""
        if not self.document or self.document_type != 'CNPJ' or self.addresses.exists():
            return None

        for api in self.CNPJ_API_ENDPOINTS:
            try:
                response = requests.get(
                    api['url'].format(cnpj=self.document),
                    timeout=api['timeout']
                )
                data = response.json()
                
                if not data.get('erro'):
                    address_data = {
                        'zip_code': data.get('cep', '').replace('-', '')[:8],
                        'street': data.get('logradouro', ''),
                        'number': data.get('numero', 'SN'),
                        'complement': data.get('complemento', ''),
                        'neighborhood': data.get('bairro', ''),
                        'city': data.get('municipio', ''),
                        'state': data.get('uf', '')
                    }
                    
                    if address_data['zip_code'] and address_data['street']:
                        address = Address(
                            content_object=self,
                            **{k: v for k, v in address_data.items() if v}
                        )
                        address.full_clean()
                        address.save()
                        logger.info(f"Endereço criado para CNPJ {self.document}")
                        return address
                        
            except (requests.RequestException, ValueError, KeyError, ValidationError) as e:
                logger.warning(f"Falha ao criar endereço: {str(e)}")
                continue
        return None

    @property
    def formatted_document(self) -> str:
        """Retorna o documento formatado para exibição."""
        if self.is_informal:
            return "Informal"
        elif self.document_type == 'CNPJ':
            return self._cnpj_validator.mask(self.document)
        elif self.document_type == 'CPF':
            return self._cpf_validator.mask(self.document)
        return ""

    @property
    def formatted_phone(self) -> str:
        """Formata o telefone para exibição: (00) 00000-0000."""
        if not self.phone:
            return ""
        phone = self.phone.zfill(11)
        return f"({phone[:2]}) {phone[2:7]}-{phone[7:]}"