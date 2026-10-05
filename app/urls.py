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
    path('learning/',views.learning,name='learning'),
    path('profile/',views.profile,name='profile'),
    # Thêm: endpoint nhận yêu cầu đăng ký theo ID khóa học.
    path('courses/<int:course_id>/enroll/', views.enroll_course, name='enroll-course'),
    path('teacher_dashboard/',views.teacher,name='teacher_dashboard'),
    path('teacher_courses/',views.teacher,name='teacher_courses'),
]
