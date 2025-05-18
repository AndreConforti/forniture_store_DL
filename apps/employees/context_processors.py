from .models import Employee

def theme_processor(request):
    active_theme_class = Employee._meta.get_field('selected_theme').default
    theme_choices_for_navbar = Employee.THEME_CHOICES

    if request.user.is_authenticated and isinstance(request.user, Employee):
        if request.user.selected_theme:
            active_theme_class = request.user.selected_theme
            
    return {
        'active_theme_class': active_theme_class,
        'THEME_CHOICES_FOR_NAVBAR': theme_choices_for_navbar
    }