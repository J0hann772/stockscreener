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
            name='Strategy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Название стратегии')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активна')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='strategies', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Стратегия',
                'verbose_name_plural': 'Стратегии',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='StrategyCondition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('indicator', models.CharField(max_length=50, verbose_name='Индикатор')),
                ('params', models.JSONField(blank=True, default=dict, verbose_name='Параметры индикатора')),
                ('operator', models.CharField(choices=[('>', 'Больше (>)'), ('<', 'Меньше (<)'), ('=', 'Равно (=)'), ('cross_up', 'Пересечение снизу вверх'), ('cross_down', 'Пересечение сверху вниз')], max_length=20, verbose_name='Оператор')),
                ('value', models.FloatField(blank=True, null=True, verbose_name='Значение для сравнения')),
                ('strategy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conditions', to='strategies.strategy', verbose_name='Стратегия')),
            ],
            options={
                'verbose_name': 'Условие стратегии',
                'verbose_name_plural': 'Условия стратегии',
            },
        ),
    ]
