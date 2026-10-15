from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.db import transaction
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from datetime import date, datetime, time, timedelta
import math
from django.db.models import Avg, CharField, Count, Prefetch, Q, Sum, Value
from django.db.models.functions import Concat
from django.utils.text import slugify
from functools import wraps
from pathlib import Path

from .models import (
    User,
    Course,
    Chapter,
    Lesson,
    Enrollment,
    SaveCourse,
    LessonProgress,
    LearningActivity,
    Assignment,
    Quiz,
)
from .forms import InstructorProfileForm, StudentProfileForm
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
# Thư viện để đọc thời lượng video
#from moviepy.editor import VideoFileClip

# ==========================================================
# 1. HỆ THỐNG XÁC THỰC (AUTHENTICATION) & TRANG CHỦ
# ==========================================================

def home(request):
    # Nếu người dùng đã đăng nhập, chuyển hướng đúng dashboard theo vai trò
    if request.user.is_authenticated:
        if request.user.role == User.Role.ADMIN:
            return redirect('admin_dashboard')
        if request.user.role == User.Role.INSTRUCTOR:
            return redirect('teacher_dashboard')

    public_courses = Course.objects.filter(ished=True).select_related(
        "instructor",
    ).annotate(
        enrollment_count=Count("enrollments", distinct=True),
    )
    courses = public_courses.order_by("-created_at", "-id")[:4]
    popular_courses = public_courses.order_by(
        "-enrollment_count",
        "-created_at",
        "-id",
    )[:4]

    student_enrollments = []
    if request.user.is_authenticated and request.user.role == User.Role.STUDENT:
        student_enrollments = list(
            Enrollment.objects.filter(
                student=request.user,
                status="ACTIVE",
                course__ished=True,
            ).select_related("course").order_by("-created_at")[:3]
        )

    context = {
        "courses": courses,
        "popular_courses": popular_courses,
        "student_enrollments": student_enrollments,
        "public_course_count": Course.objects.filter(ished=True).count(),
        "public_lesson_count": Lesson.objects.filter(
            status="active",
            chapter__course__ished=True,
        ).count(),
        "instructor_count": User.objects.filter(
            role=User.Role.INSTRUCTOR,
            courses_created__ished=True,
        ).distinct().count(),
    }
    return render(request, 'app/home.html', context)


def term(request):
    return render(request, 'app/term.html')


def registerPage(request):
    if request.method == 'POST':
        full_name = request.POST.get('name', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password')
        password_confirmation = request.POST.get('confirm_password')
        
        submitted_role = request.POST.get('role', 'STUDENT').upper()
        if submitted_role in ['INSTRUCTOR', 'STUDENT']:
            user_role = submitted_role
        else:
            user_role = 'STUDENT'

        if any(character.isdigit() for character in full_name):
            messages.error(request, 'Họ và tên không được chứa chữ số!')
            return render(request, 'app/register.html')

        if full_name:
            full_name = ' '.join(word.capitalize() for word in full_name.split())

        if not username.endswith('@gmail.com') or len(username) <= len('@gmail.com'):
            messages.error(request, 'Email đăng ký phải có định dạng đầy đủ là @gmail.com!')
            return render(request, 'app/register.html')

        if password != password_confirmation:
            messages.error(request, 'Mật khẩu nhập lại không khớp!')
            return render(request, 'app/register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Tên đăng nhập hoặc email này đã tồn tại!')
            return render(request, 'app/register.html')

        user = User.objects.create_user(username=username, email=username, password=password)
        
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

        matching_user = User.objects.filter(email__iexact=login_identifier).first()
        if not matching_user:
            matching_user = User.objects.filter(username__iexact=login_identifier).first()

        username_to_auth = matching_user.username if matching_user else login_identifier

        user = authenticate(request, username=username_to_auth, password=password)

        if user is not None:
            login(request, user)
            if user.role == User.Role.ADMIN:
                return redirect('admin_dashboard')
            elif user.role == User.Role.INSTRUCTOR:
                return redirect('teacher_dashboard')
            elif user.role == User.Role.STUDENT:
                return redirect('home')
            return redirect('home')
        else:
            messages.error(request, 'Email/Tên đăng nhập hoặc mật khẩu không chính xác!')
            return render(request, 'app/login.html')

    return render(request, 'app/login.html')


def logoutPage(request):
    logout(request)
    return redirect('login')


# ==========================================================
# 2. KHÓA HỌC & HỌC TẬP (DÀNH CHO HỌC VIÊN)
# ==========================================================

def courses(request):
    courses, catalog_context = get_student_course_catalog(request)
    context = {'courses': courses, **catalog_context}
    return render(request, 'app/courses.html', context)


def detail_course(request):
    course_id = request.GET.get('id')
    if course_id:
        course = get_object_or_404(
            Course.objects.select_related("instructor"),
            id=course_id,
            ished=True,
        )
    else:
        return redirect('courses')

    chapters = Chapter.objects.filter(course=course).annotate(
        active_lesson_count=Count(
            "lessons",
            filter=Q(lessons__status="active"),
        ),
        active_duration=Sum(
            "lessons__duration",
            filter=Q(lessons__status="active"),
        ),
    ).filter(active_lesson_count__gt=0).prefetch_related(
        Prefetch(
            "lessons",
            queryset=Lesson.objects.filter(status="active").order_by("order", "id"),
        )
    )
    lesson_summary = Lesson.objects.filter(
        chapter__course=course,
        status="active",
    ).aggregate(
        total_lessons=Count("id"),
        total_minutes=Sum("duration"),
        preview_count=Count("id", filter=Q(is_preview=True)),
    )
    course.enrollment_count = Enrollment.objects.filter(
        course=course,
        status__in=["ACTIVE", "COMPLETED"],
    ).count()

    enrollment = None
    is_saved = False
    if request.user.is_authenticated and request.user.role == User.Role.STUDENT:
        enrollment = Enrollment.objects.filter(
            student=request.user,
            course=course,
        ).first()
        is_saved = SaveCourse.objects.filter(
            student=request.user,
            course=course,
        ).exists()

    context = {
        'course': course,
        'chapters': chapters,
        'total_lessons': lesson_summary["total_lessons"],
        'total_minutes': lesson_summary["total_minutes"] or 0,
        'preview_count': lesson_summary["preview_count"],
        'enrollment': enrollment,
        'is_saved': is_saved,
    }
    return render(request, 'app/detail_course.html', context)


def search(request):
    matching_courses, catalog_context = get_student_course_catalog(request)
    context = {
        'matching_courses': matching_courses,
        **catalog_context,
    }
    return render(request, 'app/search.html', context)


def get_student_course_catalog(request):
    search_query = request.GET.get(
        "q",
        request.GET.get("searched", request.POST.get("searched", "")),
    ).strip()
    selected_instructor = request.GET.get("instructor", "").strip()
    sort_by = request.GET.get("sort", "newest")

    courses = Course.objects.filter(ished=True).select_related("instructor").annotate(
        enrollment_count=Count("enrollments"),
        instructor_name=Concat(
            "instructor__first_name",
            Value(" "),
            "instructor__last_name",
            output_field=CharField(),
        ),
    )
    if search_query:
        title_matches = courses.filter(title__icontains=search_query)
        if title_matches.exists():
            courses = title_matches
        else:
            courses = courses.filter(
                Q(description__icontains=search_query)
                | Q(instructor__first_name__icontains=search_query)
                | Q(instructor__last_name__icontains=search_query)
                | Q(instructor__username__icontains=search_query)
                | Q(instructor_name__icontains=search_query)
            )

    if selected_instructor.isdigit():
        courses = courses.filter(instructor_id=int(selected_instructor))
    else:
        selected_instructor = ""

    ordering = {
        "newest": ("-created_at", "-id"),
        "oldest": ("created_at", "id"),
        "title": ("title", "id"),
        "popular": ("-enrollment_count", "-created_at", "-id"),
    }
    if sort_by not in ordering:
        sort_by = "newest"
    courses = courses.order_by(*ordering[sort_by])

    instructors = User.objects.filter(
        role=User.Role.INSTRUCTOR,
        courses_created__ished=True,
    ).order_by("first_name", "last_name", "username").distinct()
    return courses, {
        "search_query": search_query,
        "selected_instructor": selected_instructor,
        "sort_by": sort_by,
        "instructors": instructors,
    }


@login_required
@require_POST
def enroll_course(request, course_id):
    course_to_enroll = get_object_or_404(Course, id=course_id, ished=True)
    _enrollment_record, was_created = Enrollment.objects.get_or_create(
        student=request.user,
        course=course_to_enroll,
        defaults={"status": "ACTIVE", "progress": 0}
    )
    
    if was_created:
        message = "Bạn đã đăng ký khóa học thành công."
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "status": "success",
                "message": message,
                "redirect_url": reverse("learning", args=[course_to_enroll.id]),
            })
        messages.success(request, message)
        return redirect("learning", course_id=course_to_enroll.id)

    message = "Bạn đã đăng ký khóa học này rồi."
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "status": "info",
            "message": message,
            "redirect_url": reverse("learning", args=[course_to_enroll.id]),
        })
    messages.info(request, message)
    if _enrollment_record.status in {"ACTIVE", "COMPLETED"}:
        return redirect("learning", course_id=course_to_enroll.id)
    return redirect("profile")


