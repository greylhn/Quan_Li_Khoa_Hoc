import tempfile

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .models import (
    Chapter,
    Course,
    Enrollment,
    LearningActivity,
    Lesson,
    LessonProgress,
    SaveCourse,
)


class RoleAndAccessTests(TestCase):
    def test_create_superuser_sets_admin_role(self):
        user_model_class = get_user_model()
        admin_user = user_model_class.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='test-password',
        )

        self.assertEqual(admin_user.role, user_model_class.Role.ADMIN)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)

    def test_home_redirects_admin_to_admin_dashboard(self):
        user_model_class = get_user_model()
        admin_user = user_model_class.objects.create_superuser(
            username='admin-home',
            email='admin-home@example.com',
            password='test-password',
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse('home'))

        self.assertRedirects(response, reverse('admin_dashboard'))


class HomePageContentTests(TestCase):
    def setUp(self):
        user_model_class = get_user_model()
        self.instructor = user_model_class.objects.create_user(
            username='home-instructor',
            email='home-instructor@example.com',
            password='test-password',
            role=user_model_class.Role.INSTRUCTOR,
        )
        self.student = user_model_class.objects.create_user(
            username='home-student',
            email='home-student@example.com',
            password='test-password',
            role=user_model_class.Role.STUDENT,
        )
        self.public_course = Course.objects.create(
            title='Public Home Course',
            slug='public-home-course',
            description='Visible on the home page.',
            instructor=self.instructor,
            ished=True,
        )
        public_chapter = Chapter.objects.create(
            course=self.public_course,
            title='Public chapter',
        )
        Lesson.objects.create(
            chapter=public_chapter,
            title='Public lesson',
            status='active',
        )
        Lesson.objects.create(
            chapter=public_chapter,
            title='Draft lesson',
            status='inactive',
        )
        self.draft_course = Course.objects.create(
            title='Draft Home Course',
            slug='draft-home-course',
            description='Must not be presented as public.',
            instructor=self.instructor,
            ished=False,
        )
        draft_chapter = Chapter.objects.create(
            course=self.draft_course,
            title='Draft chapter',
        )
        Lesson.objects.create(
            chapter=draft_chapter,
            title='Draft course lesson',
            status='active',
        )

    def test_home_shows_public_counts_and_student_courses_only(self):
        Enrollment.objects.create(
            student=self.student,
            course=self.public_course,
            progress=35,
        )
        Enrollment.objects.create(
            student=self.student,
            course=self.draft_course,
        )
        self.client.force_login(self.student)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['public_course_count'], 1)
        self.assertEqual(response.context['public_lesson_count'], 1)
        self.assertEqual(response.context['instructor_count'], 1)
        self.assertEqual(
            [enrollment.course for enrollment in response.context['student_enrollments']],
            [self.public_course],
        )
        self.assertContains(response, 'Public Home Course')
        self.assertNotContains(response, 'Draft Home Course')
        self.assertContains(response, 'Học theo cách của bạn')
        self.assertContains(response, 'Video · Bài đọc · Tài liệu')
        self.assertContains(response, 'aria-label="Tìm khóa học"')
        self.assertNotContains(response, 'Duy trì Streak')


