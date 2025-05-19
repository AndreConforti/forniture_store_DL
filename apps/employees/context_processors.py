# employees/context_processors.py
from .models import Employee

# Mapeamento manual das cores de preview baseadas nas suas variáveis CSS
# (valor_tema: (nome_exibicao_do_modelo, cor_fundo_hex, cor_borda_hex))
# Usaremos primary-medium para o fundo e secondary-light para a borda como referência.
THEME_PREVIEW_COLORS = {
    'theme-blue-gray': ('#185A9D', '#DCDCDC'),  # primary-medium, secondary-light
    'theme-green-gray': ('#115b14', '#a3a3a3'), # primary-medium, secondary-light
    'theme-brown-sand': ('#653C1B', '#F2E8DA'), # primary-medium, secondary-light
    'theme-purple-gray': ('#5A308D', '#DCDCDC'), # primary-medium, secondary-light
}

def theme_processor(request):
    active_theme_class = Employee._meta.get_field('selected_theme').default
    
    if request.user.is_authenticated and hasattr(request.user, 'selected_theme'):
        if request.user.selected_theme:
            active_theme_class = request.user.selected_theme
            
    # Preparar THEME_CHOICES_FOR_NAVBAR com detalhes de preview
    theme_choices_for_navbar_list = []
    employee_theme_choices = dict(Employee.THEME_CHOICES) # Para fácil lookup do nome

    for theme_value, display_name in Employee.THEME_CHOICES:
        bg_color, border_color = THEME_PREVIEW_COLORS.get(theme_value, ('#cccccc', '#999999')) # Fallback colors
        theme_choices_for_navbar_list.append({
            'value': theme_value,
            'name': display_name, # Nome já vem de Employee.THEME_CHOICES
            'bg_color': bg_color,
            'border_color': border_color,
        })
            
    return {
        'active_theme_class': active_theme_class,
        'THEME_CHOICES_FOR_NAVBAR': theme_choices_for_navbar_list
    }