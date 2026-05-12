import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Ticker',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('symbol', models.CharField(db_index=True, max_length=15, verbose_name='Тикер')),
                ('added_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tickers', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Тикер',
                'verbose_name_plural': 'Тикеры',
                'ordering': ['-added_at'],
                'unique_together': {('user', 'symbol')},
            },
        ),
    ]
