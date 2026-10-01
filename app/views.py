from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages, auth
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import User  # Lấy model User tùy chỉnh từ models.py
from .models import Course
from .models import Chapter
from .models import Lesson
# Create your views here.
def detail_course (request):
    id = request.GET.get('id')
    if id:
        course = Course.objects.filter(id=id).first()
    else :
        return redirect('courses')
    context = {'course':course}
    return render(request,'app/detail_course.html',context)
def search (request):
    if request.method == "POST":
        searched = request.POST["searched"]
        keys = Course.objects.filter(title__contains = searched)
    context = {'searched':searched,
               'keys':keys,
               }
    return render (request , 'app/search.html',context)
def registerPage(request):
    if request.method == 'POST':
        fullname = request.POST.get('name', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # Lấy giá trị role từ form và tự động chuyển thành chữ hoa
        raw_role = request.POST.get('role', 'STUDENT').upper()
        if raw_role in ['INSTRUCTOR', 'STUDENT']:
            role = raw_role
        else:
            role = 'STUDENT'

        # 1. Kiểm tra Họ và tên không chứa chữ số
        if any(char.isdigit() for char in fullname):
            messages.error(request, 'Họ và tên không được chứa chữ số!')
            return render(request, 'app/register.html')

        if fullname:
            fullname = ' '.join(word.capitalize() for word in fullname.split())

        # 2. Bắt buộc Email phải đúng định dạng @gmail.com
        if not username.endswith('@gmail.com') or len(username) <= len('@gmail.com'):
            messages.error(request, 'Email đăng ký phải có định dạng đầy đủ là @gmail.com!')
            return render(request, 'app/register.html')

        # 3. Kiểm tra mật khẩu khớp nhau
        if password != confirm_password:
            messages.error(request, 'Mật khẩu nhập lại không khớp!')
            return render(request, 'app/register.html')

        # 4. Kiểm tra tồn tại
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Tên đăng nhập hoặc email này đã tồn tại!')
            return render(request, 'app/register.html')

        # 5. Tạo tài khoản trực tiếp bằng custom User Model
        user = User.objects.create_user(username=username, email=username, password=password)
        
        # Gán role và phân quyền hệ thống
        user.role = role
        if role == 'ADMIN':
            user.is_staff = True
            user.is_superuser = True
        else:
            user.is_staff = False
            user.is_superuser = False

        if fullname:
            user.first_name = fullname

        user.save()

        logout(request) 

        messages.success(request, 'Đăng ký tài khoản thành công! Vui lòng đăng nhập.')
        return redirect('login')

    return render(request, 'app/register.html')


def loginPage(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        login_input = request.POST.get('username', '').strip()
        password = request.POST.get('password')
        # 1. Hỗ trợ tìm tài khoản bằng cả Email hoặc Username
        user_obj = User.objects.filter(email__iexact=login_input).first()
        if not user_obj:
            user_obj = User.objects.filter(username__iexact=login_input).first()
        username_to_auth = user_obj.username if user_obj else login_input
        # 2. Xác thực tài khoản
        user = authenticate(request, username=username_to_auth, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Email/Tên đăng nhập hoặc mật khẩu không chính xác!')
            return render(request, 'app/login.html')
    return render(request, 'app/login.html')

def logoutPage(request):
    logout(request)
    return redirect('login')
def home(request):
    courses = Course.objects.all()
    context = {'courses': courses}
    return render(request, 'app/home.html', context)
def term(request):
    return render(request, 'app/term.html')

def courses(request):
    courses = Course.objects.all()
    context = {'courses' : courses}
    return render(request, 'app/courses.html',context)

def learning(request):
    return render(request, 'app/learning.html')

def checkout(request):
    return render(request, 'app/checkout.html')

def teacher(request):
    return render(request, 'app/teacher.html')