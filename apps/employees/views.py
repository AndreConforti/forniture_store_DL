from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages


def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('home')  # Redireciona para a página inicial após login
        else:
            messages.error(request, 'Usuário ou senha incorretos!')
    
    return render(request, 'employees/custom_login.html')


def custom_logout(request):
    logout(request)
    return render(request, 'employees/custom_logout.html')