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
    BRAZILIAN_STATES_CHOICES = [
        ("AC", "Acre"),
        ("AL", "Alagoas"),
        ("AP", "Amapá"),
        ("AM", "Amazonas"),
        ("BA", "Bahia"),
        ("CE", "Ceará"),
        ("DF", "Distrito Federal"),
        ("ES", "Espírito Santo"),
        ("GO", "Goiás"),
        ("MA", "Maranhão"),
        ("MT", "Mato Grosso"),
        ("MS", "Mato Grosso do Sul"),
        ("MG", "Minas Gerais"),
        ("PA", "Pará"),
        ("PB", "Paraíba"),
        ("PR", "Paraná"),
        ("PE", "Pernambuco"),
        ("PI", "Piauí"),
        ("RJ", "Rio de Janeiro"),
        ("RN", "Rio Grande do Norte"),
        ("RS", "Rio Grande do Sul"),
        ("RO", "Rondônia"),
        ("RR", "Roraima"),
        ("SC", "Santa Catarina"),
        ("SP", "São Paulo"),
        ("SE", "Sergipe"),
        ("TO", "Tocantins"),
    ]
    API_TIMEOUT = 3
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
        choices=BRAZILIAN_STATES_CHOICES,  # Usar choices para validação e UI
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
        # Garante que um objeto só pode ter um endereço (opcional, dependendo da regra de negócio)
        # unique_together = ('content_type', 'object_id')

    def __str__(self):
        return self.formatted_address()

    def clean(self):
        super().clean()

        if self.zip_code:
            self.zip_code = self._clean_zip_code_format(self.zip_code)
            if not self._is_address_manually_filled():
                self._fill_address_from_cep_data()

        self._normalize_text_fields()
        # A validação de UF com RegexValidator e choices já é feita pelo Django.
        # _validate_state_custom desnecessário se choices forem usados.

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def _clean_zip_code_format(self, zip_code_value):
        if not zip_code_value:
            return None
        cleaned = "".join(filter(str.isdigit, str(zip_code_value)))
        if len(cleaned) == 8:
            return cleaned
        raise ValidationError(
            {"zip_code": "CEP inválido. Deve conter 8 dígitos numéricos."}
        )

    def _is_address_manually_filled(self):
        return all([self.street, self.neighborhood, self.city, self.state])

    def _fill_address_from_cep_data(self):
        cep_data = self.get_cep_data()
        if cep_data:
            self._update_address_fields(cep_data)
        elif (
            self.zip_code and not self._is_address_manually_filled()
        ):  # Se o CEP foi fornecido mas não encontrou dados
            # Não levanta erro aqui, permite salvar CEP mesmo que API não retorne.
            # A obrigatoriedade dos campos street, city etc pode ser definida por blank=False se necessário.
            logger.warning(
                f"Dados do CEP {self.zip_code} não encontrados ou API falhou, mas o CEP será salvo."
            )

    def get_cep_data(self):
        if not self.zip_code:
            return None

        cache_key = f"cep_data_{self.zip_code}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        data = self._fetch_via_cep() or self._fetch_brasil_api()

        if data:
            cache.set(cache_key, data, timeout=self.CEP_CACHE_TIMEOUT)
        return data

    def _fetch_via_cep(self):
        try:
            response = requests.get(
                f"https://viacep.com.br/ws/{self.zip_code}/json/",
                timeout=self.API_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("erro"):
                return {
                    "logradouro": data.get("logradouro"),
                    "bairro": data.get("bairro"),
                    "localidade": data.get("localidade"),
                    "uf": data.get("uf"),
                }
        except (requests.RequestException, ValueError) as e:
            logger.warning(f"ViaCEP falhou para {self.zip_code}: {e}")
        return None

    def _fetch_brasil_api(self):
        try:
            response = requests.get(
                f"https://brasilapi.com.br/api/cep/v1/{self.zip_code}",
                timeout=self.API_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            return {
                "logradouro": data.get("street"),
                "bairro": data.get("neighborhood"),
                "localidade": data.get("city"),
                "uf": data.get("state"),
            }
        except (requests.RequestException, ValueError, KeyError) as e:
            logger.warning(f"BrasilAPI falhou para {self.zip_code}: {e}")
        return None

    def _update_address_fields(self, api_data):
        field_map = {
            "street": api_data.get("logradouro"),
            "neighborhood": api_data.get("bairro"),
            "city": api_data.get("localidade")
            or api_data.get("cidade"),  # 'cidade' é redundante se 'localidade' é padrão
            "state": api_data.get("uf"),
        }
        for field, value in field_map.items():
            if value and not getattr(self, field):
                setattr(self, field, value.strip())

    def _normalize_text_fields(self):
        for field_name in ["street", "complement", "neighborhood", "city"]:
            value = getattr(self, field_name)
            if value:
                setattr(self, field_name, " ".join(value.strip().title().split()))
        if self.state:
            self.state = self.state.upper()

    @property
    def formatted_zip_code(self):
        return (
            f"{self.zip_code[:5]}-{self.zip_code[5:]}"
            if self.zip_code and len(self.zip_code) == 8
            else ""
        )

    def formatted_address(self):
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
