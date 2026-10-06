from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages, auth
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import User  # Lấy model User tùy chỉnh từ models.py
from .models import Course
from .models import Chapter
from .models import Lesson
from .models import Enrollment
from .models import SaveCourse
# Create your views here.
def detail_course (request):
    course_id = request.GET.get('id')
    if course_id:
        course = Course.objects.filter(id=course_id).first()
    else :
        return redirect('courses')
    context = {'course':course}
    return render(request,'app/detail_course.html',context)
def search (request):
    if request.method == "POST":
        search_query = request.POST["searched"]
        matching_courses = Course.objects.filter(title__contains=search_query)
    context = {'search_query': search_query,
               'matching_courses': matching_courses,
               }
    return render (request , 'app/search.html',context)
def registerPage(request):
    if request.method == 'POST':
        full_name = request.POST.get('name', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password')
        password_confirmation = request.POST.get('confirm_password')
        
        # Lấy giá trị role từ form và tự động chuyển thành chữ hoa
        submitted_role = request.POST.get('role', 'STUDENT').upper()
        if submitted_role in ['INSTRUCTOR', 'STUDENT']:
            user_role = submitted_role
        else:
            user_role = 'STUDENT'

        # 1. Kiểm tra Họ và tên không chứa chữ số
        if any(character.isdigit() for character in full_name):
            messages.error(request, 'Họ và tên không được chứa chữ số!')
            return render(request, 'app/register.html')

        if full_name:
            full_name = ' '.join(word.capitalize() for word in full_name.split())

        # 2. Bắt buộc Email phải đúng định dạng @gmail.com
        if not username.endswith('@gmail.com') or len(username) <= len('@gmail.com'):
            messages.error(request, 'Email đăng ký phải có định dạng đầy đủ là @gmail.com!')
            return render(request, 'app/register.html')

        # 3. Kiểm tra mật khẩu khớp nhau
        if password != password_confirmation:
            messages.error(request, 'Mật khẩu nhập lại không khớp!')
            return render(request, 'app/register.html')

        # 4. Kiểm tra tồn tại
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Tên đăng nhập hoặc email này đã tồn tại!')
            return render(request, 'app/register.html')

        # 5. Tạo tài khoản trực tiếp bằng custom User Model
        user = User.objects.create_user(username=username, email=username, password=password)
        
        # Gán role và phân quyền hệ thống
        user.role = user_role
        if user_role == 'ADMIN':
            user.is_staff = True
            user.is_superuser = True
        else:
            user.is_staff = False
            user.is_superuser = False

        if full_name:
            user.first_name = full_name

        user.save()

        logout(request) 

        messages.success(request, 'Đăng ký tài khoản thành công! Vui lòng đăng nhập.')
        return redirect('login')

    return render(request, 'app/register.html')

def loginPage(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        login_identifier = request.POST.get('username', '').strip()
        password = request.POST.get('password')

        # Tìm tài khoản bằng Email hoặc Username
        matching_user = User.objects.filter(
            email__iexact=login_identifier
        ).first()

        if not matching_user:
            matching_user = User.objects.filter(
                username__iexact=login_identifier
            ).first()

        username_to_auth = (
            matching_user.username
            if matching_user
            else login_identifier
        )

        # Xác thực tài khoản
        user = authenticate(
            request,
            username=username_to_auth,
            password=password
        )

        if user is not None:
            login(request, user)

            # Phân loại người dùng
            if user.role == 'ADMIN':
                return redirect('admin_dashboard')

            elif user.role == 'INSTRUCTOR':
                return redirect('teacher_dashboard')

            elif user.role == 'STUDENT':
                return redirect('home')

            return redirect('home')

        else:
            messages.error(
                request,
                'Email/Tên đăng nhập hoặc mật khẩu không chính xác!'
            )
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

@login_required
def learning(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    enrollment = get_object_or_404(
        Enrollment,
        student=request.user,
        course=course,
        status='ACTIVE'
    )

    chapters = Chapter.objects.filter(
        course=course
    ).prefetch_related('lessons')

    lesson_id = request.GET.get('lesson')

    if lesson_id:
        lesson = get_object_or_404(
            Lesson,
            id=lesson_id,
            chapter__course=course
        )
    else:
        lesson = Lesson.objects.filter(
            chapter__course=course
        ).order_by(
            'chapter__order',
            'order'
        ).first()

    context = {
        'course': course,
        'chapters': chapters,
        'lesson': lesson,
    }

    return render(request, 'app/learning.html', context)

def teacher(request):
    courses = Course.objects.filter(
    enrollments__student=request.user,
    enrollments__status="ACTIVE"
)
    context = {'courses' : courses}
    return render(request, 'app/teacher.html',context)
@login_required
def profile (request):
    active_enrollments = Enrollment.objects.filter(
        student=request.user,
        status='ACTIVE'
    ).select_related('course')
    enrolled_courses = [enrollment.course for enrollment in active_enrollments]
    context = {
        'courses': enrolled_courses,
        'active_enrollments': active_enrollments,
    }
    return render(request,'app/profile.html',context)
@login_required
@require_POST
def enroll_course(request, course_id):
    course_to_enroll = get_object_or_404(Course, id=course_id)

    # Thêm: ghi nhận tài khoản đang đăng nhập tham gia khóa học.
    _enrollment_record, was_created = Enrollment.objects.get_or_create(
        student=request.user,
        course=course_to_enroll,
        defaults={"status": "ACTIVE", "progress": 0}
    )
    if was_created:
        messages.success(request, "Bạn đã đăng ký khóa học thành công.")
    else:
        messages.info(request, "Bạn đã đăng ký khóa học này rồi.")
    return redirect("profile")
def saved_courses (request):
    saved_course_records = SaveCourse.objects.filter(
        student=request.user
    ).select_related('course')
    active_enrollments = Enrollment.objects.filter(
        student=request.user,
        status='ACTIVE'
    )
    saved_courses = [
        saved_course_record.course
        for saved_course_record in saved_course_records
    ]
    context = {
        'active_enrollments': active_enrollments,
        'saved_courses': saved_courses,
    }
    return render (request,'app/saved_course.html',context)
@login_required
@require_POST
def saved_course (request,course_id):
    course_to_toggle = get_object_or_404(Course,id=course_id)
    # lay hoac tao ban moi ghi luu khoa hoc 
    saved_course_record, was_created = SaveCourse.objects.get_or_create(
        student = request.user,
        course = course_to_toggle
    )
    if was_created:
        messages.success(request,"Đã lưu khóa học vào danh sách yêu thích")
    else :
        saved_course_record.delete()
        messages.info(request,"Đã xóa khóa học khỏi danh sách đã lưu")
    return redirect('saved_courses')
def add_course(request):
    context = {}
    return render (request,'app/add_course.html')