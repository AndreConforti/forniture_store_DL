from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from .forms import EmployeeLoginForm
from .models import Employee


@require_http_methods(["GET", "POST"])
def custom_login(request):
    if request.user.is_authenticated:
        return redirect('showroom:dashboard')
    
    if request.method == 'POST':
        form = EmployeeLoginForm(request, data=request.POST) # Use o form
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('showroom:dashboard')
        else:
            # Se o formulário não for válido, os erros estarão em form.errors
            # Você pode passar o form para o template para exibir os erros
            # messages.error(request, 'Usuário ou senha incorretos!') # Ou use os erros do form
            pass # O form será renderizado novamente com erros
    else:
        form = EmployeeLoginForm() # Form vazio para GET
    
    return render(request, 'employees/custom_login.html', {'form': form})


@require_POST # Garante que o logout só pode ser feito via POST
@login_required # Garante que apenas usuários logados podem tentar deslogar
def custom_logout(request):
    auth_logout(request)
    return render(request, 'employees/custom_logout.html')


@login_required
@require_POST
def change_employee_theme(request):
    theme_value = request.POST.get('selected_theme_value')    
    # Valida se o tema escolhido está entre as opções válidas
    valid_theme_values = [choice[0] for choice in Employee.THEME_CHOICES]
    if theme_value in valid_theme_values:
        employee = request.user
        if isinstance(employee, Employee): 
            employee.selected_theme = theme_value
            employee.save(update_fields=['selected_theme'])
        else:
            messages.error(request, "Não foi possível atualizar o tema para este usuário.")
    else:
        messages.error(request, "Tema inválido selecionado.")
        
    return redirect(request.META.get('HTTP_REFERER', 'showroom:dashboard'))