from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Course, Chapter, Lesson
from .models import*
# Register your models here
admin.site.site_header = "Quản Trị Hệ Thống Khóa Học"
admin.site.site_title = "Admin Khóa Học"
admin.site.index_title = "Bảng điều khiển quản trị"
# 3. Inline Chương học ngay trong Khóa học
class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 1
# 4. Quản lý Khóa học
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'ished', 'created_at')
    list_filter = ('ished','created_at')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ChapterInline]
    list_editable = ('ished',)
# 5. Inline Bài học ngay trong Chương học
class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 1
# 6. Quản lý Chương học
@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)
    search_fields = ('title',)
    inlines = [LessonInline]
# 7. Quản lý Bài học
@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'chapter', 'lesson_type', 'order', 'is_preview')
    list_filter = ('lesson_type', 'is_preview', 'chapter__course')
    search_fields = ('title', 'content')
# 8. Quản lý Custom User 
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Thông tin bổ sung', {'fields': ('role', 'avatar', 'bio')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Thông tin bổ sung', {'fields': ('email', 'role', 'avatar', 'bio')}),
    )