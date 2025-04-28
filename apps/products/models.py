from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from decimal import Decimal
from django.db import transaction


class Category(models.Model):
    """
    Modelo para categorias principais de produtos.
    
    Atributos:
        abbreviation (str): Abreviação única de 3 letras maiúsculas (ex: DEC)
        name (str): Nome completo da categoria (único no sistema)
        description (str): Descrição detalhada (opcional)
        is_active (bool): Status de ativação da categoria
        created_at (datetime): Data de criação (automática)
        updated_at (datetime): Data de atualização (automática)
    """
    abbreviation = models.CharField(
        verbose_name='Abreviação',
        max_length=3,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z]{3}$',
                message='A abreviação deve conter exatamente 3 letras maiúsculas (ex: DEC).',
            )
        ],
        help_text='Abreviação de 3 letras maiúsculas (ex: DEC)'
    )
    name = models.CharField(
        verbose_name='Nome',
        max_length=50,
        unique=True,
        help_text='Nome completo da categoria (deve ser único).'
    )
    description = models.CharField(
        verbose_name='Descrição',
        max_length=255,
        blank=True,
        help_text='Descrição detalhada da categoria (opcional).'
    )
    is_active = models.BooleanField(
        verbose_name='Ativo',
        default=True,
        help_text='Indica se a categoria está ativa no sistema.'
    )
    created_at = models.DateTimeField(
        verbose_name='Criado em',
        auto_now_add=True,
        editable=False
    )
    updated_at = models.DateTimeField(
        verbose_name='Atualizado em',
        auto_now=True
    )

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name'], name='category_name_idx'),
            models.Index(fields=['abbreviation'], name='category_abbr_idx'),
            models.Index(fields=['is_active'], name='category_active_idx'),
        ]

    def __str__(self):
        """Representação legível da categoria."""
        return f'{self.abbreviation} - {self.name}'
    
    def clean(self):
        """
        Validações adicionais:
        1. Garante que a abreviação esteja em maiúsculas
        2. Verifica unicidade do nome (case-insensitive)
        """
        super().clean()
        self.abbreviation = self.abbreviation.upper()
        
        if Category.objects.filter(name__iexact=self.name).exclude(pk=self.pk).exists():
            raise ValidationError(
                {'name': 'Já existe uma categoria com este nome (considerando maiúsculas/minúsculas).'}
            )

    def save(self, *args, **kwargs):
        """Garante que o clean() seja sempre executado antes do save."""
        self.full_clean()
        super().save(*args, **kwargs)


class Subcategory(models.Model):
    """
    Modelo para subcategorias vinculadas a categorias principais.
    
    Atributos:
        category (ForeignKey): Categoria principal relacionada
        abbreviation (str): Abreviação de 3 letras única na categoria
        name (str): Nome único dentro da categoria principal
        description (str): Descrição detalhada (opcional)
        is_active (bool): Status de ativação
        created_at (datetime): Data de criação (automática)
        updated_at (datetime): Data de atualização (automática)
    """
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='subcategories',
        verbose_name='Categoria Principal'
    )
    abbreviation = models.CharField(
        verbose_name='Abreviação',
        max_length=3,
        help_text='Abreviação de 3 letras maiúsculas (ex: RET).',
        validators=[
            RegexValidator(
                regex=r'^[A-Z]{3}$',
                message='Use exatamente 3 letras maiúsculas (ex: RET).'
            )
        ]
    )
    name = models.CharField(
        verbose_name='Nome',
        max_length=50,
        help_text='Nome completo da subcategoria (deve ser único na categoria).'
    )
    description = models.CharField(
        verbose_name='Descrição',
        max_length=255,
        blank=True,
        help_text='Descrição detalhada da subcategoria (opcional).'
    )
    is_active = models.BooleanField(
        verbose_name='Ativa',
        default=True,
        help_text='Indica se a subcategoria está ativa no sistema.'
    )
    created_at = models.DateTimeField(
        verbose_name='Criado em',
        auto_now_add=True,
        editable=False
    )
    updated_at = models.DateTimeField(
        verbose_name='Atualizado em',
        auto_now=True
    )

    class Meta:
        verbose_name = 'Subcategoria'
        verbose_name_plural = 'Subcategorias'
        ordering = ['category__name', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['category', 'abbreviation'],
                name='unique_subcat_abbreviation',
                violation_error_message='Já existe uma subcategoria com esta abreviação nesta categoria.'
            ),
            models.UniqueConstraint(
                fields=['category', 'name'],
                name='unique_subcat_name',
                violation_error_message='Já existe uma subcategoria com este nome nesta categoria.'
            )
        ]
        indexes = [
            models.Index(fields=['category', 'name'], name='subcategory_name_idx'),
            models.Index(fields=['is_active'], name='subcategory_active_idx'),
        ]

    def __str__(self):
        """Representação no formato 'CAT.SUB - Nome'."""
        return f"{self.category.abbreviation}.{self.abbreviation} - {self.name}"
    
    def clean(self):
        """
        Validações:
        1. Abreviação em maiúsculas
        2. Nome diferente da categoria pai
        3. Abreviação diferente da categoria pai
        4. Nome único na categoria (case-insensitive)
        """
        super().clean()
        self.abbreviation = self.abbreviation.upper()
        
        if self.name.lower() == self.category.name.lower():
            raise ValidationError(
                {'name': 'O nome da subcategoria não pode ser igual ao nome da categoria principal.'}
            )
        
        if self.abbreviation == self.category.abbreviation:
            raise ValidationError(
                {'abbreviation': 'A abreviação da subcategoria não pode ser igual à da categoria principal.'}
            )
        
        if Subcategory.objects.filter(
            category=self.category,
            name__iexact=self.name
        ).exclude(pk=self.pk).exists():
            raise ValidationError(
                {'name': 'Já existe uma subcategoria com nome similar nesta categoria.'}
            )

    def save(self, *args, **kwargs):
        """Garante validação completa antes de salvar."""
        self.full_clean()
        super().save(*args, **kwargs)


