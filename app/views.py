from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils import timezone
import math
from .models import User, Course, Enrollment
from django.db.models import Count, Q
from django.utils.text import slugify
from functools import wraps
from .services import (
    complete_lesson_progress,
    get_streak_status,
    get_next_lesson,
    get_course_lessons,
    is_lesson_unlocked,
    record_learning_activity,
    record_learning_time,
    update_course_progress,
    update_streak,
)
from .models import (
    User,
    Course,
    Chapter,
    Lesson,
    Enrollment,
    SaveCourse,
    LessonProgress,
)
# trang admin 
@login_required
def admin_dashboard(request):

    # Chỉ ADMIN mới được vào
    if request.user.role != 'ADMIN':
        messages.error(
            request,
            'Bạn không có quyền truy cập trang quản trị.'
        )
        return redirect('home')

    # Thống kê người dùng
    total_students = User.objects.filter(
        role=User.Role.STUDENT
    ).count()

    total_instructors = User.objects.filter(
        role=User.Role.INSTRUCTOR
    ).count()

    # Tổng khóa học
    total_courses = Course.objects.count()

    # Tổng lượt đăng ký khóa học
    total_enrollments = Enrollment.objects.count()

    # Khóa học mới nhất
    recent_courses = Course.objects.order_by('-id')[:5]

    # Giảng viên
    instructors = User.objects.filter(
        role=User.Role.INSTRUCTOR
    ).order_by('-id')[:5]

    context = {
        'total_students': total_students,
        'total_instructors': total_instructors,
        'total_courses': total_courses,
        'total_enrollments': total_enrollments,
        'recent_courses': recent_courses,
        'instructors': instructors,
    }

    return render(
        request,
        'app/admin_dashboard.html',
        context
    )
@login_required
def create_instructor(request):

    # Chỉ ADMIN mới được tạo giảng viên
    if request.user.role != 'ADMIN':
        messages.error(
            request,
            'Bạn không có quyền thực hiện chức năng này.'
        )
        return redirect('home')

    if request.method == 'POST':

        full_name = request.POST.get('full_name', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Kiểm tra dữ liệu
        if not full_name:
            messages.error(request, 'Vui lòng nhập họ tên.')
            return render(
                request,
                'app/create_instructor.html'
            )

        if not username:
            messages.error(request, 'Vui lòng nhập email/tên đăng nhập.')
            return render(
                request,
                'app/create_instructor.html'
            )

        if not password:
            messages.error(request, 'Vui lòng nhập mật khẩu.')
            return render(
                request,
                'app/create_instructor.html'
            )

        if password != confirm_password:
            messages.error(
                request,
                'Mật khẩu xác nhận không khớp.'
            )
            return render(
                request,
                'app/create_instructor.html'
            )

        # Kiểm tra tài khoản đã tồn tại
        if User.objects.filter(username=username).exists():
            messages.error(
                request,
                'Tên đăng nhập/email đã tồn tại.'
            )
            return render(
                request,
                'app/create_instructor.html'
            )

        # Tạo tài khoản
        instructor = User.objects.create_user(
            username=username,
            email=username,
            password=password
        )

        instructor.role = User.Role.INSTRUCTOR
        instructor.is_staff = False
        instructor.is_superuser = False
        instructor.first_name = full_name

        instructor.save()

        messages.success(
            request,
            f'Đã tạo tài khoản giảng viên {full_name} thành công.'
        )

        return redirect('admin_dashboard')

    return render(
        request,
        'app/create_instructor.html'
    )
# ==========================================================
# QUẢN LÝ HỌC VIÊN
# ==========================================================

@login_required
def admin_students(request):

    # Chỉ ADMIN
    if request.user.role != User.Role.ADMIN:
        messages.error(
            request,
            'Bạn không có quyền truy cập trang này.'
        )
        return redirect('home')

    search = request.GET.get('search', '').strip()

    students = User.objects.filter(
        role=User.Role.STUDENT
    ).annotate(
        enrollment_count=Count('enrollments', distinct=True)
    ).order_by('-id')

    if search:
        students = students.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )

    context = {
        'students': students,
        'search': search,
    }

    return render(
        request,
        'app/admin_students.html',
        context
    )


