# Generated by Django 5.2 on 2025-05-10 21:20

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_remove_product_short_name_product_image_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='product',
            options={'ordering': ['description'], 'verbose_name': 'Produto', 'verbose_name_plural': 'Produtos'},
        ),
        migrations.RemoveConstraint(
            model_name='product',
            name='unique_product_name_per_category',
        ),
        migrations.RemoveIndex(
            model_name='product',
            name='product_name_idx',
        ),
        migrations.RemoveIndex(
            model_name='product',
            name='product_barcode_idx',
        ),
        migrations.RemoveField(
            model_name='product',
            name='barcode',
        ),
        migrations.RemoveField(
            model_name='product',
            name='discontinued_at',
        ),
        migrations.RemoveField(
            model_name='product',
            name='image',
        ),
        migrations.RemoveField(
            model_name='product',
            name='is_fragile',
        ),
        migrations.RemoveField(
            model_name='product',
            name='name',
        ),
        migrations.RemoveField(
            model_name='product',
            name='requires_serial_number',
        ),
        migrations.AddField(
            model_name='product',
            name='barcode_image',
            field=models.URLField(blank=True, help_text='URL da imagem do código de barras.', max_length=255, null=True, verbose_name='Imagem do Código de Barras'),
        ),
        migrations.AddField(
            model_name='product',
            name='full_description',
            field=models.CharField(blank=True, help_text='Descrição completa do produto do código NCM.', max_length=255, null=True, verbose_name='Descrição completa'),
        ),
        migrations.AddField(
            model_name='product',
            name='gtin',
            field=models.CharField(blank=True, help_text='GTIN (EAN/UPC) do produto (8 a 14 dígitos).', max_length=14, null=True, unique=True, validators=[django.core.validators.RegexValidator(message='O GTIN deve conter entre 8 e 14 dígitos numéricos.', regex='^\\d{8,14}$')], verbose_name='GTIN (Código de Barras)'),
        ),
        migrations.AddField(
            model_name='product',
            name='product_image',
            field=models.ImageField(blank=True, null=True, upload_to='products/images/%Y/%m/%d/', verbose_name='Imagem do Produto'),
        ),
        migrations.AlterField(
            model_name='product',
            name='description',
            field=models.CharField(help_text='Nome principal do produto.', max_length=100, verbose_name='Descrição/Nome'),
        ),
        migrations.AlterField(
            model_name='product',
            name='ncm',
            field=models.CharField(blank=True, help_text='Nomenclatura Comum do Mercosul.', max_length=8, null=True, verbose_name='Código NCM'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['description'], name='product_description_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['gtin'], name='product_gtin_idx'),
        ),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.UniqueConstraint(fields=('category', 'description', 'model', 'brand', 'color'), name='unique_product_combo_per_category', violation_error_message='Já existe um produto com esta combinação de descrição, modelo, marca e cor nesta categoria.'),
        ),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.UniqueConstraint(condition=models.Q(('gtin__isnull', False)), fields=('gtin',), name='unique_product_gtin', violation_error_message='Já existe um produto com este GTIN.'),
        ),
    ]
