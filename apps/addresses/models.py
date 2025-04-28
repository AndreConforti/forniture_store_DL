from functools import cached_property
from django.db import models
from django.core.validators import RegexValidator, MinLengthValidator
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import requests
import logging

logger = logging.getLogger(__name__)


class Address(models.Model):
    """
    Modelo para endereços brasileiros com autopreenchimento por CEP.
    Projetado para ser vinculado a outros modelos via OneToOneField.

    Atributos:
        street (str): Nome da rua/avenida (logradouro)
        number (str): Número do endereço ou 'SN' se não houver
        complement (str): Complemento do endereço
        neighborhood (str): Bairro
        city (str): Cidade
        state (str): Sigla do estado (UF)
        zip_code (str): CEP (8 dígitos sem formatação)

    Métodos Principais:
        clean(): Validações e autopreenchimento via CEP
        formatted_address(): Retorna o endereço formatado
        formatted_zip_code: Retorna o CEP formatado
    """

    BRAZILIAN_STATES = (
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 
        'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 
        'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
    )
    API_TIMEOUT = 2  # segundos
    CEP_CACHE_TIMEOUT = 86400  # 24 horas em segundos

    # Campos do endereço
    street = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Logradouro',
        help_text="Rua, Avenida, Travessa, etc."
    )
    number = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name='Número',
        help_text="Número ou 'SN' se não houver"
    )
    complement = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Complemento',
        help_text="Apartamento, Bloco, etc."
    )
    neighborhood = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Bairro'
    )
    city = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Cidade'
    )
    state = models.CharField(
        max_length=2,
        blank=True,
        verbose_name='UF',
        validators=[
            RegexValidator(
                regex='^[A-Z]{2}$',
                message="Use a sigla com 2 letras maiúsculas (ex: SP)"
            )
        ]
    )
    zip_code = models.CharField(
        max_length=8,
        verbose_name='CEP',
        validators=[
            MinLengthValidator(8),
            RegexValidator(r'^\d{8}$', "Use 8 dígitos sem hífen")
        ],
        help_text="8 dígitos sem hífen (ex: 12345678)"
    )
    # Relacionamento genérico
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = 'Endereço'
        verbose_name_plural = 'Endereços'
        indexes = [
            models.Index(fields=['state']),
            models.Index(fields=['city']),
            models.Index(fields=['zip_code']),
            models.Index(fields=['content_type', 'object_id']),
        ]
        ordering = ['state', 'city', 'street']

    def clean(self):
        """
        Executa validações e autopreenchimento
        """
        super().clean()
        self.zip_code = self._clean_zip_code(self.zip_code)
        self._validate_state()
        
        if not self._is_address_complete():
            self._fill_address_via_cep()
        
        self._normalize_text_fields()

    def _clean_zip_code(self, zip_code):
        """Remove formatação e valida o CEP."""
        clean_zip = ''.join(filter(str.isdigit, str(zip_code)))
        if len(clean_zip) != 8:
            raise ValidationError({'zip_code': 'CEP deve ter exatamente 8 dígitos'})
        return clean_zip

    def _validate_state(self):
        """Valida se a UF pertence à lista de estados brasileiros."""
        if self.state and self.state.upper() not in self.BRAZILIAN_STATES:
            raise ValidationError({
                'state': f'UF inválida. Use uma das: {", ".join(self.BRAZILIAN_STATES)}'
            })

    def _is_address_complete(self):
        """Verifica se os campos mínimos do endereço estão preenchidos."""
        return all([self.street, self.neighborhood, self.city, self.state])

    def _fill_address_via_cep(self):
        """Preenche automaticamente os campos via API de CEP."""
        if not self._cep_data:
            logger.warning(f'CEP {self.zip_code} não encontrado nas APIs')
            return
        self._update_address(self._cep_data)

    @cached_property
    def _cep_data(self):
        """Dados do CEP obtidos via cache ou API."""
        if not self.zip_code or len(self.zip_code) != 8:
            return None
            
        if data := cache.get(f'cep_{self.zip_code}'):
            return data
            
        if data := self._fetch_via_cep():
            cache.set(f'cep_{self.zip_code}', data, timeout=self.CEP_CACHE_TIMEOUT)
            return data
            
        if data := self._fetch_brasil_api():
            cache.set(f'cep_{self.zip_code}', data, timeout=self.CEP_CACHE_TIMEOUT)
            return data
            
        return None

    def _fetch_via_cep(self):
        """Consulta o serviço ViaCEP."""
        try:
            response = requests.get(
                f'https://viacep.com.br/ws/{self.zip_code}/json/',
                timeout=self.API_TIMEOUT
            )
            response.raise_for_status()
            if not (data := response.json()).get('erro'):
                return data
        except (requests.RequestException, ValueError) as e:
            logger.warning(f'Falha ao consultar ViaCEP: {str(e)}')
        return None

    def _fetch_brasil_api(self):
        """Consulta o serviço BrasilAPI como fallback."""
        try:
            response = requests.get(
                f'https://brasilapi.com.br/api/cep/v1/{self.zip_code}',
                timeout=self.API_TIMEOUT
            )
            response.raise_for_status()
            return {
                'logradouro': response.json().get('street'),
                'bairro': response.json().get('neighborhood'),
                'localidade': response.json().get('city'),
                'uf': response.json().get('state')
            }
        except (requests.RequestException, ValueError, KeyError) as e:
            logger.warning(f'Falha ao consultar BrasilAPI: {str(e)}')
            return None

    def _update_address(self, api_data):
        """Atualiza campos vazios com dados da API."""
        field_map = {
            'street': api_data.get('logradouro'),
            'neighborhood': api_data.get('bairro'),
            'city': api_data.get('localidade') or api_data.get('cidade'),
            'state': api_data.get('uf')
        }
        
        for field, value in field_map.items():
            if value and not getattr(self, field):
                setattr(self, field, value)

    def _normalize_text_fields(self):
        """Padroniza a formatação dos campos textuais."""
        for field in ['street', 'complement', 'neighborhood', 'city']:
            if value := getattr(self, field):
                setattr(self, field, ' '.join(value.strip().title().split()))

    @property
    def formatted_zip_code(self):
        """
        Retorna o CEP formatado para exibição (12345-678).

        Returns:
            str: CEP formatado ou string vazia se inválido
        """
        return f"{self.zip_code[:5]}-{self.zip_code[5:]}" if self.zip_code and len(self.zip_code) == 8 else ''

    def formatted_address(self):
        """
        Retorna o endereço completo formatado para exibição.

        Returns:
            str: Endereço formatado ou mensagem de incompleto
        """
        components = [
            f"{self.street}, {self.number}" if self.street else None,
            f"Complemento: {self.complement}" if self.complement else None,
            self.neighborhood,
            f"{self.city}-{self.state}" if self.city else None,
            f"CEP: {self.formatted_zip_code}" if self.zip_code else None
        ]
        return ', '.join(filter(None, components)) or "Endereço incompleto"

    def __str__(self):
        return self.formatted_address()

    def save(self, *args, **kwargs):
        """Garante a validação completa antes de salvar."""
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_complete(self):
        """Verifica se todos os campos obrigatórios estão preenchidos"""
        return all([
            self.zip_code,
            self.number,
            self.street,
            self.neighborhood,
            self.city,
            self.state
        ])