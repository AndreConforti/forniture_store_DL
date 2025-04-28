from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from .models import Employee
from apps.addresses.models import Address
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Employee)
def handle_employee_address(sender, instance, created, **kwargs):
    """
    1. Cria/atualiza o endereço associado
    2. Completa dados via API quando necessário
    3. Mantém relação 1:1 mesmo com GenericRelation
    """
    if not hasattr(instance, 'addresses'):
        return

    try:
        with transaction.atomic():
            address = instance.addresses.first()
            
            # Se não tem address mas tem dados no form inline
            if not address and hasattr(instance, '_address_data'):
                address = Address(
                    content_type=ContentType.objects.get_for_model(instance),
                    object_id=instance.id,
                    **instance._address_data
                )
                address.full_clean()
                address.save()
            
            # Completa dados do address existente
            elif address and not address.is_complete:
                address.full_clean()  # Dispara autopreenchimento
                address.save()
                
    except Exception as e:
        logger.error(f"Erro ao processar endereço: {str(e)}")
        raise