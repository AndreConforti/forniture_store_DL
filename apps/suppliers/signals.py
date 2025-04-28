from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Supplier
import logging

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Supplier)
def supplier_pre_save(sender, instance, **kwargs):
    """
    Validações e processamento antes de salvar o Supplier
    """
    try:
        instance.full_clean()
    except Exception as e:
        logger.error(f"Erro na validação pré-save do Supplier {instance}: {str(e)}")
        raise

@receiver(post_save, sender=Supplier)
def supplier_post_save(sender, instance, created, **kwargs):
    """
    Garante que o endereço seja completado após salvar o Supplier
    """
    if created and instance.addresses.exists():
        for address in instance.addresses.all():
            try:
                if address.zip_code and not address.is_complete:
                    address.full_clean()
                    address.save()
            except Exception as e:
                logger.error(f"Erro ao completar endereço: {str(e)}")