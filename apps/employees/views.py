from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from .forms import EmployeeLoginForm


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