def saved_courses(request):
    saved_course_records = SaveCourse.objects.filter(
        student=request.user,
        course__ished=True,
    ).select_related('course')
    active_enrollments = Enrollment.objects.filter(
        student=request.user,
        status='ACTIVE',
        course__ished=True,
    ).select_related('course')
    saved_courses_list = [record.course for record in saved_course_records]
    context = {
        'active_enrollments': active_enrollments,
        'saved_courses': saved_courses_list,
    }
    return render(request, 'app/saved_course.html', context)


@login_required
@require_POST
def saved_course(request, course_id):
    course_to_toggle = get_object_or_404(Course, id=course_id)
    existing_record = SaveCourse.objects.filter(
        student=request.user,
        course=course_to_toggle,
    ).first()
    if not course_to_toggle.ished and not existing_record:
        raise Http404

    if existing_record:
        existing_record.delete()
        messages.info(request, "Đã xóa khóa học khỏi danh sách đã lưu")
    else:
        SaveCourse.objects.create(student=request.user, course=course_to_toggle)
        messages.success(request, "Đã lưu khóa học vào danh sách yêu thích")
    return redirect('saved_courses')


@login_required
def profile(request):
    if request.method == "POST" and request.user.role not in {
        User.Role.INSTRUCTOR,
        User.Role.STUDENT,
    }:
        messages.error(request, "Bạn không có quyền cập nhật hồ sơ tại đây.")
        return redirect("profile")

    # Sửa lại điều kiện để bắt đúng tài khoản có role là INSTRUCTOR
    if request.user.role == 'INSTRUCTOR' or request.user.is_staff or request.user.is_superuser:
        can_edit_profile = request.user.role == User.Role.INSTRUCTOR
        profile_form = None
        if can_edit_profile:
            profile_form = InstructorProfileForm(
                user=request.user,
                initial={
                    "full_name": request.user.get_full_name().strip() or request.user.username,
                    "email": request.user.email,
                    "bio": request.user.bio or "",
                },
            )
            if request.method == "POST":
                profile_form = InstructorProfileForm(
                    request.POST,
                    request.FILES,
                    user=request.user,
                )
                if profile_form.is_valid():
                    request.user.first_name = profile_form.cleaned_data["full_name"].strip()
                    request.user.last_name = ""
                    request.user.email = profile_form.cleaned_data["email"]
                    request.user.username = profile_form.cleaned_data["email"]
                    request.user.bio = profile_form.cleaned_data["bio"].strip()
                    avatar = profile_form.cleaned_data["avatar"]
                    if avatar:
                        request.user.avatar = avatar
                    request.user.save()
                    messages.success(request, "Thông tin giảng viên đã được cập nhật.")
                    return redirect("profile")

        created_courses_count = Course.objects.filter(instructor=request.user).count()
        context = {
            'created_courses_count': created_courses_count,
            'can_edit_profile': can_edit_profile,
            'profile_form': profile_form,
        }
        return render(request, 'app/teacher_profile.html', context)
    
    # Sinh viên
    student_profile_form = StudentProfileForm(
        user=request.user,
        initial={
            "full_name": request.user.get_full_name().strip() or request.user.username,
            "email": request.user.email,
        },
    )
    if request.method == "POST":
        student_profile_form = StudentProfileForm(
            request.POST,
            request.FILES,
            user=request.user,
        )
        if student_profile_form.is_valid():
            request.user.first_name = student_profile_form.cleaned_data["full_name"].strip()
            request.user.last_name = ""
            request.user.email = student_profile_form.cleaned_data["email"]
            request.user.username = student_profile_form.cleaned_data["email"]
            avatar = student_profile_form.cleaned_data["avatar"]
            if avatar:
                request.user.avatar = avatar
            request.user.save()
            messages.success(request, "Thông tin học viên đã được cập nhật.")
            return redirect("profile")

    active_enrollments = Enrollment.objects.filter(
        student=request.user,
        status='ACTIVE',
        course__ished=True,
    ).select_related('course')
    completed_enrollments = Enrollment.objects.filter(
        student=request.user,
        status='COMPLETED',
        course__ished=True,
    ).select_related('course')
    completed_lessons = LessonProgress.objects.filter(
        user=request.user,
        completed=True,
        lesson__chapter__course__ished=True,
        lesson__chapter__course__enrollments__student=request.user,
        lesson__chapter__course__enrollments__status__in=['ACTIVE', 'COMPLETED'],
    ).distinct().count()
    study_seconds = LearningActivity.objects.filter(
        user=request.user,
    ).aggregate(total=Sum("study_seconds"))["total"] or 0
    context = {
        'active_enrollments': active_enrollments,
        'completed_courses_count': completed_enrollments.count(),
        'completed_lessons_count': completed_lessons,
        'study_hours': study_seconds // 3600,
        'study_minutes_remainder': (study_seconds % 3600) // 60,
        'streak': get_streak_status(request.user),
        'student_profile_form': student_profile_form,
    }
    return render(request, 'app/profile.html', context)


