from datetime import timedelta

from django.utils import timezone
from django.db import transaction

from .models import (
    Lesson,
    LessonProgress,
    LearningActivity,
    UserStreak,
    Enrollment,
)


# =========================================================
# 1. LẤY TẤT CẢ BÀI HỌC THEO THỨ TỰ
# =========================================================

def get_course_lessons(course):

    return list(
        Lesson.objects
        .filter(
            chapter__course=course
        )
        .select_related(
            "chapter"
        )
        .order_by(
            "chapter__order",
            "order"
        )
    )


# =========================================================
# 2. TÌM BÀI HỌC TRƯỚC
# =========================================================

def get_previous_lesson(lesson):

    lessons = get_course_lessons(
        lesson.chapter.course
    )

    for index, current_lesson in enumerate(lessons):

        if current_lesson.id == lesson.id:

            if index == 0:
                return None

            return lessons[index - 1]

    return None


def get_next_lesson(lesson):

    lessons = get_course_lessons(
        lesson.chapter.course
    )

    for index, current_lesson in enumerate(lessons):

        if current_lesson.id == lesson.id:

            if index + 1 < len(lessons):
                return lessons[index + 1]

            return None

    return None


# =========================================================
# 3. KIỂM TRA BÀI ĐÃ ĐƯỢC MỞ KHÓA CHƯA
# =========================================================

def is_lesson_unlocked(user, lesson):

    if lesson is None:
        return False

    # Bài cho phép học thử
    if lesson.is_preview:
        return True

    previous_lesson = get_previous_lesson(
        lesson
    )

    # Bài đầu tiên
    if previous_lesson is None:
        return True

    previous_progress = (
        LessonProgress.objects
        .filter(
            user=user,
            lesson=previous_lesson
        )
        .first()
    )

    # Chưa từng học bài trước
    if previous_progress is None:
        return False

    # Hoàn thành bài trước luôn mở bài tiếp theo.
    if previous_progress.completed:
        return True

    # Bài kế tiếp cũng có thể mở khi người học tích lũy đủ thời gian
    # trên bài trước, kể cả khi chưa đạt ngưỡng hoàn thành bài.
    if lesson.unlock_type == Lesson.UnlockType.STUDY_TIME:
        required_seconds = lesson.unlock_required_minutes * 60
        if previous_lesson.lesson_type == Lesson.LessonType.VIDEO:
            studied_seconds = previous_progress.video_watched_seconds
        else:
            studied_seconds = previous_progress.watched_seconds
        return studied_seconds >= required_seconds

    return False


# =========================================================
# 4. CẬP NHẬT TIẾN ĐỘ KHÓA HỌC
# =========================================================

def update_course_progress(
    user,
    course
):

    total_lessons = (
        Lesson.objects
        .filter(
            chapter__course=course
        )
        .count()
    )

    completed_lessons = (
        LessonProgress.objects
        .filter(
            user=user,
            lesson__chapter__course=course,
            completed=True
        )
        .count()
    )

    if total_lessons == 0:
        progress_percent = 0
    else:
        progress_percent = round(
            completed_lessons
            / total_lessons
            * 100
        )

    enrollment = (
        Enrollment.objects
        .filter(
            student=user,
            course=course
        )
        .first()
    )

    if enrollment:

        enrollment.progress = progress_percent

        if progress_percent >= 100:
            enrollment.status = "COMPLETED"

        enrollment.save(
            update_fields=[
                "progress",
                "status"
            ]
        )

    return progress_percent


# =========================================================
# 5. GHI NHẬN HOẠT ĐỘNG HỌC TRONG NGÀY
# =========================================================

def record_learning_activity(
    user,
    minutes=0,
    lesson_completed=False
):

    today = timezone.localdate()

    activity, _ = (
        LearningActivity.objects
        .get_or_create(
            user=user,
            date=today
        )
    )

    activity.minutes += minutes

    if lesson_completed:
        activity.lessons_completed += 1

    activity.save()

    return activity


def record_learning_time(user, seconds):
    """Accumulate study time and count a learning day after one minute."""
    if seconds <= 0:
        return None

    today = timezone.localdate()
    with transaction.atomic():
        activity, _ = LearningActivity.objects.get_or_create(
            user=user,
            date=today,
        )
        activity = LearningActivity.objects.select_for_update().get(pk=activity.pk)
        previous_whole_minutes = activity.study_seconds // 60
        activity.study_seconds += seconds
        activity.minutes += activity.study_seconds // 60 - previous_whole_minutes
        activity.save(update_fields=['study_seconds', 'minutes'])

    if activity.study_seconds >= 60:
        update_streak(user)

    return activity


def complete_lesson_progress(user, course, lesson, progress):
    """Save one completion and update its course, activity, and streak totals."""
    with transaction.atomic():
        progress = LessonProgress.objects.select_for_update().get(pk=progress.pk)
        if progress.completed:
            return False

        progress.completed = True
        progress.watched_percent = 100
        progress.completed_at = timezone.now()
        progress.save(update_fields=['completed', 'watched_percent', 'completed_at'])

        update_course_progress(user, course)
        update_streak(user)
        record_learning_activity(user, lesson_completed=True)
    return True


# =========================================================
# 6. CẬP NHẬT STREAK
# =========================================================

def update_streak(user):

    today = timezone.localdate()

    with transaction.atomic():
        streak, _ = UserStreak.objects.get_or_create(user=user)
        streak = UserStreak.objects.select_for_update().get(pk=streak.pk)

        # Hôm nay đã tính streak rồi.
        if streak.last_activity_date == today:
            return streak

        # Hôm qua có học thì nối chuỗi; nếu nghỉ ít nhất một ngày thì bắt đầu lại.
        if streak.last_activity_date == today - timedelta(days=1):
            streak.current_streak += 1
        else:
            streak.current_streak = 1

        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak

        streak.last_activity_date = today
        streak.save()

    return streak


def get_streak_status(user):
    """Return the current streak, clearing it after a full missed day."""
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    streak, _ = UserStreak.objects.get_or_create(user=user)

    if (
        streak.last_activity_date
        and streak.last_activity_date < yesterday
        and streak.current_streak != 0
    ):
        streak.current_streak = 0
        streak.save(update_fields=['current_streak'])

    return streak
