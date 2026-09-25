from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Category, Course, Chapter, Lesson

# Đăng ký User Custom
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Thông tin bổ sung', {'fields': ('role', 'avatar', 'bio')}),
    )
    list_display = ('username', 'email', 'role', 'is_staff')

# Đăng ký Category với tính năng tự tạo slug
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'parent')
    prepopulated_fields = {'slug': ('name',)}

# Đăng ký các model còn lại
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'category', 'price', 'is_published')
    prepopulated_fields = {'slug': ('title',)}

admin.site.register(Chapter)
admin.site.register(Lesson)