@login_required
def my_courses(request):
    if request.user.role != User.Role.STUDENT:
        return redirect("profile")

    active_enrollments = Enrollment.objects.filter(
        student=request.user,
        status="ACTIVE",
        course__ished=True,
    ).select_related("course", "course__instructor").order_by("-created_at")
    completed_enrollments = Enrollment.objects.filter(
        student=request.user,
        status="COMPLETED",
        course__ished=True,
    ).select_related("course", "course__instructor").order_by("-created_at")

    return render(request, "app/my_courses.html", {
        "active_enrollments": active_enrollments,
        "completed_enrollments": completed_enrollments,
    })


# --- Trình phát học tập (Learning Room) ---

@login_required
def learning(request, course_id):
    course = get_object_or_404(Course, id=course_id, ished=True)
    enrollment = get_object_or_404(
        Enrollment,
        student=request.user,
        course=course,
        status__in=['ACTIVE', 'COMPLETED']
    )
    chapters = Chapter.objects.filter(course=course).prefetch_related(
        Prefetch('lessons', queryset=Lesson.objects.filter(status='active'))
    )
    all_lessons = get_course_lessons(course)
    lesson_id = request.GET.get('lesson')

    if lesson_id:
        lesson = get_object_or_404(
            Lesson,
            id=lesson_id,
            chapter__course=course,
            status='active',
        )
    else:
        lesson = all_lessons[0] if all_lessons else None

    lesson_unlocked = is_lesson_unlocked(request.user, lesson)

    if lesson and not lesson_unlocked:
        first_unlocked_lesson = next(
            (item for item in all_lessons if is_lesson_unlocked(request.user, item)),
            None,
        )
        if first_unlocked_lesson:
            return redirect(f"/learning/{course.id}/?lesson={first_unlocked_lesson.id}")

    lesson_progress = None
    next_lesson = None
    if lesson:
        lesson_progress, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
        next_lesson = get_next_lesson(lesson)

    course_progress = enrollment.progress

    for chapter in chapters:
        for current_lesson in chapter.lessons.all():
            current_lesson.is_unlocked = is_lesson_unlocked(request.user, current_lesson)
            current_lesson.progress = LessonProgress.objects.filter(user=request.user, lesson=current_lesson).first()

    if next_lesson:
        next_lesson.is_unlocked = is_lesson_unlocked(request.user, next_lesson)

    watched_seconds = (
        (
            lesson_progress.video_watched_seconds
            if lesson and lesson.lesson_type == Lesson.LessonType.VIDEO
            else lesson_progress.watched_seconds
        )
        if lesson_progress
        else 0
    )

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

    return render(request, 'app/learning.html', context)