# ==========================================================
# QUẢN LÝ GIẢNG VIÊN
# ==========================================================

@login_required
def admin_instructors(request):

    # Chỉ ADMIN
    if request.user.role != User.Role.ADMIN:
        messages.error(
            request,
            'Bạn không có quyền truy cập trang này.'
        )
        return redirect('home')

    search = request.GET.get('search', '').strip()

    instructors = User.objects.filter(
        role=User.Role.INSTRUCTOR
    ).annotate(
        course_count=Count(
            'courses_created',
            distinct=True
        )
    ).order_by('-id')

    if search:
        instructors = instructors.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )

    context = {
        'instructors': instructors,
        'search': search,
    }

    return render(
        request,
        'app/admin_instructors.html',
        context
    )


# ==========================================================
# QUẢN LÝ KHÓA HỌC
# ==========================================================

@login_required
def admin_courses(request):

    # Chỉ ADMIN
    if request.user.role != User.Role.ADMIN:
        messages.error(
            request,
            'Bạn không có quyền truy cập trang này.'
        )
        return redirect('home')

    search = request.GET.get('search', '').strip()

    courses = Course.objects.select_related(
        'instructor'
    ).annotate(
        enrollment_count=Count(
            'enrollments',
            distinct=True
        ),
        chapter_count=Count(
            'chapters',
            distinct=True
        )
    ).order_by('-id')

    if search:
        courses = courses.filter(
            title__icontains=search
        )

    context = {
        'courses': courses,
        'search': search,
    }

    return render(
        request,
        'app/admin_courses.html',
        context
    )


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

    # =====================================================
    # 1. LẤY KHÓA HỌC
    # =====================================================

    course = get_object_or_404(
        Course,
        id=course_id
    )

    # =====================================================
    # 2. KIỂM TRA USER ĐÃ ĐĂNG KÝ KHÓA HỌC CHƯA
    # =====================================================

    enrollment = get_object_or_404(
        Enrollment,
        student=request.user,
        course=course,
        status__in=['ACTIVE', 'COMPLETED']
    )

    # =====================================================
    # 3. LẤY CHAPTER + LESSON
    # =====================================================

    chapters = (
        Chapter.objects
        .filter(course=course)
        .prefetch_related('lessons')
    )

    # =====================================================
    # 4. LẤY LESSON ĐƯỢC CHỌN
    # =====================================================

    all_lessons = get_course_lessons(course)
    lesson_id = request.GET.get('lesson')

    if lesson_id:

        lesson = get_object_or_404(
            Lesson,
            id=lesson_id,
            chapter__course=course
        )

    else:

        lesson = all_lessons[0] if all_lessons else None

    # =====================================================
    # 5. KIỂM TRA LESSON CÓ ĐƯỢC MỞ KHÔNG
    # =====================================================

    lesson_unlocked = is_lesson_unlocked(request.user, lesson)

    # Không gửi nội dung bài đang khóa cho trình duyệt.
    if lesson and not lesson_unlocked:
        first_unlocked_lesson = next(
            (
                item for item in all_lessons
                if is_lesson_unlocked(request.user, item)
            ),
            None,
        )
        if first_unlocked_lesson:
            return redirect(
                f"/learning/{course.id}/?lesson={first_unlocked_lesson.id}"
            )

    # =====================================================
    # 6. LẤY TIẾN ĐỘ CỦA USER CHO LESSON HIỆN TẠI
    # =====================================================

    lesson_progress = None
    next_lesson = None
    if lesson:
        lesson_progress, _ = LessonProgress.objects.get_or_create(
            user=request.user,
            lesson=lesson,
        )
        next_lesson = get_next_lesson(lesson)

    # =====================================================
    # 7. LẤY TIẾN ĐỘ TOÀN KHÓA HỌC
    # =====================================================

    course_progress = enrollment.progress

    # =====================================================
    # 8. CẬP NHẬT TRẠNG THÁI CHO SIDEBAR
    # =====================================================

    for chapter in chapters:

        for current_lesson in chapter.lessons.all():

            current_lesson.is_unlocked = (
                is_lesson_unlocked(
                    request.user,
                    current_lesson
                )
            )

            current_lesson.progress = (
                LessonProgress.objects
                .filter(
                    user=request.user,
                    lesson=current_lesson
                )
                .first()
            )

    if next_lesson:
        next_lesson.is_unlocked = is_lesson_unlocked(
            request.user,
            next_lesson,
        )

    watched_seconds = (
        (
            lesson_progress.video_watched_seconds
            if lesson and lesson.lesson_type == Lesson.LessonType.VIDEO
            else lesson_progress.watched_seconds
        )
        if lesson_progress
        else 0
    )

    # =====================================================
    # 9. TRẢ DỮ LIỆU CHO TEMPLATE
    # =====================================================

    context = {
        'course': course,
        'enrollment': enrollment,
        'chapters': chapters,
        'lesson': lesson,
        'lesson_progress': lesson_progress,
        'lesson_unlocked': lesson_unlocked,
        'course_progress': course_progress,
        'next_lesson': next_lesson,
        'watched_seconds': watched_seconds,
        'streak': get_streak_status(request.user),
    }

    return render(
        request,
        'app/learning.html',
        context
    )


