from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages, auth
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import User  # Lấy model User tùy chỉnh từ models.py
# Create your views here.
def home(request):
    return render(request, 'app/home.html')

def registerPage(request):
    if request.method == 'POST':
        fullname = request.POST.get('name', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # Lấy giá trị role từ form và tự động chuyển thành chữ hoa
        raw_role = request.POST.get('role', 'STUDENT').upper()
        if raw_role in ['ADMIN', 'INSTRUCTOR', 'STUDENT']:
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

        # 6. THÊM ĐOẠN NÀY ĐỂ ĐẢM BẢO CHẮC CHẮN KHÔNG BỊ GIỮ PHIÊN ĐĂNG NHẬP NGẦM
        logout(request) 

        messages.success(request, 'Đăng ký tài khoản thành công! Vui lòng đăng nhập.')
        return redirect('login')

    return render(request, 'app/register.html')


def loginPage(request):
    # Nếu người dùng đã đăng nhập rồi, tự động phân quyền điều hướng luôn
    if request.user.is_authenticated:
        if request.user.role == 'ADMIN' or request.user.is_superuser or request.user.is_staff:
            return redirect('/admin/')
        elif request.user.role == 'INSTRUCTOR':
            # Bạn có thể đổi hướng về trang quản lý của giảng viên nếu có, ví dụ: redirect('instructor_dashboard')
            return redirect('home')
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Xác thực tài khoản với custom User model
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            
            # Phân quyền chuyển hướng thông minh dựa vào trường role trong model
            if user.role == 'ADMIN' or user.is_superuser or user.is_staff:
                return redirect('/admin/')  # Quản trị viên vào trang admin
            elif user.role == 'INSTRUCTOR':
                return redirect('home')     # Giảng viên (có thể tùy chỉnh trang riêng sau)
            else:
                return redirect('home')     # Học sinh (STUDENT) về trang chủ
        else:
            messages.error(request, 'Email hoặc mật khẩu không chính xác!')
            return render(request, 'app/login.html')

    return render(request, 'app/login.html')

def logoutPage(request):
    logout(request)
    return redirect('login')

def term(request):
    return render(request, 'app/term.html')

def courses(request):
    return render(request, 'app/courses.html')

def detail_courses(request):
    return render(request, 'app/detail_courses.html')

def learning(request):
    return render(request, 'app/learning.html')

def checkout(request):
    return render(request, 'app/checkout.html')

def teacher(request):
    return render(request, 'app/teacher.html')