from django.db import migrations, models


def migrate_time_unlocks(apps, schema_editor):
    Lesson = apps.get_model('app', 'Lesson')
    database = schema_editor.connection.alias

    for lesson in Lesson.objects.using(database).filter(
        unlock_type='TIME_DELAY'
    ).iterator():
        # A prior hour-based setting becomes the equivalent study-minute
        # requirement. A zero-hour setting receives the new five-minute default.
        required_minutes = max(lesson.unlock_delay_hours * 60, 5)
        Lesson.objects.using(database).filter(pk=lesson.pk).update(
            unlock_type='STUDY_TIME',
            unlock_required_minutes=required_minutes,
        )


def reverse_time_unlocks(apps, schema_editor):
    Lesson = apps.get_model('app', 'Lesson')
    database = schema_editor.connection.alias

    for lesson in Lesson.objects.using(database).filter(
        unlock_type='STUDY_TIME'
    ).iterator():
        hours = (lesson.unlock_required_minutes + 59) // 60
        Lesson.objects.using(database).filter(pk=lesson.pk).update(
            unlock_type='TIME_DELAY',
            unlock_delay_hours=hours,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0006_lesson_required_watch_percent_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='lesson',
            name='unlock_required_minutes',
            field=models.PositiveIntegerField(
                default=5,
                verbose_name='Số phút cần học ở bài trước',
            ),
        ),
        migrations.RunPython(migrate_time_unlocks, reverse_time_unlocks),
        migrations.AlterField(
            model_name='lesson',
            name='unlock_type',
            field=models.CharField(
                choices=[
                    ('SEQUENTIAL', 'Hoàn thành bài học trước'),
                    ('STUDY_TIME', 'Hoàn thành hoặc học đủ phút bài trước'),
                ],
                default='SEQUENTIAL',
                max_length=20,
                verbose_name='Cách mở bài',
            ),
        ),
        migrations.RemoveField(
            model_name='lesson',
            name='unlock_delay_hours',
        ),
        migrations.AddField(
            model_name='lessonprogress',
            name='last_activity_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
