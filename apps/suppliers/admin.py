from django.contrib import admin
from django.utils.html import format_html
from .models import Supplier

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    # Configurações para tornar tudo readonly
    def has_add_permission(self, request):
        return False  # Desabilita a criação de novos registros

    def has_change_permission(self, request, obj=None):
        return False  # Desabilita edições

    # Exibição na lista de fornecedores
    list_display = (
        'full_name',
        'formatted_tax_id',
        'supplier_type_display',
        'contact_person',
        'formatted_phone',
        'email_link',
        'is_active_display',
        'address_display'
    )
    
    list_filter = ('supplier_type', 'is_active', 'registration_date')
    search_fields = ('full_name', 'preferred_name', 'tax_id', 'email', 'phone', 'contact_person')
    list_per_page = 20

    # Campos na página de detalhes
    readonly_fields = (
        'supplier_type_display',
        'full_name',
        'preferred_name',
        'formatted_tax_id',
        'state_registration',
        'municipal_registration',
        'phone',
        'formatted_phone',
        'email',
        'email_link',
        'contact_person',
        'bank_info_display',
        'pix_key_display',
        'is_active_display',
        'registration_date',
        'updated_at',
        'notes_display',
        'address_display'
    )

    fieldsets = (
        ('Informações Básicas', {
            'fields': (
                'supplier_type_display',
                'full_name',
                'preferred_name',
                'formatted_tax_id',
                'registration_date',
                'updated_at'
            )
        }),
        ('Dados Fiscais', {
            'fields': (
                'state_registration',
                'municipal_registration',
            ),
            'classes': ('collapse',)
        }),
        ('Contato', {
            'fields': (
                'contact_person',
                'phone',
                'formatted_phone',
                'email_link'
            )
        }),
        ('Dados Bancários', {
            'fields': (
                'bank_info_display',
                'pix_key_display',
            ),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': (
                'is_active_display',
            )
        }),
        ('Outras Informações', {
            'fields': (
                'notes_display',
                'address_display'
            )
        }),
    )

    # Métodos customizados para exibição
    def supplier_type_display(self, obj):
        return dict(Supplier.SUPPLIER_TYPE_CHOICES).get(obj.supplier_type, obj.supplier_type)
    supplier_type_display.short_description = 'Tipo de Fornecedor'

    def formatted_tax_id(self, obj):
        return obj.formatted_tax_id()
    formatted_tax_id.short_description = 'CPF/CNPJ'

    def formatted_phone(self, obj):
        return obj.formatted_phone
    formatted_phone.short_description = 'Telefone Formatado'

    def email_link(self, obj):
        if obj.email:
            return format_html('<a href="mailto:{}">{}</a>', obj.email, obj.email)
        return "-"
    email_link.short_description = 'E-mail'
    email_link.admin_order_field = 'email'

    def is_active_display(self, obj):
        return "✅ Ativo" if obj.is_active else "❌ Inativo"
    is_active_display.short_description = 'Status'

    def bank_info_display(self, obj):
        if obj.bank_name or obj.bank_agency or obj.bank_account:
            return format_html(
                """
                <div style="margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                    <strong>Dados Bancários:</strong><br>
                    Banco: {bank_name}<br>
                    Agência: {agency}<br>
                    Conta: {account}
                </div>
                """,
                bank_name=obj.bank_name or '--',
                agency=obj.bank_agency or '--',
                account=obj.bank_account or '--'
            )
        return "Nenhuma informação bancária cadastrada"
    bank_info_display.short_description = "Dados Bancários"

    def pix_key_display(self, obj):
        if obj.pix_key:
            return format_html(
                """
                <div style="margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                    <strong>Chave PIX:</strong><br>
                    {pix_key}
                </div>
                """,
                pix_key=obj.pix_key
            )
        return "Nenhuma chave PIX cadastrada"
    pix_key_display.short_description = "Chave PIX"

    def notes_display(self, obj):
        if obj.notes:
            return format_html(
                """
                <div style="margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px; white-space: pre-line;">
                    {notes}
                </div>
                """,
                notes=obj.notes
            )
        return "Nenhuma observação cadastrada"
    notes_display.short_description = "Observações"

    def address_display(self, obj):
        address = obj.addresses.first()  # Pega o primeiro endereço relacionado
        if address:
            return format_html(
                """
                <div style="margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                    <strong>Endereço:</strong><br>
                    {street}, {number}{complement}<br>
                    {neighborhood}<br>
                    {city}/{state}<br>
                    CEP: {zip_code}
                </div>
                """,
                street=address.street or '--',
                number=address.number or '--',
                complement=', ' + address.complement if address.complement else '',
                neighborhood=address.neighborhood or '--',
                city=address.city or '--',
                state=address.state or '--',
                zip_code=address.zip_code or '--'
            )
        return "Nenhum endereço cadastrado"
    address_display.short_description = "Endereço Completo"