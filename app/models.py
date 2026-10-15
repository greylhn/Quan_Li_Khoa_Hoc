from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser, BaseUserManager
from urllib.parse import parse_qs, urlencode, urlsplit
import re
#from django.contrib.auth.forms import UserCreationForm


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, username=None, email=None, password=None, **extra_fields):
        if username is None and email is None:
            raise ValueError('A username or email must be provided.')

        if username is None:
            username = email

        if email is None:
            email = username

        extra_fields.setdefault('role', User.Role.STUDENT)
        user = self.model(username=username, email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username=username, email=email, password=password, **extra_fields)


# Create your models here.
# 3 vai tro trong he thong 
class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Quan Tri Vien' # admin
        INSTRUCTOR = 'INSTRUCTOR' , 'Giang Vien'
        STUDENT = 'STUDENT' , 'Hoc Sinh'
    role = models.CharField(max_length=20,choices=Role.choices,default=Role.STUDENT)
    
    # ĐÃ CHỈNH SỬA: Thêm upload_to='teacher/' để lưu ảnh đại diện vào đúng thư mục teacher
    avatar = models.ImageField(upload_to='teacher/', null=True, blank=True)
    
    bio = models.TextField(blank=True,null=True)
    objects = UserManager()

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

# KHOA HOC
class Course(models.Model):
    # tieu de 
    title = models.CharField(max_length=200,verbose_name="Tên Khóa Học")
    # slug 
    slug = models.SlugField(max_length=200,unique=True)
    description = models.TextField(verbose_name="Mô tả chi tiết")
    
    # ĐÃ CHỈNH SỬA: Loại bỏ dòng trùng lặp thumbnail, giữ lại cấu hình upload vào thư mục courses/
    thumbnail = models.ImageField(upload_to='courses/', null=True, blank=True)
    
    instructor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='courses_created',
        limit_choices_to={'role':User.Role.INSTRUCTOR},
        verbose_name="Giang Vien"
    )
    ished = models.BooleanField(default=False,verbose_name="Da xuat Ban")
    
    # ĐÃ CHỈNH SỬA: Loại bỏ dòng created_at bị trùng lặp ở phía trên
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

# CHUONG HOC 
class Chapter (models.Model) :
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='chapters'
    )
    title = models.CharField(max_length=200,verbose_name="Ten Chuong")
    order = models.PositiveIntegerField(default=1,verbose_name="Thu tu hien thi")

    class Meta :
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title}-Chương {self.order}: {self.title}"

