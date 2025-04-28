from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.contrib.contenttypes.fields import GenericRelation
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

class Employee(AbstractUser):
    phone = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Formato: '+999999999'. Até 15 dígitos."
            )
        ],
        verbose_name='Telefone',
        blank=True,
        null=True
    )
    
    birth_date = models.DateField(
        verbose_name='Data de Nascimento',
        blank=True,
        null=True
    )
    
    hire_date = models.DateField(
        verbose_name='Data de Contratação',
        blank=True,
        null=True
    )
    
    position = models.CharField(
        max_length=50,
        verbose_name='Cargo',
        blank=True,
        null=True
    )
    
    # Relacionamento genérico com Address
    addresses = GenericRelation(
        'addresses.Address',
        related_query_name='employee',
        content_type_field='content_type',
        object_id_field='object_id'
    )

    class Meta:
        verbose_name = 'Funcionário'
        verbose_name_plural = 'Funcionários'
        ordering = ['last_name', 'first_name']
    
    @property
    def address(self):
        """Propriedade para compatibilidade com código existente."""
        return self.addresses.first()
    
    def save(self, *args, **kwargs):
        """Garante a validação completa antes de salvar."""
        with transaction.atomic():
            super().save(*args, **kwargs)
            
            # Processa o endereço se existir
            if address := self.address:
                self._complete_address_data(address)
    
    def _complete_address_data(self, address):
        """Preenche automaticamente os dados do endereço via API se necessário"""
        try:
            if address.zip_code and not all([
                address.street,
                address.neighborhood,
                address.city,
                address.state
            ]):
                address.full_clean()  # Dispara a busca na API
                address.save()
        except Exception as e:
            logger.error(f"Erro ao completar endereço: {str(e)}")