from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    age = models.IntegerField(null=True, blank=True, verbose_name='Возраст')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='Баланс')

    def __str__(self):
        return f"Профиль {self.user.username}"

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        # Для обновления пользователя (если профиль по какой-то причине отсутствует)
        Profile.objects.get_or_create(user=instance)
        instance.profile.save()