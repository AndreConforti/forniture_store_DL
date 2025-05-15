from functools import cached_property
from django.db import models
from django.core.validators import RegexValidator, MinLengthValidator
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from core.services import fetch_address_data # Importar o serviço centralizado
import logging

logger = logging.getLogger(__name__)


class Address(models.Model):
    """
    Modelo para armazenar informações de endereço.

    Este modelo utiliza um GenericForeignKey para se associar a qualquer outro
    modelo que necessite de um endereço (ex: Cliente, Fornecedor).
    Ele também inclui lógica para buscar dados de CEP de APIs públicas
    e cachear esses resultados.
    """
    BRAZILIAN_STATES_CHOICES = [
        ("AC", "Acre"), ("AL", "Alagoas"), ("AP", "Amapá"), ("AM", "Amazonas"),
        ("BA", "Bahia"), ("CE", "Ceará"), ("DF", "Distrito Federal"),
        ("ES", "Espírito Santo"), ("GO", "Goiás"), ("MA", "Maranhão"),
        ("MT", "Mato Grosso"), ("MS", "Mato Grosso do Sul"),
        ("MG", "Minas Gerais"), ("PA", "Pará"), ("PB", "Paraíba"),
        ("PR", "Paraná"), ("PE", "Pernambuco"), ("PI", "Piauí"),
        ("RJ", "Rio de Janeiro"), ("RN", "Rio Grande do Norte"),
        ("RS", "Rio Grande do Sul"), ("RO", "Rondônia"), ("RR", "Roraima"),
        ("SC", "Santa Catarina"), ("SP", "São Paulo"), ("SE", "Sergipe"),
        ("TO", "Tocantins"),
    ]
    CEP_CACHE_TIMEOUT = 86400  # 24 horas

    street = models.CharField(max_length=100, blank=True, verbose_name="Logradouro")
    number = models.CharField(
        max_length=10, blank=True, null=True, verbose_name="Número"
    )
    complement = models.CharField(max_length=50, blank=True, verbose_name="Complemento")
    neighborhood = models.CharField(max_length=50, blank=True, verbose_name="Bairro")
    city = models.CharField(max_length=50, blank=True, verbose_name="Cidade")
    state = models.CharField(
        max_length=2,
        blank=True,
        verbose_name="UF",
        choices=BRAZILIAN_STATES_CHOICES,
        validators=[
            RegexValidator(
                regex="^[A-Z]{2}$", message="UF deve ter 2 letras maiúsculas."
            )
        ],
    )
    zip_code = models.CharField(
        max_length=8,
        verbose_name="CEP",
        validators=[
            MinLengthValidator(8),
            RegexValidator(r"^\d{8}$", "CEP deve ter 8 dígitos numéricos."),
        ],
        blank=True,
        null=True,
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        verbose_name = "Endereço"
        verbose_name_plural = "Endereços"
        indexes = [
            models.Index(fields=["state"]),
            models.Index(fields=["city"]),
            models.Index(fields=["zip_code"]),
            models.Index(fields=["content_type", "object_id"]),
        ]
        ordering = ["state", "city", "street"]

    def __str__(self):
        return self.formatted_address()

    def clean(self):
        """
        Realiza validações e limpeza dos dados do endereço.

        Se um CEP for fornecido e os campos de endereço não estiverem
        preenchidos manualmente, tenta preenchê-los automaticamente
        usando dados de uma API de CEP. Normaliza campos de texto.
        """
        super().clean()

        if self.zip_code:
            self.zip_code = self._clean_zip_code_format(self.zip_code)
            if not self._is_address_manually_filled():
                self._fill_address_from_cep_data()

        self._normalize_text_fields()

    def save(self, *args, **kwargs):
        """
        Salva a instância do endereço após realizar uma limpeza completa dos dados.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def _clean_zip_code_format(self, zip_code_value):
        """Limpa o CEP, mantendo apenas dígitos, e valida seu formato."""
        if not zip_code_value:
            return None
        cleaned = "".join(filter(str.isdigit, str(zip_code_value)))
        if len(cleaned) == 8:
            return cleaned
        raise ValidationError(
            {"zip_code": "CEP inválido. Deve conter 8 dígitos numéricos."}
        )

    def _is_address_manually_filled(self):
        """Verifica se os principais campos de endereço foram preenchidos manualmente."""
        return all([self.street, self.neighborhood, self.city, self.state])

    def _fill_address_from_cep_data(self):
        """
        Preenche os campos de endereço (rua, bairro, cidade, UF)
        com base nos dados retornados pela consulta ao CEP,
        se esses campos já não estiverem preenchidos.
        """
        cep_data = self.get_cep_data() # Usa o serviço centralizado agora
        if cep_data:
            self._update_address_fields(cep_data)
        elif self.zip_code and not self._is_address_manually_filled():
            logger.warning(
                f"Dados do CEP {self.zip_code} não encontrados ou API falhou, mas o CEP será salvo."
            )

    def get_cep_data(self):
        """
        Obtém os dados do CEP, utilizando cache.
        Delega a busca para a função `fetch_address_data` do `core.services`.
        """
        if not self.zip_code:
            return None

        cache_key = f"cep_data_{self.zip_code}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        # Usa o serviço centralizado
        data = fetch_address_data(self.zip_code)

        if data:
            # O serviço já retorna no formato esperado:
            # {"zip_code", "street", "neighborhood", "city", "state"}
            # Precisamos mapear para "logradouro", "bairro", "localidade", "uf"
            # que _update_address_fields espera, ou ajustar _update_address_fields.
            # Vamos ajustar _update_address_fields para ser mais flexível ou usar o formato do serviço.
            # A função fetch_address_data já retorna um dicionário com chaves "street", "neighborhood", "city", "state".
            # O método _update_address_fields já está preparado para isso devido ao 'or'.
            cache.set(cache_key, data, timeout=self.CEP_CACHE_TIMEOUT)
        return data

    def _update_address_fields(self, api_data):
        """
        Atualiza os campos do modelo com os dados da API.
        Prioriza os dados já existentes no modelo se não estiverem vazios.
        """
        # O serviço `fetch_address_data` retorna:
        # "street", "neighborhood", "city", "state"
        # O método original esperava "logradouro", "bairro", "localidade", "uf" de ViaCEP/BrasilAPI.
        # Ajustamos para o formato do `fetch_address_data`
        field_map = {
            "street": api_data.get("street"),
            "neighborhood": api_data.get("neighborhood"),
            "city": api_data.get("city"),
            "state": api_data.get("state"),
        }
        for field, value in field_map.items():
            if value and not getattr(self, field): # Só preenche se o campo estiver vazio
                setattr(self, field, value.strip())

    def _normalize_text_fields(self):
        """Normaliza campos de texto para title case e remove espaços extras."""
        for field_name in ["street", "complement", "neighborhood", "city"]:
            value = getattr(self, field_name)
            if value:
                setattr(self, field_name, " ".join(value.strip().title().split()))
        if self.state:
            self.state = self.state.upper()

    @property
    def formatted_zip_code(self):
        """Retorna o CEP formatado (ex: '00000-000')."""
        return (
            f"{self.zip_code[:5]}-{self.zip_code[5:]}"
            if self.zip_code and len(self.zip_code) == 8
            else self.zip_code or ""
        )

    def formatted_address(self):
        """Retorna uma string representando o endereço completo formatado."""
        parts = [
            f"{self.street}, {self.number or 'S/N'}" if self.street else None,
            f"Compl: {self.complement}" if self.complement else None,
            self.neighborhood,
            f"{self.city}-{self.state}" if self.city and self.state else None,
            f"CEP: {self.formatted_zip_code}" if self.zip_code else None,
        ]
        return ", ".join(filter(None, parts)) or "Endereço não fornecido"

    @property
    def is_complete(self):
        """Verifica se os campos essenciais do endereço estão preenchidos."""
        return all(
            [
                self.zip_code,
                self.street,
                self.number,
                self.neighborhood,
                self.city,
                self.state,
            ]
        )