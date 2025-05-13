from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required


@require_http_methods(["GET", "POST"])
def custom_login(request):
    if request.user.is_authenticated:
        return redirect('showroom:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('showroom:dashboard')
        else:
            messages.error(request, 'Usuário ou senha incorretos!')
            return redirect('employees:login')
    
    return render(request, 'employees/custom_login.html')


@require_POST
@login_required
def custom_logout(request):
    logout(request)
    return redirect('employees:login')