from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from .models import *
import json
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate,login,logout
from django.contrib import messages
# Create your views here.
def home(request):
    return render(request,'app/home.html')
def loginPage(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request,username = username , password = password)
        if user is not None:
            login(request,user)
            return redirect('home')
        else :
            messages.info(request,'Tên đăng nhập hoặc mật khẩu không hợp lệ!')
    context = {}
    return render(request,'app/login.html',context)
def registerPage(request) :
    context = {}
    return render(request,'app/register.html',context)
def term(request):
    context = {}
    return render(request,'app/term.html',context)