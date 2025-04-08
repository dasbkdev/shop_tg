from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PaymentRequest, BotUser

@receiver(post_save, sender=PaymentRequest)
def update_user_balance(sender, instance, created, **kwargs):
    if not created and instance.status == 'approved':
        user = instance.user
        user.balance += instance.amount
        user.save()