@login_required
@require_POST
def track_lesson_study(request, course_id, lesson_id):
    course = get_object_or_404(Course, id=course_id)
    get_object_or_404(
        Enrollment,
        student=request.user,
        course=course,
        status__in=['ACTIVE', 'COMPLETED'],
    )
    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        chapter__course=course,
    )

    if lesson.lesson_type == Lesson.LessonType.VIDEO:
        return HttpResponseBadRequest(
            'Thời gian video được tính theo lượt phát thực tế.'
        )

    if not is_lesson_unlocked(request.user, lesson):
        return HttpResponseForbidden('Bài học này đang bị khóa.')

    progress, _ = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson,
    )
    now = timezone.now()
    credited_seconds = 0

    with transaction.atomic():
        progress = LessonProgress.objects.select_for_update().get(pk=progress.pk)
        if not progress.completed:
            if progress.last_activity_at:
                elapsed = int((now - progress.last_activity_at).total_seconds())
                # Chỉ tính khoảng ngắn giữa hai heartbeat; thời gian để tab
                # nền hoặc kết nối bị ngắt sẽ không được cộng dồn.
                if 2 <= elapsed <= 30:
                    credited_seconds = elapsed

            progress.watched_seconds += credited_seconds
            ending_session = request.POST.get('end_session') == '1'
            progress.last_activity_at = None if ending_session else now
            progress.save(update_fields=['watched_seconds', 'last_activity_at'])

    if credited_seconds:
        record_learning_time(request.user, credited_seconds)

    next_lesson = get_next_lesson(lesson)
    next_unlocked = bool(
        next_lesson and is_lesson_unlocked(request.user, next_lesson)
    )
    return JsonResponse({
        'watched_seconds': progress.watched_seconds,
        'watched_minutes': progress.watched_seconds // 60,
        'credited_seconds': credited_seconds,
        'next_lesson_id': next_lesson.id if next_lesson else None,
        'next_lesson_unlocked': next_unlocked,
    })


