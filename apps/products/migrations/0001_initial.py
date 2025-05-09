# Generated by Django 5.2 on 2025-05-04 01:54

import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('abbreviation', models.CharField(help_text='Abreviação de 3 letras maiúsculas (ex: DEC)', max_length=3, unique=True, validators=[django.core.validators.RegexValidator(message='A abreviação deve conter exatamente 3 letras maiúsculas (ex: DEC).', regex='^[A-Z]{3}$')], verbose_name='Abreviação')),
                ('name', models.CharField(help_text='Nome completo da categoria (deve ser único).', max_length=50, unique=True, verbose_name='Nome')),
                ('description', models.CharField(blank=True, help_text='Descrição detalhada da categoria (opcional).', max_length=255, verbose_name='Descrição')),
                ('is_active', models.BooleanField(default=True, help_text='Indica se a categoria está ativa no sistema.', verbose_name='Ativo')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
            ],
            options={
                'verbose_name': 'Categoria',
                'verbose_name_plural': 'Categorias',
                'ordering': ['name'],
                'indexes': [models.Index(fields=['name'], name='category_name_idx'), models.Index(fields=['abbreviation'], name='category_abbr_idx'), models.Index(fields=['is_active'], name='category_active_idx')],
            },
        ),
        migrations.CreateModel(
            name='Subcategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('abbreviation', models.CharField(help_text='Abreviação de 3 letras maiúsculas (ex: RET).', max_length=3, validators=[django.core.validators.RegexValidator(message='Use exatamente 3 letras maiúsculas (ex: RET).', regex='^[A-Z]{3}$')], verbose_name='Abreviação')),
                ('name', models.CharField(help_text='Nome completo da subcategoria (deve ser único na categoria).', max_length=50, verbose_name='Nome')),
                ('description', models.CharField(blank=True, help_text='Descrição detalhada da subcategoria (opcional).', max_length=255, verbose_name='Descrição')),
                ('is_active', models.BooleanField(default=True, help_text='Indica se a subcategoria está ativa no sistema.', verbose_name='Ativa')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='subcategories', to='products.category', verbose_name='Categoria Principal')),
            ],
            options={
                'verbose_name': 'Subcategoria',
                'verbose_name_plural': 'Subcategorias',
                'ordering': ['category__name', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Nome completo do produto para exibição.', max_length=100, verbose_name='Nome do Produto')),
                ('short_name', models.CharField(blank=True, help_text='Nome reduzido para etiquetas e sistemas com espaço limitado.', max_length=50, verbose_name='Nome Curto')),
                ('internal_code', models.CharField(blank=True, help_text='Código único para controle interno (gerado automaticamente se vazio).', max_length=20, null=True, unique=True, verbose_name='Código Interno')),
                ('barcode', models.CharField(blank=True, help_text='GTIN/EAN/UPC (opcional).', max_length=13, null=True, unique=True, validators=[django.core.validators.RegexValidator(message='O código de barras deve conter entre 8 e 13 dígitos.', regex='^\\d{8,13}$')], verbose_name='Código de Barras')),
                ('sku', models.CharField(blank=True, help_text='Stock Keeping Unit (identificador do fornecedor).', max_length=30, null=True, unique=True, verbose_name='SKU')),
                ('ncm', models.CharField(blank=True, help_text='Nomenclatura Comum do Mercosul (opcional).', max_length=8, null=True, verbose_name='NCM')),
                ('cost_price', models.DecimalField(decimal_places=2, help_text='Preço pago pelo produto (incluindo impostos e frete).', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))], verbose_name='Preço de Custo')),
                ('sale_price', models.DecimalField(decimal_places=2, help_text='Preço de venda ao consumidor final.', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))], verbose_name='Preço de Venda')),
                ('weight', models.DecimalField(blank=True, decimal_places=3, help_text='Peso do produto em quilogramas (opcional).', max_digits=8, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0.001'))], verbose_name='Peso (kg)')),
                ('length', models.DecimalField(blank=True, decimal_places=2, help_text='Comprimento do produto em centímetros (opcional).', max_digits=6, null=True, verbose_name='Comprimento (cm)')),
                ('width', models.DecimalField(blank=True, decimal_places=2, help_text='Largura do produto em centímetros (opcional).', max_digits=6, null=True, verbose_name='Largura (cm)')),
                ('height', models.DecimalField(blank=True, decimal_places=2, help_text='Altura do produto em centímetros (opcional).', max_digits=6, null=True, verbose_name='Altura (cm)')),
                ('description', models.TextField(blank=True, help_text='Descrição completa com características e detalhes do produto.', verbose_name='Descrição Detalhada')),
                ('materials', models.CharField(blank=True, help_text='Materiais principais que compõem o produto (opcional).', max_length=200, verbose_name='Materiais')),
                ('color', models.CharField(blank=True, help_text='Cor principal do produto (opcional).', max_length=50, verbose_name='Cor')),
                ('brand', models.CharField(blank=True, help_text='Marca/fabricante do produto (opcional).', max_length=50, verbose_name='Marca')),
                ('origin', models.CharField(blank=True, help_text='País de origem/fabricação (opcional).', max_length=30, verbose_name='Origem')),
                ('is_active', models.BooleanField(default=True, help_text='Indica se o produto está ativo para venda.', verbose_name='Ativo')),
                ('requires_serial_number', models.BooleanField(default=False, help_text='Produtos de alto valor que exigem registro de série.', verbose_name='Requer Número de Série')),
                ('is_fragile', models.BooleanField(default=False, help_text='Produto requer cuidados especiais no manuseio.', verbose_name='Frágil')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('discontinued_at', models.DateTimeField(blank=True, help_text='Data em que o produto foi descontinuado (opcional).', null=True, verbose_name='Descontinuado em')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='products', to='products.category', verbose_name='Categoria Principal')),
                ('subcategory', models.ForeignKey(blank=True, help_text='Subcategoria opcional para classificação mais detalhada.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='products', to='products.subcategory', verbose_name='Subcategoria')),
            ],
            options={
                'verbose_name': 'Produto',
                'verbose_name_plural': 'Produtos',
                'ordering': ['name'],
            },
        ),
        migrations.AddIndex(
            model_name='subcategory',
            index=models.Index(fields=['category', 'name'], name='subcategory_name_idx'),
        ),
        migrations.AddIndex(
            model_name='subcategory',
            index=models.Index(fields=['is_active'], name='subcategory_active_idx'),
        ),
        migrations.AddConstraint(
            model_name='subcategory',
            constraint=models.UniqueConstraint(fields=('category', 'abbreviation'), name='unique_subcat_abbreviation', violation_error_message='Já existe uma subcategoria com esta abreviação nesta categoria.'),
        ),
        migrations.AddConstraint(
            model_name='subcategory',
            constraint=models.UniqueConstraint(fields=('category', 'name'), name='unique_subcat_name', violation_error_message='Já existe uma subcategoria com este nome nesta categoria.'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['name'], name='product_name_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['internal_code'], name='product_internal_code_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['barcode'], name='product_barcode_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['category', 'subcategory'], name='product_category_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['is_active'], name='product_active_idx'),
        ),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.UniqueConstraint(fields=('category', 'name'), name='unique_product_name_per_category', violation_error_message='Já existe um produto com este nome nesta categoria.'),
        ),
    ]