@login_required
@require_POST
def track_lesson_study(request, course_id, lesson_id):
    course = get_object_or_404(Course, id=course_id, ished=True)
    get_object_or_404(Enrollment, student=request.user, course=course, status__in=['ACTIVE', 'COMPLETED'])
    lesson = get_object_or_404(
        Lesson, id=lesson_id, chapter__course=course, status='active'
    )

    if lesson.lesson_type == Lesson.LessonType.VIDEO:
        return HttpResponseBadRequest('Thời gian video được tính theo lượt phát thực tế.')

    if not is_lesson_unlocked(request.user, lesson):
        return HttpResponseForbidden('Bài học này đang bị khóa.')

    progress, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
    now = timezone.now()
    credited_seconds = 0

    with transaction.atomic():
        progress = LessonProgress.objects.select_for_update().get(pk=progress.pk)
        if not progress.completed:
            if progress.last_activity_at:
                elapsed = int((now - progress.last_activity_at).total_seconds())
                if 2 <= elapsed <= 30:
                    credited_seconds = elapsed

            progress.watched_seconds += credited_seconds
            ending_session = request.POST.get('end_session') == '1'
            progress.last_activity_at = None if ending_session else now
            progress.save(update_fields=['watched_seconds', 'last_activity_at'])

    if credited_seconds:
        record_learning_time(request.user, credited_seconds)

    next_lesson = get_next_lesson(lesson)
    next_unlocked = bool(next_lesson and is_lesson_unlocked(request.user, next_lesson))
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
    course = get_object_or_404(Course, id=course_id, ished=True)
    get_object_or_404(Enrollment, student=request.user, course=course, status__in=['ACTIVE', 'COMPLETED'])
    lesson = get_object_or_404(
        Lesson, id=lesson_id, chapter__course=course, status='active'
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

    if not math.isfinite(position) or not math.isfinite(duration) or duration <= 0 or duration > 86400 or position < 0 or position > duration:
        return HttpResponseBadRequest('Tiến độ video không hợp lệ.')

    progress, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
    now = timezone.now()
    credited_seconds = 0
    completed_now = False

    with transaction.atomic():
        progress = LessonProgress.objects.select_for_update().get(pk=progress.pk)
        if not progress.completed:
            if progress.video_duration_seconds is None:
                progress.video_duration_seconds = duration
            elif abs(progress.video_duration_seconds - duration) > max(2, progress.video_duration_seconds * 0.02):
                progress.video_duration_seconds = duration
                progress.video_watched_seconds = 0
                progress.watched_percent = 0
                progress.last_video_position = None

            if progress.last_video_activity_at and progress.last_video_position is not None:
                elapsed = (now - progress.last_video_activity_at).total_seconds()
                position_delta = position - progress.last_video_position
                if 1 <= elapsed <= 15 and 0 < position_delta <= elapsed * 2.5 + 1:
                    credited_seconds = max(1, round(position_delta))

            progress.video_watched_seconds += credited_seconds
            progress.last_video_position = position
            progress.last_video_activity_at = now
            duration_for_progress = progress.video_duration_seconds or duration
            progress.watched_percent = min(100, progress.video_watched_seconds / duration_for_progress * 100)

            completion_threshold = max(1, min(100, lesson.required_watch_percent))
            if progress.watched_percent >= completion_threshold:
                progress.completed = True
                progress.completed_at = now
                completed_now = True

            progress.save(update_fields=[
                'video_watched_seconds', 'video_duration_seconds', 'last_video_position',
                'last_video_activity_at', 'watched_percent', 'completed', 'completed_at',
            ])

    if credited_seconds:
        record_learning_time(request.user, credited_seconds)

    if completed_now:
        update_course_progress(request.user, course)
        update_streak(request.user)
        record_learning_activity(request.user, lesson_completed=True)

    next_lesson = get_next_lesson(lesson)
    next_unlocked = bool(next_lesson and is_lesson_unlocked(request.user, next_lesson))
    enrollment = Enrollment.objects.filter(student=request.user, course=course).first()
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
    course = get_object_or_404(Course, id=course_id, ished=True)
    get_object_or_404(Enrollment, student=request.user, course=course, status__in=['ACTIVE', 'COMPLETED'])
    lesson = get_object_or_404(
        Lesson, id=lesson_id, chapter__course=course, status='active'
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

    progress, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
    completed_now = complete_lesson_progress(request.user, course, lesson, progress)
    progress.refresh_from_db()
    enrollment = Enrollment.objects.filter(student=request.user, course=course).first()
    streak = get_streak_status(request.user)
    next_lesson = get_next_lesson(lesson)
    next_unlocked = bool(next_lesson and is_lesson_unlocked(request.user, next_lesson))
    return JsonResponse({
        'completed': progress.completed,
        'completed_now': completed_now,
        'course_progress': enrollment.progress if enrollment else 0,
        'current_streak': streak.current_streak,
        'longest_streak': streak.longest_streak,
        'next_lesson_id': next_lesson.id if next_lesson else None,
        'next_lesson_unlocked': next_unlocked,
    })


# ==========================================================
# 3. QUẢN TRỊ HỆ THỐNG (ADMIN)
# ==========================================================

@login_required
def admin_dashboard(request):
    if request.user.role != 'ADMIN':
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')

    timeframe = request.GET.get('period', '30d')
    if timeframe not in {'7d', '30d', '12m'}:
        timeframe = '30d'

    today = timezone.localdate()
    if timeframe == '7d':
        day_count = 7
        period_start = today - timedelta(days=day_count - 1)
        bucket_dates = [period_start + timedelta(days=index) for index in range(day_count)]
        chart_labels = [bucket.strftime('%d/%m') for bucket in bucket_dates]
        enrollments_by_bucket = {
            row['bucket']: row['total']
            for row in Enrollment.objects.filter(
                created_at__date__gte=period_start,
                created_at__date__lte=today,
            ).annotate(bucket=TruncDate('created_at')).values('bucket').annotate(
                total=Count('id')
            )
        }
        chart_values = [enrollments_by_bucket.get(bucket, 0) for bucket in bucket_dates]
        previous_start = period_start - timedelta(days=day_count)
        previous_end = period_start - timedelta(days=1)
    elif timeframe == '30d':
        day_count = 30
        period_start = today - timedelta(days=day_count - 1)
        bucket_dates = [period_start + timedelta(days=index) for index in range(day_count)]
        chart_labels = [bucket.strftime('%d/%m') for bucket in bucket_dates]
        enrollments_by_bucket = {
            row['bucket']: row['total']
            for row in Enrollment.objects.filter(
                created_at__date__gte=period_start,
                created_at__date__lte=today,
            ).annotate(bucket=TruncDate('created_at')).values('bucket').annotate(
                total=Count('id')
            )
        }
        chart_values = [enrollments_by_bucket.get(bucket, 0) for bucket in bucket_dates]
        previous_start = period_start - timedelta(days=day_count)
        previous_end = period_start - timedelta(days=1)
    else:
        month_index = today.year * 12 + today.month - 1
        bucket_months = []
        for offset in range(11, -1, -1):
            bucket_index = month_index - offset
            bucket_year, zero_based_month = divmod(bucket_index, 12)
            bucket_months.append(date(bucket_year, zero_based_month + 1, 1))
        period_start = bucket_months[0]
        chart_labels = [f"Tháng {bucket.month}/{bucket.year}" for bucket in bucket_months]
        enrollments_by_bucket = {
            date(row['bucket'].year, row['bucket'].month, 1): row['total']
            for row in Enrollment.objects.filter(
                created_at__date__gte=period_start,
                created_at__date__lte=today,
            ).annotate(bucket=TruncMonth('created_at')).values('bucket').annotate(
                total=Count('id')
            )
        }
        chart_values = [enrollments_by_bucket.get(bucket, 0) for bucket in bucket_months]
        previous_start = date(period_start.year - 1, period_start.month, 1)
        previous_end = period_start - timedelta(days=1)

    period_enrollments = Enrollment.objects.filter(
        created_at__date__gte=period_start,
        created_at__date__lte=today,
    ).count()
    previous_enrollments = Enrollment.objects.filter(
        created_at__date__gte=previous_start,
        created_at__date__lte=previous_end,
    ).count()
    if previous_enrollments:
        enrollment_change = round(
            (period_enrollments - previous_enrollments) * 100 / previous_enrollments
        )
    else:
        enrollment_change = 100 if period_enrollments else 0

    total_students = User.objects.filter(role=User.Role.STUDENT).count()
    total_instructors = User.objects.filter(role=User.Role.INSTRUCTOR).count()
    total_courses = Course.objects.count()
    total_enrollments = Enrollment.objects.count()
    recent_courses = Course.objects.order_by('-id')[:5]
    instructors = User.objects.filter(role=User.Role.INSTRUCTOR).order_by('-id')[:5]
    popular_courses = Course.objects.select_related('instructor').annotate(
        student_count=Count('enrollments', distinct=True)
    ).order_by('-student_count', 'title')[:5]

    active_users = User.objects.filter(is_active=True).count()
    inactive_users = User.objects.filter(is_active=False).count()
    published_courses = Course.objects.filter(ished=True).count()
    unpublished_courses = Course.objects.filter(ished=False).count()

    period_start_datetime = timezone.make_aware(
        datetime.combine(period_start, time.min)
    )
    activity_items = []
    for enrollment in Enrollment.objects.filter(
        created_at__gte=period_start_datetime,
        created_at__date__lte=today,
    ).select_related('student', 'course').order_by('-created_at')[:8]:
        activity_items.append({
            'created_at': enrollment.created_at,
            'icon': 'bi-person-plus-fill',
            'color': 'success',
            'title': enrollment.student.get_full_name() or enrollment.student.username,
            'description': f'đăng ký khóa học {enrollment.course.title}',
        })
    for course in Course.objects.filter(
        created_at__gte=period_start_datetime,
        created_at__date__lte=today,
    ).select_related('instructor').order_by('-created_at')[:8]:
        activity_items.append({
            'created_at': course.created_at,
            'icon': 'bi-journal-plus',
            'color': 'warning',
            'title': course.title,
            'description': 'khóa học mới được tạo',
        })
    for user in User.objects.filter(
        date_joined__gte=period_start_datetime,
        date_joined__date__lte=today,
    ).order_by('-date_joined')[:8]:
        activity_items.append({
            'created_at': user.date_joined,
            'icon': 'bi-person-add',
            'color': 'primary',
            'title': user.get_full_name() or user.username,
            'description': f'tài khoản {user.get_role_display().lower()} mới',
        })
    recent_activity = sorted(
        activity_items,
        key=lambda item: item['created_at'],
        reverse=True,
    )[:8]

    context = {
        'total_students': total_students,
        'total_instructors': total_instructors,
        'total_courses': total_courses,
        'total_enrollments': total_enrollments,
        'recent_courses': recent_courses,
        'instructors': instructors,
        'popular_courses': popular_courses,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'published_courses': published_courses,
        'unpublished_courses': unpublished_courses,
        'timeframe': timeframe,
        'chart_labels': chart_labels,
        'chart_values': chart_values,
        'period_enrollments': period_enrollments,
        'previous_enrollments': previous_enrollments,
        'enrollment_change': enrollment_change,
        'recent_activity': recent_activity,
    }
    return render(request, 'app/admin_dashboard.html', context)


@login_required
def create_instructor(request):
    if request.user.role != 'ADMIN':
        messages.error(request, 'Bạn không có quyền thực hiện chức năng này.')
        return redirect('home')

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if not full_name:
            messages.error(request, 'Vui lòng nhập họ tên.')
            return render(request, 'app/create_instructor.html')
        if not username:
            messages.error(request, 'Vui lòng nhập email/tên đăng nhập.')
            return render(request, 'app/create_instructor.html')
        if not password:
            messages.error(request, 'Vui lòng nhập mật khẩu.')
            return render(request, 'app/create_instructor.html')
        if password != confirm_password:
            messages.error(request, 'Mật khẩu xác nhận không khớp.')
            return render(request, 'app/create_instructor.html')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Tên đăng nhập/email đã tồn tại.')
            return render(request, 'app/create_instructor.html')

        instructor = User.objects.create_user(username=username, email=username, password=password)
        instructor.role = User.Role.INSTRUCTOR
        instructor.is_staff = False
        instructor.is_superuser = False
        instructor.first_name = full_name
        instructor.save()

        messages.success(request, f'Đã tạo tài khoản giảng viên {full_name} thành công.')
        return redirect('admin_dashboard')

    return render(request, 'app/create_instructor.html')


@login_required
def admin_students(request):
    if request.user.role != User.Role.ADMIN:
        messages.error(request, 'Bạn không có quyền truy cập trang này.')
        return redirect('home')

    search = request.GET.get('search', '').strip()
    students = User.objects.filter(role=User.Role.STUDENT).annotate(
        enrollment_count=Count('enrollments', distinct=True)
    ).order_by('-id')

    if search:
        students = students.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )

    context = {'students': students, 'search': search}
    return render(request, 'app/admin_students.html', context)


@login_required
def admin_instructors(request):
    if request.user.role != User.Role.ADMIN:
        messages.error(request, 'Bạn không có quyền truy cập trang này.')
        return redirect('home')

    search = request.GET.get('search', '').strip()
    instructors = User.objects.filter(role=User.Role.INSTRUCTOR).annotate(
        course_count=Count('courses_created', distinct=True)
    ).order_by('-id')

    if search:
        instructors = instructors.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )

    context = {'instructors': instructors, 'search': search}
    return render(request, 'app/admin_instructors.html', context)