class Product(models.Model):
    """
    Modelo para produtos de decoração e móveis.
    
    Atributos obrigatórios:
        category (ForeignKey): Categoria principal
        name (str): Nome do produto
        cost_price (Decimal): Preço de custo
        sale_price (Decimal): Preço de venda
        
    Atributos opcionais:
        subcategory (ForeignKey): Subclassificação
        barcode (str): Código de barras (EAN/UPC)
        dimensions: Comprimento, largura, altura
    """
    # Relacionamentos
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='Categoria Principal'
    )
    subcategory = models.ForeignKey(
        Subcategory,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='Subcategoria',
        blank=True,
        null=True,
        help_text='Subcategoria opcional para classificação mais detalhada.'
    )
    
    # Identificação básica
    name = models.CharField(
        verbose_name='Nome do Produto',
        max_length=100,
        help_text='Nome completo do produto para exibição.'
    )
    short_name = models.CharField(
        verbose_name='Nome Curto',
        max_length=50,
        blank=True,
        help_text='Nome reduzido para etiquetas e sistemas com espaço limitado.'
    )
    
    # Códigos e identificadores
    internal_code = models.CharField(
        verbose_name='Código Interno',
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        help_text='Código único para controle interno (gerado automaticamente se vazio).'
    )
    barcode = models.CharField(
        verbose_name='Código de Barras',
        max_length=13,
        blank=True,
        null=True,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{8,13}$',
                message='O código de barras deve conter entre 8 e 13 dígitos.'
            )
        ],
        help_text='GTIN/EAN/UPC (opcional).'
    )
    sku = models.CharField(
        verbose_name='SKU',
        max_length=30,
        blank=True,
        null=True,
        unique=True,
        help_text='Stock Keeping Unit (identificador do fornecedor).'
    )
    ncm = models.CharField(
        verbose_name='NCM',
        max_length=8,
        blank=True,
        null=True,
        help_text='Nomenclatura Comum do Mercosul (opcional).'
    )
    
    # Informações de preço
    cost_price = models.DecimalField(
        verbose_name='Preço de Custo',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Preço pago pelo produto (incluindo impostos e frete).'
    )
    sale_price = models.DecimalField(
        verbose_name='Preço de Venda',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Preço de venda ao consumidor final.'
    )
    
    # Dimensões e peso
    weight = models.DecimalField(
        verbose_name='Peso (kg)',
        max_digits=8,
        decimal_places=3,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text='Peso do produto em quilogramas (opcional).'
    )
    length = models.DecimalField(
        verbose_name='Comprimento (cm)',
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Comprimento do produto em centímetros (opcional).'
    )
    width = models.DecimalField(
        verbose_name='Largura (cm)',
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Largura do produto em centímetros (opcional).'
    )
    height = models.DecimalField(
        verbose_name='Altura (cm)',
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Altura do produto em centímetros (opcional).'
    )
    
    # Informações adicionais
    description = models.TextField(
        verbose_name='Descrição Detalhada',
        blank=True,
        help_text='Descrição completa com características e detalhes do produto.'
    )
    materials = models.CharField(
        verbose_name='Materiais',
        max_length=200,
        blank=True,
        help_text='Materiais principais que compõem o produto (opcional).'
    )
    color = models.CharField(
        verbose_name='Cor',
        max_length=50,
        blank=True,
        help_text='Cor principal do produto (opcional).'
    )
    brand = models.CharField(
        verbose_name='Marca',
        max_length=50,
        blank=True,
        help_text='Marca/fabricante do produto (opcional).'
    )
    origin = models.CharField(
        verbose_name='Origem',
        max_length=30,
        blank=True,
        help_text='País de origem/fabricação (opcional).'
    )
    
    # Status e controle
    is_active = models.BooleanField(
        verbose_name='Ativo',
        default=True,
        help_text='Indica se o produto está ativo para venda.'
    )
    requires_serial_number = models.BooleanField(
        verbose_name='Requer Número de Série',
        default=False,
        help_text='Produtos de alto valor que exigem registro de série.'
    )
    is_fragile = models.BooleanField(
        verbose_name='Frágil',
        default=False,
        help_text='Produto requer cuidados especiais no manuseio.'
    )
    
    # Datas
    created_at = models.DateTimeField(
        verbose_name='Criado em',
        auto_now_add=True,
        editable=False
    )
    updated_at = models.DateTimeField(
        verbose_name='Atualizado em',
        auto_now=True
    )
    discontinued_at = models.DateTimeField(
        verbose_name='Descontinuado em',
        blank=True,
        null=True,
        help_text='Data em que o produto foi descontinuado (opcional).'
    )

    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        app_label = 'products'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name'], name='product_name_idx'),
            models.Index(fields=['internal_code'], name='product_internal_code_idx'),
            models.Index(fields=['barcode'], name='product_barcode_idx'),
            models.Index(fields=['category', 'subcategory'], name='product_category_idx'),
            models.Index(fields=['is_active'], name='product_active_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['category', 'name'],
                name='unique_product_name_per_category',
                violation_error_message='Já existe um produto com este nome nesta categoria.'
            )
        ]

    def __str__(self):
        """Representação no formato 'CÓDIGO - Nome' ou apenas 'Nome'."""
        if self.internal_code:
            return f"{self.internal_code} - {self.name}"
        return self.name

    def clean(self):
        """
        Validações:
        1. Subcategoria pertence à categoria
        2. Produto descontinuado não pode estar ativo
        3. Geração segura de internal_code
        """
        super().clean()
        
        # Valida relacionamento categoria-subcategoria
        if self.subcategory and self.subcategory.category != self.category:
            raise ValidationError(
                {'subcategory': 'A subcategoria selecionada não pertence à categoria principal.'}
            )
        
        # Valida status vs data de descontinuação
        if self.discontinued_at and self.is_active:
            raise ValidationError(
                {'is_active': 'Produto descontinuado não pode estar ativo.'}
            )
        
        # Geração thread-safe do código interno
        if not self.internal_code:
            self._generate_internal_code()

    def _generate_internal_code(self):
        """Gera um código interno único no formato CCC[SSS]NNNN."""
        with transaction.atomic():
            prefix = self.category.abbreviation
            if self.subcategory:
                prefix += self.subcategory.abbreviation
            
            last_code = (
                Product.objects.filter(internal_code__startswith=prefix)
                .order_by('internal_code')
                .values_list('internal_code', flat=True)
                .last()
            )
            
            last_num = int(last_code[len(prefix):]) if last_code else 0
            self.internal_code = f"{prefix}{last_num + 1:04d}"

    def save(self, *args, **kwargs):
        """Garante validação completa antes de salvar."""
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def profit_margin(self):
        """
        Calcula a margem de lucro percentual.
        
        Returns:
            float: Margem de lucro em porcentagem (0 se custo for zero)
        """
        if self.cost_price == 0:
            return 0
        return ((self.sale_price - self.cost_price) / self.cost_price) * 100

    @property
    def dimensions(self):
        """
        Retorna as dimensões formatadas se disponíveis.
        
        Returns:
            str: String formatada "L × W × H cm" ou mensagem de indisponibilidade
        """
        if all([self.length, self.width, self.height]):
            return f"{self.length} × {self.width} × {self.height} cm"
        return "Dimensões não disponíveis"