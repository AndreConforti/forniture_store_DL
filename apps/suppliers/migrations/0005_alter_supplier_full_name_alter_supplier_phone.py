# Generated by Django 5.2 on 2025-05-22 23:34

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('suppliers', '0004_alter_supplier_full_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='supplier',
            name='full_name',
            field=models.CharField(help_text='Nome completo (PF) ou Razão Social (PJ)', max_length=100, verbose_name='Razão Social / Nome Completo'),
        ),
        migrations.AlterField(
            model_name='supplier',
            name='phone',
            field=models.CharField(blank=True, max_length=11, null=True, validators=[django.core.validators.RegexValidator('^\\d{10,11}$', 'Telefone deve ter 10 ou 11 dígitos.')], verbose_name='Telefone'),
        ),
    ]