@login_required
def admin_courses(request):
    if request.user.role != User.Role.ADMIN:
        messages.error(request, 'Bạn không có quyền truy cập trang này.')
        return redirect('home')

    search = request.GET.get('search', '').strip()
    courses = Course.objects.select_related('instructor').annotate(
        enrollment_count=Count('enrollments', distinct=True),
        chapter_count=Count('chapters', distinct=True)
    ).order_by('-id')

    if search:
        courses = courses.filter(title__icontains=search)

    context = {'courses': courses, 'search': search}
    return render(request, 'app/admin_courses.html', context)


# ==========================================================
# 4. KHU VỰC GIẢNG VIÊN (INSTRUCTOR MANAGEMENT)
# ==========================================================

LESSON_ATTACHMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.ppt', '.pptx'}


def is_supported_lesson_attachment(upload):
    return Path(upload.name).suffix.lower() in LESSON_ATTACHMENT_EXTENSIONS


def instructor_only(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != User.Role.INSTRUCTOR:
            messages.error(request, "Bạn không có quyền truy cập trang giảng viên.")
            return redirect("home")
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
def teacher_dashboard(request):
    if request.user.role != 'INSTRUCTOR':
        messages.error(request, 'Bạn không có quyền truy cập trang giảng viên.')
        return redirect('home')

    courses = Course.objects.filter(instructor=request.user).annotate(
        enrollment_count=Count('enrollments', distinct=True),
        lesson_count=Count('chapters__lessons', distinct=True),
    ).prefetch_related('chapters').order_by('-created_at')
    
    total_courses = courses.count()
    total_chapters = Chapter.objects.filter(course__in=courses).count()
    total_lessons = Lesson.objects.filter(chapter__course__in=courses).count()
    total_students = Enrollment.objects.filter(course__in=courses).values('student').distinct().count()

    # Lấy danh sách đăng ký kèm thời gian
    enrollments_qs = Enrollment.objects.filter(
        course__in=courses
    ).select_related('student', 'course').order_by('-created_at')
    
    recent_enrollments = []
    for en in enrollments_qs[:8]:
        # Giả sử model Enrollment có trường thời gian là enrolled_at hoặc created_at (nếu không có, dùng ngày hiện tại)
        en_date = getattr(en, 'enrolled_at', None) or getattr(en, 'created_at', timezone.now())
        recent_enrollments.append({
            'student_name': en.student.get_full_name() or en.student.username,
            'course_title': en.course.title,
            'date_str': en_date.strftime('%d/%m/%Y')  # Định dạng ngày: DD/MM/YYYY
        })

    context = {
        'courses': courses,
        'total_courses': total_courses,
        'total_chapters': total_chapters,
        'total_lessons': total_lessons,
        'total_students': total_students,
        'recent_enrollments': recent_enrollments,
    }
    return render(request, 'app/teacher_dashboard.html', context)


@instructor_only
def teacher(request):
    courses = Course.objects.filter(instructor=request.user).annotate(
        enrollment_count=Count('enrollments', distinct=True)
    ).prefetch_related('chapters')
    courses = Course.objects.filter(instructor=request.user).prefetch_related('chapters')
    total_courses = courses.count()
    total_chapters = sum(course.chapters.count() for course in courses)
    total_lessons = sum(chapter.lessons.count() for course in courses for chapter in course.chapters.all())
    total_students = Enrollment.objects.filter(course__instructor=request.user).values('student').distinct().count()

    context = {
        'courses': courses,
        'total_courses': total_courses,
        'total_chapters': total_chapters,
        'total_lessons': total_lessons,
        'total_students': total_students,
    }
    return render(request, 'app/teacher_dashboard.html', context)


@instructor_only
def teacher_courses(request):
    courses = Course.objects.filter(instructor=request.user).order_by('-id')

    # Tìm kiếm theo tên khóa học
    search_query = request.GET.get('q', '').strip()
    if search_query:
        courses = courses.filter(title__icontains=search_query)

    # Lọc theo trạng thái xuất bản (dùng đúng trường ished trong model Course)
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        courses = courses.filter(ished=True)   # Đang hoạt động / Đã xuất bản
    elif status_filter == 'inactive':
        courses = courses.filter(ished=False)  # Tạm ngưng / Chưa xuất bản

    context = {
        'courses': courses,
        'search_query': search_query,
        'selected_status': status_filter,
    }
    return render(request, 'app/teacher_courses.html', context)

@instructor_only
def create_course(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        thumbnail = request.FILES.get("thumbnail")
        status_value = request.POST.get("status", "published")
        if status_value not in {"published", "draft"}:
            messages.error(request, "Trạng thái khóa học không hợp lệ.")
            return render(request, "app/add_course.html")
        is_published = status_value == "published"

        if not title:
            messages.error(request, "Vui lòng nhập tên khóa học.")
            return render(request, "app/add_course.html")

        if not description:
            messages.error(request, "Vui lòng nhập mô tả khóa học.")
            return render(request, "app/add_course.html")

        slug = slugify(title)
        original_slug = slug
        counter = 1

        while Course.objects.filter(slug=slug).exists():
            slug = f"{original_slug}-{counter}"
            counter += 1

        # Lưu vào database với trạng thái động vừa nhận
        course = Course.objects.create(
            title=title,
            slug=slug,
            description=description,
            thumbnail=thumbnail,
            instructor=request.user,
            ished=is_published  # Sử dụng biến động thay vì gán cứng False
        )

        messages.success(request, f'Đã tạo khóa học "{course.title}" thành công.')
        return redirect("teacher_courses")

    return render(request, 'app/add_course.html')


def add_course(request):
    return render(request, 'app/add_course.html')


@instructor_only
def edit_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        thumbnail = request.FILES.get("thumbnail")

        if not title:
            messages.error(request, "Vui lòng nhập tên khóa học.")
            return render(request, "app/edit_course.html", {"course": course})

        if not description:
            messages.error(request, "Vui lòng nhập mô tả khóa học.")
            return render(request, "app/edit_course.html", {"course": course})

        course.title = title
        course.description = description
        status_value = request.POST.get("status")
        if status_value not in {"published", "draft"}:
            messages.error(request, "Vui lòng chọn trạng thái công khai hoặc riêng tư.")
            return render(request, "app/edit_course.html", {"course": course})
        course.ished = status_value == "published"
        if thumbnail:
            course.thumbnail = thumbnail
        course.save()

        messages.success(request, f'Đã cập nhật khóa học "{course.title}" thành công.')
        return redirect("teacher_courses")

    context = {"course": course}
    return render(request, "app/edit_course.html", context)


@instructor_only
def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)

    # Cho phép xóa thành công bất kể là GET hay POST
    course.delete()
    messages.success(request, "Đã xóa khóa học thành công.")
    return redirect('teacher_courses')


# --- Quản lý Chi tiết Khóa học, Chương & Bài học (Giảng viên) ---

@instructor_only
def course_detail_instructor(request, course_id):
    """Trang xem chi tiết và quản lý chương, bài học của một khóa học"""
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    context = {'course': course}
    return render(request, 'app/course_detail_instructor.html', context)


@login_required
def add_chapter(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    if request.method == 'POST':
        title = request.POST.get('title')
        if title:
            Chapter.objects.create(course=course, title=title)
            messages.success(request, 'Thêm chương mới thành công!')
        else:
            messages.error(request, 'Tiêu đề chương không được để trống.')
    return redirect('course_detail_instructor', course_id=course.id)


@login_required
def delete_chapter(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id, course__instructor=request.user)
    course_id = chapter.course.id
    chapter.delete()
    messages.success(request, 'Đã xóa chương thành công!')
    return redirect('course_detail_instructor', course_id=course_id)


@instructor_only
def add_lesson(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id, course__instructor=request.user)
    course_id = chapter.course.id
    if request.method == 'POST':
        title = request.POST.get('title')
        video_url = request.POST.get('video_url', '')
        content = request.POST.get('content', '')
        status = request.POST.get('status', 'active')
        attachment = request.FILES.get('attachment')
        if attachment and not is_supported_lesson_attachment(attachment):
            messages.error(
                request,
                'Tệp bài giảng phải có định dạng PDF, Word (.doc/.docx) hoặc PowerPoint (.ppt/.pptx).',
            )
        elif status not in {'active', 'inactive'}:
            messages.error(request, 'Vui lòng chọn trạng thái công khai hoặc riêng tư.')
        elif title:
            next_order = (
                chapter.lessons.order_by('-order', '-id')
                .values_list('order', flat=True)
                .first()
                or 0
            ) + 1
            Lesson.objects.create(
                chapter=chapter,
                title=title,
                order=next_order,
                video_url=video_url,
                content=content,
                attachment=attachment,
                status=status,
            )
            messages.success(request, 'Thêm bài học mới thành công!')
        else:
            messages.error(request, 'Tiêu đề bài học không được để trống.')
    return redirect('course_detail_instructor', course_id=course_id)


@login_required
def delete_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, chapter__course__instructor=request.user)
    course_id = lesson.chapter.course.id
    lesson.delete()
    messages.success(request, 'Đã xóa bài học thành công!')
    return redirect('course_detail_instructor', course_id=course_id)

@login_required
def teacher_students_view(request):
    # Lấy các khóa học do giảng viên hiện tại tạo ra
    teacher_courses = Course.objects.filter(instructor=request.user)
    
    # Lấy danh sách học viên đăng ký vào các khóa học của giảng viên này
    enrollments = Enrollment.objects.filter(course__in=teacher_courses).select_related('student', 'course')
    
    context = {
        'enrollments': enrollments,
    }
    return render(request, 'app/teacher_students.html', context)

@login_required
def teacher_course_list_for_students(request):
    # Chỉ Admin cao nhất (superuser) mới thấy tất cả. Giảng viên (kể cả có is_staff) chỉ thấy khóa của mình.
    if request.user.is_superuser:
        courses = Course.objects.all()
    else:
        courses = Course.objects.filter(instructor=request.user)
        
    context = {
        'courses': courses,
    }
    return render(request, 'app/teacher_course_list_for_students.html', context)

@login_required
def course_students_detail(request, course_id):
    # Chỉ Superuser mới được xem mọi khóa. Giảng viên bắt buộc phải khớp instructor=request.user
    if request.user.is_superuser:
        course = get_object_or_404(Course, id=course_id)
    else:
        course = get_object_or_404(Course, id=course_id, instructor=request.user)
    
    enrollments = Enrollment.objects.filter(course=course).select_related('student')
    
    context = {
        'course': course,
        'enrollments': enrollments,
    }
    return render(request, 'app/course_students_detail.html', context)

def teacher_analytics_view(request):
    my_courses = Course.objects.filter(instructor=request.user)

    total_courses = my_courses.count()
    enrollments = Enrollment.objects.filter(course__in=my_courses)
    total_enrollments = enrollments.count()
    total_students = enrollments.values('student_id').distinct().count()
    total_lessons = Lesson.objects.filter(chapter__course__in=my_courses).count()

    # Danh sách khóa học kèm số lượng học viên
    course_stats = my_courses.annotate(
        student_count=Count('enrollments'),
        avg_progress=Avg('enrollments__progress'),
    ).order_by('-student_count', 'title')

    # 1. Khóa học có nhiều học viên nhất (Tự động)
    top_course_by_students = course_stats.order_by('-student_count').first()

    total_records = total_enrollments
    completed_count = enrollments.filter(
        Q(status='COMPLETED') | Q(progress__gte=100)
    ).count()
    in_progress_count = enrollments.filter(
        progress__gt=0,
        progress__lt=100,
    ).exclude(status='COMPLETED').count()
    not_started_count = total_records - completed_count - in_progress_count

    if total_records:
        avg_completion_rate = round(enrollments.aggregate(
            average=Avg('progress')
        )['average'] or 0, 1)
        completed_percent = round(completed_count * 100 / total_records)
        in_progress_percent = round(in_progress_count * 100 / total_records)
        not_started_percent = 100 - completed_percent - in_progress_percent
    else:
        avg_completion_rate = 0.0
        completed_percent = 0
        in_progress_percent = 0
        not_started_percent = 100

    today = timezone.localdate()
    month_index = today.year * 12 + today.month - 1
    trend_months = []
    for offset in range(5, -1, -1):
        bucket_index = month_index - offset
        bucket_year, zero_based_month = divmod(bucket_index, 12)
        trend_months.append(date(bucket_year, zero_based_month + 1, 1))

    trend_start = trend_months[0]
    enrollments_by_month = {
        date(row['bucket'].year, row['bucket'].month, 1): row['total']
        for row in enrollments.filter(
            created_at__date__gte=trend_start,
            created_at__date__lte=today,
        ).annotate(bucket=TruncMonth('created_at')).values('bucket').annotate(
            total=Count('id')
        )
    }
    max_month_enrollments = max(enrollments_by_month.values(), default=0)
    enrollment_trend = [
        {
            'label': f'T{month.month:02d}',
            'month_label': month.strftime('%m/%Y'),
            'value': enrollments_by_month.get(month, 0),
            'height': round(
                enrollments_by_month.get(month, 0) * 100 / max_month_enrollments
            ) if max_month_enrollments else 0,
        }
        for month in trend_months
    ]

    total_interactions = LessonProgress.objects.filter(
        lesson__chapter__course__in=my_courses
    ).count()

    context = {
        'total_courses': total_courses,
        'total_students': total_students,
        'total_enrollments': total_enrollments,
        'total_lessons': total_lessons,
        'course_stats': course_stats,
        'top_course_by_students': top_course_by_students,
        'avg_completion_rate': avg_completion_rate,
        'total_interactions': total_interactions,
        'completed_percent': completed_percent,
        'in_progress_percent': in_progress_percent,
        'not_started_percent': not_started_percent,
        'enrollment_trend': enrollment_trend,
    }
    return render(request, 'app/teacher_analytics.html', context)

@instructor_only
def teacher_lessons_view(request):
    my_courses = Course.objects.filter(instructor=request.user)
    lessons = Lesson.objects.filter(chapter__course__in=my_courses).select_related(
        'chapter', 'chapter__course'
    ).order_by(
        'chapter__course__title',
        'chapter__course_id',
        'chapter__order',
        'chapter_id',
        'order',
        'id',
    )

    # Lọc theo từ khóa tìm kiếm
    search_query = request.GET.get('q', '').strip()
    if search_query:
        lessons = lessons.filter(title__icontains=search_query)

    # Lọc theo khóa học
    course_filter = request.GET.get('course', '')
    if course_filter:
        lessons = lessons.filter(chapter__course_id=course_filter)

    # Lọc theo trạng thái chính xác
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        lessons = lessons.filter(status='active')
    elif status_filter == 'inactive':
        lessons = lessons.filter(status='inactive')

    context = {
        'lessons': lessons,
        'my_courses': my_courses,
        'search_query': search_query,
        'selected_course': course_filter,
        'selected_status': status_filter,
    }
    return render(request, 'app/teacher_lessons.html', context)

@instructor_only
def add_lesson_view(request, course_id):
    # Lấy khóa học tương ứng
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        duration = request.POST.get('duration', 15) # Lấy thời lượng do giảng viên nhập
        chapter_id = request.POST.get('chapter_id')
        
        # Tạo bài giảng mới: created_at sẽ tự động nhận thời gian thực hiện tại
        Lesson.objects.create(
            chapter_id=chapter_id,
            title=title,
            duration=duration,
            status='active'
        )
        return redirect('teacher_lessons')
        
    return render(request, 'app/add_lesson.html', {'course': course})

def add_lesson_view(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    if request.method == 'POST':
        title = request.POST.get('title')
        video_url = request.POST.get('video_url', '')
        duration = request.POST.get('duration', 15) # Lấy số phút do giảng viên nhập vào form

        Lesson.objects.create(
            chapter=chapter,
            title=title,
            video_url=video_url,
            duration=duration, # Lưu thời lượng thực tế
            status='active'
        )
    return redirect('course_detail_instructor', course_id=chapter.course.id)
@instructor_only
def edit_lesson(request, lesson_id):
    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        chapter__course__instructor=request.user,
    )
    
    if request.method == 'POST':
        status = request.POST.get('status')
        if status not in {'active', 'inactive'}:
            messages.error(request, 'Vui lòng chọn trạng thái công khai hoặc riêng tư.')
            return render(request, 'app/edit_lesson.html', {'lesson': lesson})
        attachment = request.FILES.get('attachment')
        if attachment and not is_supported_lesson_attachment(attachment):
            messages.error(
                request,
                'Tệp bài giảng phải có định dạng PDF, Word (.doc/.docx) hoặc PowerPoint (.ppt/.pptx).',
            )
            return render(request, 'app/edit_lesson.html', {'lesson': lesson})
        previous_attachment = lesson.attachment
        lesson.title = request.POST.get('title', lesson.title).strip()
        lesson.duration = request.POST.get('duration', lesson.duration)
        lesson.status = status
        lesson.video_url = request.POST.get('video_url', lesson.video_url)
        lesson.content = request.POST.get('content', lesson.content)
        if attachment:
            lesson.attachment = attachment
        lesson.save()
        if (
            attachment
            and previous_attachment
            and previous_attachment.name != lesson.attachment.name
        ):
            previous_attachment.delete(save=False)
        messages.success(request, 'Đã cập nhật bài giảng.')
        return redirect('teacher_lessons')
        
    context = {
        'lesson': lesson
    }
    return render(request, 'app/edit_lesson.html', context)

@instructor_only
def teacher_assignments_view(request):
    # Lấy các khóa học do giảng viên hiện tại quản lý
    my_courses = Course.objects.filter(instructor=request.user)
    
    # Lấy danh sách bài tập thuộc các khóa học của giảng viên
    assignments = Assignment.objects.filter(course__in=my_courses).select_related('course').order_by('-id')

    # Tìm kiếm theo tên bài tập
    search_query = request.GET.get('q', '').strip()
    if search_query:
        assignments = assignments.filter(title__icontains=search_query)

    # Lọc theo khóa học
    course_filter = request.GET.get('course', '')
    if course_filter:
        assignments = assignments.filter(course_id=course_filter)

    # Lọc theo trạng thái
    status_filter = request.GET.get('status', '')
    if status_filter:
        assignments = assignments.filter(status=status_filter)

    context = {
        'assignments': assignments,
        'my_courses': my_courses,
        'search_query': search_query,
        'selected_course': course_filter,
        'selected_status': status_filter,
    }
    return render(request, 'app/teacher_assignments.html', context)

@login_required
def teacher_quizzes(request):
    # Lấy danh sách khóa học để đưa vào ô lọc select
    my_courses = Course.objects.all()  # Hoặc lọc theo giáo viên: Course.objects.filter(instructor=request.user)
    
    quizzes = Quiz.objects.all().order_by('-created_at')

    # Xử lý tìm kiếm theo tên
    search_query = request.GET.get('q', '')
    if search_query:
        quizzes = quizzes.filter(title__icontains=search_query)

    # Lọc theo khóa học
    selected_course = request.GET.get('course', '')
    if selected_course:
        quizzes = quizzes.filter(course_id=selected_course)

    # Lọc theo trạng thái
    selected_status = request.GET.get('status', '')
    if selected_status:
        quizzes = quizzes.filter(status=selected_status)

    context = {
        'quizzes': quizzes,
        'my_courses': my_courses,
        'search_query': search_query,
        'selected_course': selected_course,
        'selected_status': selected_status,
    }
    return render(request, 'app/teacher_quizzes.html', context)