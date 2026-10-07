from django.urls import path
from .import views
urlpatterns = [
    path('', views.home,name="home"),
    path('register/',views.registerPage,name='register'),
    path('login/',views.loginPage,name='login'),
    path('logout/', views.logoutPage, name='logout'),
    path('term/',views.term,name='term'),
    path('courses/',views.courses,name='courses'),
    path('search/',views.search,name='search'),
    path('detail-course/',views.detail_course,name='detail-course'),
    path('profile/',views.profile,name='profile'),
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
]
