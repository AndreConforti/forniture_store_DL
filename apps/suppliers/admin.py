from django.contrib import admin
from django import forms
from .models import Supplier
from apps.addresses.models import Address
from django.contrib.contenttypes.admin import GenericStackedInline

class AddressInline(GenericStackedInline):
    model = Address
    extra = 1
    max_num = 1
    fields = (
        'zip_code', 'street', 'number', 'complement',
        'neighborhood', 'city', 'state'
    )
    verbose_name = "Endereço"
    verbose_name_plural = "Endereços"

class DocumentTypeFilter(admin.SimpleListFilter):
    title = 'Tipo de Documento'
    parameter_name = 'document_type'

    def lookups(self, request, model_admin):
        return Supplier.DOCUMENT_TYPE_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(document_type=self.value())
        return queryset

class SupplierAdminForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    form = SupplierAdminForm
    inlines = [AddressInline]
    list_display = (
        'trade_name', 'legal_name', 'document_type', 
        'formatted_document', 'is_active', 'phone'
    )
    list_filter = (DocumentTypeFilter, 'is_active', 'is_informal')
    search_fields = (
        'trade_name', 'legal_name', 'document', 
        'email', 'phone'
    )
    fieldsets = (
        ('Informações Básicas', {
            'fields': (
                'is_active', 'is_informal',
                ('document_type', 'document'),
                ('legal_name', 'trade_name'),
            )
        }),
        ('Contato', {
            'fields': (
                'email', 'phone',
            )
        }),
    )
    readonly_fields = ('registration_date',)
    actions = ['activate_suppliers', 'deactivate_suppliers']

    def formatted_document(self, obj):
        return obj.formatted_document
    formatted_document.short_description = 'Documento'

    def activate_suppliers(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} fornecedores ativados com sucesso.")
    activate_suppliers.short_description = "Ativar fornecedores selecionados"

    def deactivate_suppliers(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} fornecedores desativados com sucesso.")
    deactivate_suppliers.short_description = "Desativar fornecedores selecionados"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('addresses')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:  # Se for criação
            obj.create_address_from_cnpj()

    def save_formset(self, request, form, formset, change):
        """
        Garante que o endereço seja salvo com a referência correta ao Supplier
        """
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, Address):
                instance.content_object = form.instance
                instance.save()
        formset.save_m2m()
        super().save_formset(request, form, formset, change)