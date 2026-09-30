from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from .models import *
import json
# 1. Import model User chuẩn của Django
from django.contrib.auth.models import User 
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
import json
# Create your views here.
def home(request):
    # lay tat ca danh muc
    categories = Category.objects.all()
    courses = Course.objects.all()
    if request.user.is_authenticated :
        user = request.user 
    context = {
        'categories': categories,
        'courses': courses,
    }   
    return render(request, 'app/home.html',context)

def loginPage(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.info(request, 'Tên đăng nhập hoặc mật khẩu không hợp lệ!')
            
    context = {}
    return render(request, 'app/login.html', context)

def registerPage(request):
    # if request.user.is_authenticated:
    #     return redirect('home')

    if request.method == 'POST':
        fullname = request.POST.get('name', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # 2. Kiểm tra Họ và tên không được chứa chữ số
        if any(char.isdigit() for char in fullname):
            messages.error(request, 'Họ và tên không được chứa chữ số!')
            return render(request, 'app/register.html')

        # Tự động viết hoa chữ cái đầu của Họ và tên (VD: "nguyen van a" -> "Nguyen Van A")
        if fullname:
            fullname = ' '.join(word.capitalize() for word in fullname.split())

        # 3. Bắt buộc Username/Email phải kết thúc bằng @gmail.com
        if not username.endswith('@gmail.com'):
            messages.error(request, 'Tài khoản đăng ký phải là Email có đuôi @gmail.com!')
            return render(request, 'app/register.html')

        # 4. Kiểm tra mật khẩu nhập lại có khớp không
        if password != confirm_password:
            messages.error(request, 'Mật khẩu nhập lại không khớp!')
            return render(request, 'app/register.html')

        # 5. Kiểm tra xem Email/Username đã tồn tại trong Database chưa
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Tên đăng nhập hoặc email này đã tồn tại!')
            return render(request, 'app/register.html')

        # 6. Tạo tài khoản mới và lưu thông tin vào Database
        user = User.objects.create_user(username=username, email=username, password=password)
        if fullname:
            user.first_name = fullname  # Lưu họ tên vào profile người dùng
            user.save()

        messages.success(request, 'Đăng ký tài khoản thành công! Vui lòng đăng nhập.')
        return redirect('login')

    # Render giao diện register.html khi truy cập bằng phương thức GET
    return render(request, 'app/register.html')

# 2. THÊM HÀM LOGOUT NÀY ĐỂ BẠN CÓ THỂ ĐĂNG XUẤT VÀ VÀO LẠI TRANG REGISTER
def logoutPage(request):
    logout(request)
    return redirect('login')

def term(request):
    context = {}
    return render(request, 'app/term.html', context)

def courses(request):
    context = {}
    return render(request, 'app/courses.html', context)

def detail_courses(request):
    context = {}
    return render(request, 'app/detail_courses.html', context)

def learning(request):
    context = {}
    return render(request, 'app/learning.html', context)

def checkout(request):
    context = {}
    return render(request, 'app/checkout.html', context)

def teacher(request):
    context = {}
    return render(request, 'app/teacher.html', context)