@login_required
@require_POST
def track_video_progress(request, course_id, lesson_id):
    course = get_object_or_404(Course, id=course_id)
    get_object_or_404(
        Enrollment,
        student=request.user,
        course=course,
        status__in=['ACTIVE', 'COMPLETED'],
    )
    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        chapter__course=course,
    )

    if lesson.lesson_type != Lesson.LessonType.VIDEO:
        return HttpResponseBadRequest('Bài học này không phải video.')

    if not is_lesson_unlocked(request.user, lesson):
        return HttpResponseForbidden('Bài học này đang bị khóa.')

    try:
        position = float(request.POST.get('position', ''))
        duration = float(request.POST.get('duration', ''))
    except (TypeError, ValueError):
        return HttpResponseBadRequest('Thiếu tiến độ video hợp lệ.')

    if (
        not math.isfinite(position)
        or not math.isfinite(duration)
        or duration <= 0
        or duration > 86400
        or position < 0
        or position > duration
    ):
        return HttpResponseBadRequest('Tiến độ video không hợp lệ.')

    progress, _ = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson,
    )
    now = timezone.now()
    credited_seconds = 0
    completed_now = False

    with transaction.atomic():
        progress = LessonProgress.objects.select_for_update().get(pk=progress.pk)
        if not progress.completed:
            if progress.video_duration_seconds is None:
                progress.video_duration_seconds = duration
            elif abs(progress.video_duration_seconds - duration) > max(
                2,
                progress.video_duration_seconds * 0.02,
            ):
                # A changed video should not inherit watch time from the old one.
                progress.video_duration_seconds = duration
                progress.video_watched_seconds = 0
                progress.watched_percent = 0
                progress.last_video_position = None

            if progress.last_video_activity_at and progress.last_video_position is not None:
                elapsed = (now - progress.last_video_activity_at).total_seconds()
                position_delta = position - progress.last_video_position
                # Only credit forward playback that could have happened during
                # the interval. A seek to the end therefore earns no progress.
                if (
                    1 <= elapsed <= 15
                    and 0 < position_delta <= elapsed * 2.5 + 1
                ):
                    credited_seconds = max(1, round(position_delta))

            progress.video_watched_seconds += credited_seconds
            progress.last_video_position = position
            progress.last_video_activity_at = now
            duration_for_progress = progress.video_duration_seconds or duration
            progress.watched_percent = min(
                100,
                progress.video_watched_seconds / duration_for_progress * 100,
            )

            completion_threshold = max(1, min(100, lesson.required_watch_percent))
            if progress.watched_percent >= completion_threshold:
                progress.completed = True
                progress.completed_at = now
                completed_now = True

            progress.save(update_fields=[
                'video_watched_seconds',
                'video_duration_seconds',
                'last_video_position',
                'last_video_activity_at',
                'watched_percent',
                'completed',
                'completed_at',
            ])

    if credited_seconds:
        record_learning_time(request.user, credited_seconds)

    if completed_now:
        update_course_progress(request.user, course)
        update_streak(request.user)
        record_learning_activity(request.user, lesson_completed=True)

    next_lesson = get_next_lesson(lesson)
    next_unlocked = bool(
        next_lesson and is_lesson_unlocked(request.user, next_lesson)
    )
    enrollment = Enrollment.objects.filter(
        student=request.user,
        course=course,
    ).first()
    streak = get_streak_status(request.user)

    return JsonResponse({
        'watched_percent': round(progress.watched_percent, 1),
        'watched_seconds': progress.video_watched_seconds,
        'completed': progress.completed,
        'completed_now': completed_now,
        'course_progress': enrollment.progress if enrollment else 0,
        'current_streak': streak.current_streak,
        'longest_streak': streak.longest_streak,
        'next_lesson_id': next_lesson.id if next_lesson else None,
        'next_lesson_unlocked': next_unlocked,
    })


@login_required
@require_POST
def record_lesson_completion(request, course_id, lesson_id):
    course = get_object_or_404(Course, id=course_id)
    get_object_or_404(
        Enrollment,
        student=request.user,
        course=course,
        status__in=['ACTIVE', 'COMPLETED'],
    )
    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        chapter__course=course,
    )

    if lesson.lesson_type == Lesson.LessonType.VIDEO:
        return HttpResponseForbidden('Video được hoàn thành qua thời lượng xem.')
    if not is_lesson_unlocked(request.user, lesson):
        return HttpResponseForbidden('Bài học này đang bị khóa.')

    source = request.POST.get('source')
    allowed_sources = {
        Lesson.LessonType.ARTICLE: 'article_read',
        Lesson.LessonType.DOCUMENT: 'document_opened',
    }
    if source != allowed_sources.get(lesson.lesson_type):
        return HttpResponseBadRequest('Không nhận diện được hoạt động học.')

    progress, _ = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson,
    )
    completed_now = complete_lesson_progress(
        request.user,
        course,
        lesson,
        progress,
    )
    progress.refresh_from_db()
    enrollment = Enrollment.objects.filter(
        student=request.user,
        course=course,
    ).first()
    streak = get_streak_status(request.user)
    next_lesson = get_next_lesson(lesson)
    next_unlocked = bool(
        next_lesson and is_lesson_unlocked(request.user, next_lesson)
    )
    return JsonResponse({
        'completed': progress.completed,
        'completed_now': completed_now,
        'course_progress': enrollment.progress if enrollment else 0,
        'current_streak': streak.current_streak,
        'longest_streak': streak.longest_streak,
        'next_lesson_id': next_lesson.id if next_lesson else None,
        'next_lesson_unlocked': next_unlocked,
    })