class AdminDashboardAnalyticsTests(TestCase):
    def setUp(self):
        user_model_class = get_user_model()
        self.admin = user_model_class.objects.create_superuser(
            username='analytics-admin',
            email='analytics-admin@example.com',
            password='test-password',
        )
        self.instructor = user_model_class.objects.create_user(
            username='analytics-instructor',
            email='analytics-instructor@example.com',
            password='test-password',
            role=user_model_class.Role.INSTRUCTOR,
        )
        self.students = [
            user_model_class.objects.create_user(
                username=f'analytics-student-{index}',
                email=f'analytics-student-{index}@example.com',
                password='test-password',
                role=user_model_class.Role.STUDENT,
            )
            for index in range(2)
        ]
        self.course = Course.objects.create(
            title='Analytics Course',
            slug='analytics-course',
            description='Course used for admin dashboard analytics tests.',
            instructor=self.instructor,
            ished=True,
        )
        for student in self.students:
            Enrollment.objects.create(student=student, course=self.course)
        self.client.force_login(self.admin)

    def test_dashboard_shows_period_stats_and_popular_course(self):
        response = self.client.get(reverse('admin_dashboard'), {'period': '7d'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['timeframe'], '7d')
        self.assertEqual(response.context['period_enrollments'], 2)
        self.assertEqual(sum(response.context['chart_values']), 2)
        self.assertEqual(response.context['popular_courses'][0].student_count, 2)
        self.assertEqual(response.context['published_courses'], 1)
        self.assertEqual(response.context['total_students'], 2)

    def test_dashboard_uses_default_period_for_invalid_filter(self):
        response = self.client.get(reverse('admin_dashboard'), {'period': 'invalid'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['timeframe'], '30d')

    def test_dashboard_builds_twelve_month_chart(self):
        response = self.client.get(reverse('admin_dashboard'), {'period': '12m'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['timeframe'], '12m')
        self.assertEqual(len(response.context['chart_labels']), 12)
        self.assertEqual(len(response.context['chart_values']), 12)
        self.assertEqual(sum(response.context['chart_values']), 2)


class TeacherDashboardTests(TestCase):
    def test_dashboard_uses_larger_course_summary_counts(self):
        user_model_class = get_user_model()
        instructor = user_model_class.objects.create_user(
            username='dashboard-instructor',
            email='dashboard-instructor@example.com',
            password='test-password',
            role=user_model_class.Role.INSTRUCTOR,
        )
        course = Course.objects.create(
            title='Instructor Course',
            slug='instructor-course',
            description='A course for the instructor dashboard.',
            instructor=instructor,
            ished=True,
        )
        chapter = Chapter.objects.create(course=course, title='First chapter')
        Lesson.objects.create(chapter=chapter, title='First lesson')
        self.client.force_login(instructor)

        response = self.client.get(reverse('teacher_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_lessons'], 1)
        self.assertEqual(response.context['courses'][0].lesson_count, 1)


class InstructorProfileTests(TestCase):
    def setUp(self):
        user_model_class = get_user_model()
        self.instructor = user_model_class.objects.create_user(
            username='profile-instructor',
            email='profile-instructor@example.com',
            password='test-password',
            role=user_model_class.Role.INSTRUCTOR,
            first_name='Tên cũ',
        )
        self.client.force_login(self.instructor)

    def test_instructor_can_update_own_profile(self):
        response = self.client.post(
            reverse('profile'),
            {
                'full_name': 'Tên giảng viên mới',
                'email': 'updated-instructor@example.com',
                'bio': 'Giới thiệu giảng viên',
            },
        )

        self.assertRedirects(response, reverse('profile'))
        self.instructor.refresh_from_db()
        self.assertEqual(self.instructor.first_name, 'Tên giảng viên mới')
        self.assertEqual(self.instructor.email, 'updated-instructor@example.com')
        self.assertEqual(self.instructor.username, 'updated-instructor@example.com')
        self.assertEqual(self.instructor.bio, 'Giới thiệu giảng viên')

    def test_profile_update_rejects_duplicate_email(self):
        user_model_class = get_user_model()
        user_model_class.objects.create_user(
            username='another-instructor',
            email='already-used@example.com',
            password='test-password',
            role=user_model_class.Role.INSTRUCTOR,
        )

        response = self.client.post(
            reverse('profile'),
            {
                'full_name': 'Tên giảng viên mới',
                'email': 'already-used@example.com',
                'bio': '',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Email này đã được tài khoản khác sử dụng.')
        self.instructor.refresh_from_db()
        self.assertEqual(self.instructor.first_name, 'Tên cũ')

    def test_profile_update_rejects_invalid_avatar(self):
        response = self.client.post(
            reverse('profile'),
            {
                'full_name': 'Tên giảng viên mới',
                'email': self.instructor.email,
                'bio': '',
                'avatar': SimpleUploadedFile('avatar.txt', b'not an image'),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('avatar', response.context['profile_form'].errors)
        self.instructor.refresh_from_db()
        self.assertEqual(self.instructor.first_name, 'Tên cũ')

    def test_student_can_update_own_profile(self):
        user_model_class = get_user_model()
        student = user_model_class.objects.create_user(
            username='profile-student',
            email='profile-student@example.com',
            password='test-password',
            role=user_model_class.Role.STUDENT,
        )
        self.client.force_login(student)

        response = self.client.post(
            reverse('profile'),
            {
                'full_name': 'Changed Student Name',
                'email': 'changed-student@example.com',
            },
        )

        self.assertRedirects(response, reverse('profile'))
        student.refresh_from_db()
        self.assertEqual(student.first_name, 'Changed Student Name')
        self.assertEqual(student.email, 'changed-student@example.com')
        self.assertEqual(student.username, 'changed-student@example.com')


class StudentProfileDashboardTests(TestCase):
    def setUp(self):
        user_model_class = get_user_model()
        self.instructor = user_model_class.objects.create_user(
            username='student-dashboard-instructor',
            email='student-dashboard-instructor@example.com',
            password='test-password',
            role=user_model_class.Role.INSTRUCTOR,
        )
        self.student = user_model_class.objects.create_user(
            username='student-dashboard-user',
            email='student-dashboard-user@example.com',
            password='test-password',
            role=user_model_class.Role.STUDENT,
        )
        self.active_course = Course.objects.create(
            title='Active Learning Course',
            slug='active-learning-course',
            description='Course currently in progress.',
            instructor=self.instructor,
            ished=True,
        )
        self.completed_course = Course.objects.create(
            title='Completed Learning Course',
            slug='completed-learning-course',
            description='Course already completed.',
            instructor=self.instructor,
            ished=True,
        )
        Lesson.objects.create(
            chapter=Chapter.objects.create(
                course=self.active_course,
                title='Active chapter',
            ),
            title='Completed lesson',
        )
        Enrollment.objects.create(
            student=self.student,
            course=self.active_course,
            status='ACTIVE',
            progress=40,
        )
        Enrollment.objects.create(
            student=self.student,
            course=self.completed_course,
            status='COMPLETED',
            progress=100,
        )
        LessonProgress.objects.create(
            user=self.student,
            lesson=self.active_course.chapters.first().lessons.first(),
            completed=True,
        )
        LearningActivity.objects.create(
            user=self.student,
            date='2026-10-14',
            study_seconds=3720,
        )
        self.client.force_login(self.student)

    def test_profile_displays_real_completion_history_and_study_time(self):
        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active_enrollments'].count(), 1)
        self.assertEqual(response.context['completed_courses_count'], 1)
        self.assertEqual(response.context['completed_lessons_count'], 1)
        self.assertEqual(response.context['study_hours'], 1)
        self.assertEqual(response.context['study_minutes_remainder'], 2)
        self.assertContains(response, 'Thông tin cá nhân')
        self.assertContains(response, 'Lưu hồ sơ')
        self.assertNotContains(response, 'Quản lý hồ sơ cá nhân')
        self.assertNotContains(response, self.completed_course.title)
        self.assertContains(response, '1 giờ 2 phút')

    def test_my_courses_page_separates_enrollments_from_profile(self):
        response = self.client.get(reverse('my_courses'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active_enrollments'].count(), 1)
        self.assertEqual(response.context['completed_enrollments'].count(), 1)
        self.assertContains(response, self.active_course.title)
        self.assertContains(response, self.completed_course.title)
        self.assertContains(response, reverse('profile'))

    def test_non_student_is_redirected_from_my_courses_to_profile(self):
        instructor = get_user_model().objects.create_user(
            username='my-courses-instructor',
            email='my-courses-instructor@example.com',
            password='test-password',
            role=get_user_model().Role.INSTRUCTOR,
        )
        self.client.force_login(instructor)

        response = self.client.get(reverse('my_courses'))

        self.assertRedirects(response, reverse('profile'))


class SavedCoursesPageTests(TestCase):
    def setUp(self):
        user_model_class = get_user_model()
        self.student = user_model_class.objects.create_user(
            username='saved-courses-student',
            email='saved-courses-student@example.com',
            password='test-password',
            role=user_model_class.Role.STUDENT,
        )
        self.instructor = user_model_class.objects.create_user(
            username='saved-courses-instructor',
            email='saved-courses-instructor@example.com',
            password='test-password',
            role=user_model_class.Role.INSTRUCTOR,
        )
        self.course = Course.objects.create(
            title='Saved Django Course',
            slug='saved-django-course',
            description='A course saved for later.',
            instructor=self.instructor,
            ished=True,
        )
        SaveCourse.objects.create(student=self.student, course=self.course)
        self.client.force_login(self.student)

    def test_saved_courses_page_is_standalone_from_profile(self):
        response = self.client.get(reverse('saved_courses'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Khóa học đã lưu')
        self.assertContains(response, self.course.title)
        self.assertContains(response, '1 khóa học')
        self.assertNotContains(response, 'Học viên PTIT')
        self.assertNotContains(response, 'Thống kê học tập')


class StudentCourseCatalogTests(TestCase):
    def setUp(self):
        user_model_class = get_user_model()
        self.instructor = user_model_class.objects.create_user(
            username='catalog-instructor',
            email='catalog-instructor@example.com',
            password='test-password',
            role=user_model_class.Role.INSTRUCTOR,
            first_name='Ava',
            last_name='Teacher',
        )
        self.other_instructor = user_model_class.objects.create_user(
            username='other-catalog-instructor',
            email='other-catalog-instructor@example.com',
            password='test-password',
            role=user_model_class.Role.INSTRUCTOR,
            first_name='Zoe',
            last_name='Tutor',
        )
        self.student = user_model_class.objects.create_user(
            username='catalog-student',
            email='catalog-student@example.com',
            password='test-password',
            role=user_model_class.Role.STUDENT,
        )
        self.second_student = user_model_class.objects.create_user(
            username='catalog-second-student',
            email='catalog-second-student@example.com',
            password='test-password',
            role=user_model_class.Role.STUDENT,
        )
        self.course_z = Course.objects.create(
            title='Zebra Python',
            slug='zebra-python',
            description='Build backend applications.',
            instructor=self.instructor,
            ished=True,
        )
        self.course_a = Course.objects.create(
            title='Alpha Django',
            slug='alpha-django',
            description='Learn web backend development.',
            instructor=self.instructor,
            ished=True,
        )
        self.other_course = Course.objects.create(
            title='Mobile Design',
            slug='mobile-design',
            description='Design mobile apps.',
            instructor=self.other_instructor,
            ished=True,
        )
        Enrollment.objects.create(student=self.student, course=self.course_z)
        Enrollment.objects.create(student=self.second_student, course=self.course_z)

    def test_catalog_sorts_filters_and_searches_course_content(self):
        response = self.client.get(
            reverse('courses'),
            {
                'q': 'backend',
                'instructor': str(self.instructor.pk),
                'sort': 'title',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context['courses'].values_list('id', flat=True)),
            [self.course_a.id, self.course_z.id],
        )
        self.assertEqual(response.context['sort_by'], 'title')

    def test_search_matches_instructor_name_and_handles_legacy_post(self):
        response = self.client.post(
            reverse('search'),
            {'searched': 'Ava Teacher'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.context['matching_courses'].values_list('id', flat=True)),
            {self.course_a.id, self.course_z.id},
        )

    def test_course_title_matches_take_precedence_over_description_matches(self):
        cplusplus_course = Course.objects.create(
            title='C++ Programming',
            slug='cplusplus-programming',
            description='Learn programming fundamentals.',
            instructor=self.instructor,
            ished=True,
        )
        self.course_z.description = 'A Python course for students who know C/C++.'
        self.course_z.save(update_fields=['description'])

        response = self.client.get(reverse('courses'), {'q': 'C++'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context['courses'].values_list('id', flat=True)),
            [cplusplus_course.id],
        )

    def test_catalog_popularity_sort_uses_enrollment_count(self):
        response = self.client.get(reverse('courses'), {'sort': 'popular'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['courses'][0], self.course_z)
        self.assertEqual(response.context['courses'][0].enrollment_count, 2)

    def test_invalid_catalog_sort_falls_back_to_newest(self):
        response = self.client.get(reverse('courses'), {'sort': 'rating'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sort_by'], 'newest')


class TeacherAnalyticsTests(TestCase):
    def setUp(self):
        user_model_class = get_user_model()
        self.instructor = user_model_class.objects.create_user(
            username='analytics-teacher',
            email='analytics-teacher@example.com',
            password='test-password',
            role=user_model_class.Role.INSTRUCTOR,
        )
        self.students = [
            user_model_class.objects.create_user(
                username=f'analytics-learner-{index}',
                email=f'analytics-learner-{index}@example.com',
                password='test-password',
                role=user_model_class.Role.STUDENT,
            )
            for index in range(2)
        ]
        self.course = Course.objects.create(
            title='Analytics Instructor Course',
            slug='analytics-instructor-course',
            description='A course for instructor analytics tests.',
            instructor=self.instructor,
            ished=True,
        )
        self.lesson = Lesson.objects.create(
            chapter=Chapter.objects.create(course=self.course, title='Chapter'),
            title='Lesson',
        )
        Enrollment.objects.create(
            student=self.students[0],
            course=self.course,
            status='COMPLETED',
            progress=100,
        )
        Enrollment.objects.create(
            student=self.students[1],
            course=self.course,
            progress=50,
        )
        self.client.force_login(self.instructor)

    def test_analytics_uses_real_enrollment_progress_and_monthly_counts(self):
        LessonProgress.objects.create(
            user=self.students[0],
            lesson=self.lesson,
            completed=True,
        )

        response = self.client.get(reverse('teacher_analytics'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_students'], 2)
        self.assertEqual(response.context['completed_percent'], 50)
        self.assertEqual(response.context['in_progress_percent'], 50)
        self.assertEqual(response.context['not_started_percent'], 0)
        self.assertEqual(response.context['avg_completion_rate'], 75)
        self.assertEqual(len(response.context['enrollment_trend']), 6)
        self.assertEqual(response.context['enrollment_trend'][-1]['value'], 2)
        self.assertEqual(response.context['course_stats'][0].avg_progress, 75)
        self.assertEqual(response.context['total_interactions'], 1)


class CourseVisibilityTests(TestCase):
    def setUp(self):
        user_model_class = get_user_model()
        self.instructor = user_model_class.objects.create_user(
            username='visibility-instructor',
            email='visibility-instructor@example.com',
            password='test-password',
            role=user_model_class.Role.INSTRUCTOR,
        )
        self.student = user_model_class.objects.create_user(
            username='visibility-student',
            email='visibility-student@example.com',
            password='test-password',
            role=user_model_class.Role.STUDENT,
        )
        self.public_course = Course.objects.create(
            title='Public Course',
            slug='public-course',
            description='A public course.',
            instructor=self.instructor,
            ished=True,
        )
        self.private_course = Course.objects.create(
            title='Private Course',
            slug='private-course',
            description='A private course.',
            instructor=self.instructor,
            ished=False,
        )
        Enrollment.objects.create(
            student=self.student,
            course=self.private_course,
        )

    def test_private_course_is_hidden_and_students_cannot_access_it(self):
        self.client.force_login(self.student)

        home_response = self.client.get(reverse('home'))
        courses_response = self.client.get(reverse('courses'))
        search_response = self.client.post(
            reverse('search'),
            {'searched': 'Course'},
        )

        self.assertContains(home_response, self.public_course.title)
        self.assertNotContains(home_response, self.private_course.title)
        self.assertContains(courses_response, self.public_course.title)
        self.assertNotContains(courses_response, self.private_course.title)
        self.assertContains(search_response, self.public_course.title)
        self.assertNotContains(search_response, self.private_course.title)
        self.assertEqual(
            self.client.get(
                reverse('detail-course'),
                {'id': self.private_course.id},
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                reverse('enroll_course', args=[self.private_course.id]),
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse('learning', args=[self.private_course.id]),
            ).status_code,
            404,
        )

    def test_instructor_can_change_course_visibility(self):
        self.client.force_login(self.instructor)

        response = self.client.post(
            reverse('edit_course', args=[self.public_course.id]),
            {
                'title': self.public_course.title,
                'description': self.public_course.description,
                'status': 'draft',
            },
        )

        self.assertRedirects(response, reverse('teacher_courses'))
        self.public_course.refresh_from_db()
        self.assertFalse(self.public_course.ished)


class CourseDetailPageTests(TestCase):
    def setUp(self):
        user_model_class = get_user_model()
        self.instructor = user_model_class.objects.create_user(
            username='detail-instructor',
            email='detail-instructor@example.com',
            password='test-password',
            role=user_model_class.Role.INSTRUCTOR,
            first_name='Course',
            last_name='Teacher',
        )
        self.student = user_model_class.objects.create_user(
            username='detail-student',
            email='detail-student@example.com',
            password='test-password',
            role=user_model_class.Role.STUDENT,
        )
        self.other_student = user_model_class.objects.create_user(
            username='detail-other-student',
            email='detail-other-student@example.com',
            password='test-password',
            role=user_model_class.Role.STUDENT,
        )
        self.course = Course.objects.create(
            title='Advanced Detail Course',
            slug='advanced-detail-course',
            description='A public course with a structured curriculum.',
            instructor=self.instructor,
            ished=True,
        )
        self.chapter = Chapter.objects.create(
            course=self.course,
            title='Getting Started',
            order=1,
        )
        self.preview_lesson = Lesson.objects.create(
            chapter=self.chapter,
            title='Introduction Preview',
            lesson_type=Lesson.LessonType.ARTICLE,
            content='Public preview content.',
            duration=12,
            order=1,
            is_preview=True,
            status='active',
        )
        Lesson.objects.create(
            chapter=self.chapter,
            title='Regular Lesson',
            duration=20,
            order=2,
            status='active',
        )
        Lesson.objects.create(
            chapter=self.chapter,
            title='Draft Lesson',
            duration=90,
            order=3,
            status='inactive',
        )
        draft_chapter = Chapter.objects.create(
            course=self.course,
            title='Draft-only chapter',
            order=2,
        )
        Lesson.objects.create(
            chapter=draft_chapter,
            title='Draft-only lesson',
            status='inactive',
        )
        Enrollment.objects.create(student=self.other_student, course=self.course)

    def test_detail_shows_public_curriculum_counts_and_preview_only(self):
        response = self.client.get(
            reverse('detail-course'),
            {'id': self.course.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_lessons'], 2)
        self.assertEqual(response.context['total_minutes'], 32)
        self.assertEqual(response.context['preview_count'], 1)
        self.assertEqual(response.context['course'].enrollment_count, 1)
        self.assertContains(response, 'Introduction Preview')
        self.assertContains(response, 'Public preview content.')
        self.assertContains(
            response,
            f'data-bs-target="#lessonPreview{self.preview_lesson.id}"',
        )
        self.assertNotContains(response, 'Draft Lesson')
        self.assertNotContains(response, 'Draft-only chapter')
        self.assertNotContains(response, 'id="enroll-form"')
        self.assertContains(response, reverse('login'))

    def test_enrolled_student_can_continue_from_course_detail(self):
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status='ACTIVE',
            progress=40,
        )
        self.client.force_login(self.student)

        response = self.client.get(
            reverse('detail-course'),
            {'id': self.course.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('learning', args=[self.course.id]))
        self.assertContains(response, '40%')
        self.assertNotContains(response, 'id="enroll-form"')

    def test_enrolling_from_detail_redirects_to_learning(self):
        self.client.force_login(self.student)

        response = self.client.post(
            reverse('enroll_course', args=[self.course.id]),
        )

        self.assertRedirects(
            response,
            reverse('learning', args=[self.course.id]),
        )
        self.assertTrue(
            Enrollment.objects.filter(
                student=self.student,
                course=self.course,
                status='ACTIVE',
            ).exists()
        )

    def test_ajax_enrollment_returns_learning_url(self):
        self.client.force_login(self.student)

        response = self.client.post(
            reverse('enroll_course', args=[self.course.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertEqual(
            response.json()['redirect_url'],
            reverse('learning', args=[self.course.id]),
        )


class LessonVisibilityTests(TestCase):
    def setUp(self):
        user_model_class = get_user_model()
        self.instructor = user_model_class.objects.create_user(
            username='lesson-visibility-instructor',
            email='lesson-visibility-instructor@example.com',
            password='test-password',
            role=user_model_class.Role.INSTRUCTOR,
        )
        self.student = user_model_class.objects.create_user(
            username='lesson-visibility-student',
            email='lesson-visibility-student@example.com',
            password='test-password',
            role=user_model_class.Role.STUDENT,
        )
        self.course = Course.objects.create(
            title='Lesson Visibility Course',
            slug='lesson-visibility-course',
            description='A course for lesson visibility tests.',
            instructor=self.instructor,
            ished=True,
        )
        self.chapter = Chapter.objects.create(course=self.course, title='Chapter')
        self.public_lesson = Lesson.objects.create(
            chapter=self.chapter,
            title='Public lesson',
            status='active',
        )
        self.private_lesson = Lesson.objects.create(
            chapter=self.chapter,
            title='Private lesson',
            status='inactive',
        )
        Enrollment.objects.create(student=self.student, course=self.course)

    def test_private_lesson_is_hidden_and_direct_access_is_blocked(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse('learning', args=[self.course.id]))

        self.assertContains(response, self.public_lesson.title)
        self.assertNotContains(response, self.private_lesson.title)
        self.assertEqual(
            self.client.get(
                reverse('learning', args=[self.course.id]),
                {'lesson': self.private_lesson.id},
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                reverse(
                    'track_lesson_study',
                    args=[self.course.id, self.private_lesson.id],
                ),
            ).status_code,
            404,
        )

    def test_instructor_can_edit_lesson_visibility(self):
        self.client.force_login(self.instructor)

        self.assertEqual(
            self.client.get(
                reverse('edit_lesson', args=[self.public_lesson.id]),
            ).status_code,
            200,
        )
        response = self.client.post(
            reverse('edit_lesson', args=[self.public_lesson.id]),
            {
                'title': self.public_lesson.title,
                'duration': 15,
                'status': 'inactive',
                'video_url': '',
                'content': '',
            },
        )

        self.assertRedirects(response, reverse('teacher_lessons'))
        self.public_lesson.refresh_from_db()
        self.assertEqual(self.public_lesson.status, 'inactive')

    def test_instructor_can_create_private_lesson(self):
        self.client.force_login(self.instructor)

        self.client.post(
            reverse('add_lesson', args=[self.chapter.id]),
            {
                'title': 'New private lesson',
                'status': 'inactive',
                'content': 'Nội dung bài giảng riêng tư.',
            },
        )

        new_lesson = Lesson.objects.get(title='New private lesson')
        self.assertEqual(new_lesson.status, 'inactive')
        self.assertEqual(new_lesson.content, 'Nội dung bài giảng riêng tư.')

    def test_instructor_adds_lessons_in_chapter_order(self):
        self.client.force_login(self.instructor)

        for title in ('First added lesson', 'Second added lesson'):
            response = self.client.post(
                reverse('add_lesson', args=[self.chapter.id]),
                {'title': title, 'status': 'active'},
            )
            self.assertRedirects(
                response,
                reverse('course_detail_instructor', args=[self.course.id]),
            )

        first_added = Lesson.objects.get(title='First added lesson')
        second_added = Lesson.objects.get(title='Second added lesson')
        self.assertEqual(first_added.order, 2)
        self.assertEqual(second_added.order, 3)
        self.assertEqual(
            list(self.chapter.lessons.values_list('title', flat=True)),
            ['Public lesson', 'Private lesson', 'First added lesson', 'Second added lesson'],
        )

    def test_instructor_can_upload_and_replace_word_and_powerpoint_attachments(self):
        self.client.force_login(self.instructor)

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(MEDIA_ROOT=media_root):
                self.client.post(
                    reverse('add_lesson', args=[self.chapter.id]),
                    {
                        'title': 'Lesson with Word document',
                        'status': 'active',
                        'content': 'Lesson notes entered while creating the lesson.',
                        'attachment': SimpleUploadedFile(
                            'course-notes.docx',
                            b'word document contents',
                            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        ),
                    },
                )

                lesson = Lesson.objects.get(title='Lesson with Word document')
                self.assertEqual(
                    lesson.content,
                    'Lesson notes entered while creating the lesson.',
                )
                self.assertTrue(lesson.attachment.name.endswith('.docx'))
                self.assertTrue(lesson.attachment.storage.exists(lesson.attachment.name))
                previous_attachment_name = lesson.attachment.name

                response = self.client.post(
                    reverse('edit_lesson', args=[lesson.id]),
                    {
                        'title': lesson.title,
                        'duration': 15,
                        'status': 'active',
                        'video_url': '',
                        'content': '',
                        'attachment': SimpleUploadedFile(
                            'course-slides.pptx',
                            b'powerpoint presentation contents',
                            content_type='application/vnd.openxmlformats-officedocument.presentationml.presentation',
                        ),
                    },
                )

                self.assertRedirects(response, reverse('teacher_lessons'))
                lesson.refresh_from_db()
                self.assertTrue(lesson.attachment.name.endswith('.pptx'))
                self.assertTrue(lesson.attachment.storage.exists(lesson.attachment.name))
                self.assertFalse(
                    lesson.attachment.storage.exists(previous_attachment_name)
                )

                self.client.post(
                    reverse('edit_lesson', args=[lesson.id]),
                    {
                        'title': lesson.title,
                        'duration': 15,
                        'status': 'active',
                        'video_url': '',
                        'content': '',
                    },
                )
                lesson.refresh_from_db()
                self.assertTrue(lesson.attachment.name.endswith('.pptx'))

    def test_rejects_unsupported_lesson_attachment_extension(self):
        self.client.force_login(self.instructor)

        self.client.post(
            reverse('add_lesson', args=[self.chapter.id]),
            {
                'title': 'Unsupported attachment',
                'status': 'active',
                'attachment': SimpleUploadedFile(
                    'program.exe',
                    b'not an allowed document',
                ),
            },
        )

        self.assertFalse(Lesson.objects.filter(title='Unsupported attachment').exists())


class CourseAdminAddTests(TestCase):
    def setUp(self):
        user_model_class = get_user_model()
        self.admin = user_model_class.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='test-password',
        )
        self.instructor = user_model_class.objects.create_user(
            username='instructor',
            email='instructor@example.com',
            password='test-password',
            role=user_model_class.Role.INSTRUCTOR,
        )

    def test_admin_can_add_course_without_price(self):
        admin_request = RequestFactory().get('/admin/app/course/add/')
        admin_request.user = self.admin
        course_admin = admin.site._registry[Course]
        course_form_class = course_admin.get_form(admin_request)
        course_form = course_form_class(
            data={
                'title': 'Test Course',
                'slug': 'test-course',
                'description': 'A course description',
                'instructor': str(self.instructor.pk),
            }
        )

        self.assertNotIn('price', course_form.fields)
        self.assertTrue(course_form.is_valid(), course_form.errors)
        course_form.save()
        self.assertTrue(Course.objects.filter(slug='test-course').exists())
