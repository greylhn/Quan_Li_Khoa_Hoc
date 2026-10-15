from django.db import migrations, models


def set_default_watch_threshold(apps, schema_editor):
    Lesson = apps.get_model('app', 'Lesson')
    database = schema_editor.connection.alias
    Lesson.objects.using(database).filter(required_watch_percent=90).update(
        required_watch_percent=50
    )


def restore_default_watch_threshold(apps, schema_editor):
    Lesson = apps.get_model('app', 'Lesson')
    database = schema_editor.connection.alias
    Lesson.objects.using(database).filter(required_watch_percent=50).update(
        required_watch_percent=90
    )


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0007_lesson_study_unlock'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lesson',
            name='required_watch_percent',
            field=models.PositiveIntegerField(
                default=50,
                verbose_name='Phần trăm cần học để hoàn thành',
            ),
        ),
        migrations.RunPython(
            set_default_watch_threshold,
            restore_default_watch_threshold,
        ),
        migrations.AddField(
            model_name='lessonprogress',
            name='video_watched_seconds',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='lessonprogress',
            name='video_duration_seconds',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='lessonprogress',
            name='last_video_position',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='lessonprogress',
            name='last_video_activity_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='learningactivity',
            name='study_seconds',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