@login_required
def teacher_dashboard(request):

    if request.user.role != User.Role.INSTRUCTOR:
        messages.error(
            request,
            'Bạn không có quyền truy cập trang giảng viên.'
        )
        return redirect('home')

    courses = (
        Course.objects
        .filter(instructor=request.user)
        .prefetch_related('chapters')
        .order_by('-created_at')
    )

    total_courses = courses.count()

    total_chapters = Chapter.objects.filter(
        course__in=courses
    ).count()

    total_lessons = Lesson.objects.filter(
        chapter__course__in=courses
    ).count()

    total_students = Enrollment.objects.filter(
        course__in=courses
    ).values('student').distinct().count()

    context = {
        'courses': courses,
        'total_courses': total_courses,
        'total_chapters': total_chapters,
        'total_lessons': total_lessons,
        'total_students': total_students,
    }

    return render(
        request,
        'app/teacher_dashboard.html',
        context
    )
def instructor_only(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != User.Role.INSTRUCTOR:
            messages.error(request, "Bạn không có quyền truy cập trang giảng viên.")
            return redirect("home")

        return view_func(request, *args, **kwargs)

    return wrapper
@instructor_only
def teacher(request):
    courses = Course.objects.filter(
        instructor=request.user
    ).prefetch_related('chapters')

    total_courses = courses.count()

    total_chapters = sum(
        course.chapters.count()
        for course in courses
    )

    total_lessons = sum(
        chapter.lessons.count()
        for course in courses
        for chapter in course.chapters.all()
    )

    total_students = Enrollment.objects.filter(
        course__instructor=request.user
    ).values('student').distinct().count()

    context = {
        'courses': courses,
        'total_courses': total_courses,
        'total_chapters': total_chapters,
        'total_lessons': total_lessons,
        'total_students': total_students,
    }

    return render(
        request,
        'app/teacher_dashboard.html',
        context
    )
@instructor_only
def teacher_courses(request):

    courses = Course.objects.filter(
        instructor=request.user
    ).prefetch_related('chapters')

    context = {
        'courses': courses,
    }

    return render(
        request,
        'app/instructor_courses.html',
        context
    )
@instructor_only
def create_course(request):

    if request.method == "POST":

        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        thumbnail = request.FILES.get("thumbnail")

        if not title:
            messages.error(request, "Vui lòng nhập tên khóa học.")
            return render(request, "app/create_course.html")

        if not description:
            messages.error(request, "Vui lòng nhập mô tả khóa học.")
            return render(request, "app/create_course.html")

        slug = slugify(title)

        # Tránh trùng slug
        original_slug = slug
        counter = 1

        while Course.objects.filter(slug=slug).exists():
            slug = f"{original_slug}-{counter}"
            counter += 1

        course = Course.objects.create(
            title=title,
            slug=slug,
            description=description,
            thumbnail=thumbnail,
            instructor=request.user,
            ished=False
        )

        messages.success(
            request,
            f'Đã tạo khóa học "{course.title}" thành công.'
        )

        return redirect("teacher_courses")

    return render(
        request,
        "app/create_course.html"
    )
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
        'streak': get_streak_status(request.user),
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
