from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name="home"),
    path('register/', views.registerPage, name='register'),
    path('login/', views.loginPage, name='login'),
    path('logout/', views.logoutPage, name='logout'),
    path('term/', views.term, name='term'),
    path('courses/', views.courses, name='courses'),
    path('search/', views.search, name='search'),
    path('detail-course/', views.detail_course, name='detail-course'),
    path('profile/', views.profile, name='profile'),
    path('my-courses/', views.my_courses, name='my_courses'),
    # Thêm: endpoint nhận yêu cầu đăng ký theo ID khóa học.
    path('courses/<int:course_id>/enroll/', views.enroll_course, name='enroll_course'),
    path('saved-course/<int:course_id>/', views.saved_course, name='saved_course'),
    path('saved-course/', views.saved_courses, name='saved_courses'),
    path(
        'learning/<int:course_id>/',
        views.learning,
        name='learning'
    ),
    path(
        'learning/<int:course_id>/lessons/<int:lesson_id>/study/',
        views.track_lesson_study,
        name='track_lesson_study',
    ),
    path(
        'learning/<int:course_id>/lessons/<int:lesson_id>/video-progress/',
        views.track_video_progress,
        name='track_video_progress',
    ),
    path(
        'learning/<int:course_id>/lessons/<int:lesson_id>/record-completion/',
        views.record_lesson_completion,
        name='record_lesson_completion',
    ),
    path(
        'dashboard/',
        views.admin_dashboard,
        name='admin_dashboard'
    ),

    path(
        'dashboard/create-instructor/',
        views.create_instructor,
        name='create_instructor'
    ),
    path(
        'dashboard/students/',
        views.admin_students,
        name='admin_students'
    ),

    path(
        'dashboard/instructors/',
        views.admin_instructors,
        name='admin_instructors'
    ),

    path(
        'dashboard/courses/',
        views.admin_courses,
        name='admin_courses'
    ),
    path(
        'instructor/dashboard/',
        views.teacher_dashboard,
        name='teacher_dashboard'
    ),
    path(
        'instructor/dashboard/teacher_courses',
        views.teacher_courses,
        name='teacher_courses'
    ),
    path(
        'instructor/dashboard/create_course',
        views.create_course,
        name='create_course'
    ),
    path(
        'teacher/course/edit/<int:course_id>/',
        views.edit_course, 
        name='edit_course'
    ),
    path(
        'teacher/course/delete/<int:course_id>/',
        views.delete_course,
        name='delete_course'
    ),
    path(
        'course/add/', 
        views.create_course, 
        name='add_course'
    ),
    
    # === BỔ SUNG: URL Chi tiết khóa học cho giảng viên ===
    path(
        'instructor/course/<int:course_id>/', 
        views.course_detail_instructor, 
        name='course_detail_instructor'
    ),
    path('teacher/students/', views.teacher_students_view, name='teacher_students'),

    # URL Thêm/Xóa Chương & Bài học
    path('instructor/chapter/add/<int:course_id>/', views.add_chapter, name='add_chapter'),
    path('instructor/chapter/delete/<int:chapter_id>/', views.delete_chapter, name='delete_chapter'),
    path('instructor/lesson/add/<int:chapter_id>/', views.add_lesson, name='add_lesson'),
    path('instructor/lesson/delete/<int:lesson_id>/', views.delete_lesson, name='delete_lesson'),
    # Thêm dòng này vào danh sách urlpatterns:
    path('teacher/students/courses/', views.teacher_course_list_for_students, name='teacher_course_list_for_students'),
    # Và đường dẫn chi tiết danh sách học sinh của khóa học (nếu bạn chưa thêm):
    path('teacher/course/<int:course_id>/students/', views.course_students_detail, name='course_students_detail'),
    path('teacher/analytics/', views.teacher_analytics_view, name='teacher_analytics'),
    path('teacher/lessons/', views.teacher_lessons_view, name='teacher_lessons'),
    path('instructor/lesson/edit/<int:lesson_id>/', views.edit_lesson, name='edit_lesson'),
    path('teacher/assignments/', views.teacher_assignments_view, name='teacher_assignments'),
    path('teacher/quizzes/', views.teacher_quizzes, name='teacher_quizzes'),
]