# BAI HOC 
class Lesson(models.Model):
    class LessonType(models.TextChoices):
        VIDEO = "VIDEO", 'Video'
        ARTICLE = "ARTICLE", 'Bài đọc'
        DOCUMENT = "DOCUMENT", 'Tài liệu PDF/FILE'

    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name="lessons"
    )
    title = models.CharField(max_length=200, verbose_name="Tên bài học")
    lesson_type = models.CharField(
        max_length=10,
        choices=LessonType.choices,
        default=LessonType.VIDEO
    )
    duration = models.PositiveIntegerField(default=15, verbose_name="Thời lượng (phút)")
    created_at = models.DateTimeField(auto_now_add=True)  # Tự động lấy giờ hiện tại khi tạo

    video_url = models.URLField(blank=True, null=True, verbose_name="Link VIDEO (...)")
    content = models.TextField(blank=True, null=True, verbose_name="Nội dung văn bản")
    attachment = models.FileField(upload_to="lessons/documents/", blank=True, null=True, verbose_name="File đính kèm")
    order = models.PositiveIntegerField(default=1, verbose_name="Thứ tự bài học")
    is_preview = models.BooleanField(default=False, verbose_name='Cho phép học thử')
    
    status = models.CharField(
        max_length=20,
        choices=[('active', 'Đã công khai'), ('inactive', 'Bản nháp')],
        default='active',
        verbose_name="Trạng thái"
    )

    class UnlockType(models.TextChoices):
        SEQUENTIAL = "SEQUENTIAL", "Hoàn thành bài học trước"
        STUDY_TIME = "STUDY_TIME", "Hoàn thành hoặc học đủ phút bài trước"

    unlock_type = models.CharField(
        max_length=20,
        choices=UnlockType.choices,
        default=UnlockType.SEQUENTIAL,
        verbose_name="Cách mở bài"
    )

    unlock_required_minutes = models.PositiveIntegerField(
        default=5,
        verbose_name="Số phút cần học ở bài trước"
    )

    required_watch_percent = models.PositiveIntegerField(
        default=50,
        verbose_name="Phần trăm cần học để hoàn thành"
    )

    class Meta:
        ordering = ['order', 'id']

    @property
    def embed_video_url(self):
        if not self.video_url:
            return ""

        parsed_url = urlsplit(self.video_url)
        hostname = (parsed_url.hostname or "").lower().rstrip(".")
        youtube_hosts = {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "music.youtube.com",
            "youtu.be",
            "www.youtu.be",
            "youtube-nocookie.com",
            "www.youtube-nocookie.com",
        }

        if hostname not in youtube_hosts:
            return self.video_url

        path_parts = [part for part in parsed_url.path.split("/") if part]
        query = parse_qs(parsed_url.query)
        video_id = None

        if hostname.endswith("youtu.be"):
            video_id = path_parts[0] if path_parts else None
        elif parsed_url.path.rstrip("/") == "/watch":
            video_id = query.get("v", [None])[0]
        elif len(path_parts) >= 2 and path_parts[0] in {
            "embed", "shorts", "live", "v"
        }:
            video_id = path_parts[1]

        playlist_id = query.get("list", [None])[0]
        if not video_id and playlist_id and re.fullmatch(r"[A-Za-z0-9_-]+", playlist_id):
            return "https://www.youtube.com/embed/videoseries?" + urlencode({"list": playlist_id})

        if not video_id or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            return ""

        embed_query = {}
        start = query.get("start", [None])[0]
        if start and start.isdigit():
            embed_query["start"] = start

        embed_url = f"https://www.youtube.com/embed/{video_id}"
        if embed_query:
            embed_url += "?" + urlencode(embed_query)
        return embed_url

    @property
    def is_youtube_video(self):
        if not self.video_url:
            return False
        hostname = (urlsplit(self.video_url).hostname or "").lower().rstrip(".")
        return hostname in {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "music.youtube.com",
            "youtu.be",
            "www.youtu.be",
            "youtube-nocookie.com",
            "www.youtube-nocookie.com",
        }

    def __str__(self):
        return f"{self.chapter.title}-Bài {self.order}: {self.title}"
    
class Enrollment(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('ACTIVE', 'Đang học'),
            ('COMPLETED', 'Hoàn thành'),
            ('PAUSED', 'Tạm dừng'),
        ],
        default='ACTIVE'
    )
    progress = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'course')

    def __str__(self):
        return f"{self.student.username} - {self.course.title}"

class SaveCourse(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="savecourse"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='savecourse'
    )
    saved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('student','course')
    def __str__(self):
        return f"{self.student.username} - {self.course.title}"

class LessonProgress(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="lesson_progresses"
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="progresses"
    )
    watched_seconds = models.PositiveIntegerField(default=0)
    watched_percent = models.FloatField(default=0)
    video_watched_seconds = models.PositiveIntegerField(default=0)
    video_duration_seconds = models.FloatField(null=True, blank=True)
    last_video_position = models.FloatField(null=True, blank=True)
    last_video_activity_at = models.DateTimeField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "lesson"],
                name="unique_user_lesson_progress"
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.lesson.title}"

class LearningActivity(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="learning_activities"
    )
    date = models.DateField()
    minutes = models.PositiveIntegerField(default=0)
    study_seconds = models.PositiveIntegerField(default=0)
    lessons_completed = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "date"],
                name="unique_user_learning_date"
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.date}"

class UserStreak(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="streak"
    )
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.current_streak} ngày"

class Assignment(models.Model):
    title = models.CharField(max_length=255)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    deadline = models.DateTimeField()
    status = models.CharField(
        max_length=20, 
        choices=[('active', 'Đang diễn ra'), ('closed', 'Đã kết thúc')], 
        default='active'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Quiz(models.Model):
    STATUS_CHOICES = (
        ('active', 'Đang diễn ra'),
        ('closed', 'Đã kết thúc'),
    )

    title = models.CharField(max_length=255, verbose_name="Tên bài kiểm tra")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes', verbose_name="Khóa học")
    duration = models.PositiveIntegerField(default=60, verbose_name="Thời gian làm (phút)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="Trạng thái")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")

    def __str__(self):
        return self.title