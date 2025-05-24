# reports/templatetags/reports_tags.py
from django import template
from django import forms # Importar forms aqui

register = template.Library()

@register.filter(name='is_radioselect')
def is_radioselect(field):
    """Checks if a form field is using the RadioSelect widget."""
    return isinstance(field.field.widget, forms.RadioSelect)

@register.filter(name='is_checkboxselectmultiple')
def is_checkboxselectmultiple(field):
    """Checks if a form field is using the CheckboxSelectMultiple widget."""
    return isinstance(field.field.widget, forms.CheckboxSelectMultiple)
