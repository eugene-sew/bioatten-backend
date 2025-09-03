# Generated manually to transform Schedule model

import django.db.models.deletion
from django.db import migrations, models
from datetime import time


class Migration(migrations.Migration):

    dependencies = [
        ('schedules', '0001_initial'),
    ]

    operations = [
        # Step 1: Add new fields with defaults
        migrations.AddField(
            model_name='schedule',
            name='title',
            field=models.CharField(default='Class Session', max_length=200, help_text='Title or name of the class session'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='schedule',
            name='date',
            field=models.DateField(db_index=True, help_text='Date of the scheduled class', null=True),
        ),
        migrations.AddField(
            model_name='schedule',
            name='clock_in_opens_at',
            field=models.TimeField(
                default=time(8, 45),  # Default: 15 minutes before 9:00
                help_text='Time when students can start clocking in (e.g., 15 minutes before start)'
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='schedule',
            name='clock_in_closes_at',
            field=models.TimeField(
                default=time(9, 15),  # Default: 15 minutes after 9:00
                help_text='Time when clock-in window closes (e.g., 15 minutes after start)'
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='schedule',
            name='description',
            field=models.TextField(blank=True, help_text='Additional notes or description'),
        ),
        migrations.RenameField(
            model_name='schedule',
            old_name='student_group',
            new_name='assigned_group',
        ),
        migrations.AlterField(
            model_name='schedule',
            name='room',
            field=models.CharField(blank=True, max_length=50, help_text='Room or location'),
        ),
        
        # Step 2: Remove old fields and constraints
        migrations.AlterUniqueTogether(
            name='schedule',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='schedule',
            name='weekday',
        ),
        migrations.RemoveField(
            model_name='schedule',
            name='course_name',
        ),
        migrations.RemoveField(
            model_name='schedule',
            name='is_active',
        ),
        migrations.RemoveField(
            model_name='schedule',
            name='effective_from',
        ),
        migrations.RemoveField(
            model_name='schedule',
            name='effective_until',
        ),
        
        # Step 3: Make date required and add new constraints
        migrations.AlterField(
            model_name='schedule',
            name='date',
            field=models.DateField(db_index=True, help_text='Date of the scheduled class'),
        ),
        migrations.AddIndex(
            model_name='schedule',
            index=models.Index(fields=['date', 'assigned_group'], name='schedules_date_7fb8f8_idx'),
        ),
        migrations.AddIndex(
            model_name='schedule',
            index=models.Index(fields=['date', 'faculty'], name='schedules_date_e3a1f7_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='schedule',
            unique_together={('assigned_group', 'date', 'start_time'), ('faculty', 'date', 'start_time')},
        ),
        migrations.AlterModelOptions(
            name='schedule',
            options={'ordering': ['date', 'start_time'], 'verbose_name': 'Schedule', 'verbose_name_plural': 'Schedules'},
        ),
        
        # Update field attributes
        migrations.AlterField(
            model_name='schedule',
            name='start_time',
            field=models.TimeField(help_text='Class start time'),
        ),
        migrations.AlterField(
            model_name='schedule',
            name='end_time',
            field=models.TimeField(help_text='Class end time'),
        ),
        migrations.AlterField(
            model_name='schedule',
            name='assigned_group',
            field=models.ForeignKey(
                help_text='Student group assigned to this class',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='schedules',
                to='students.studentgroup'
            ),
        ),
        migrations.AlterField(
            model_name='schedule',
            name='faculty',
            field=models.ForeignKey(
                help_text='Faculty member teaching this class',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='schedules',
                to='faculty.faculty'
            ),
        ),
    ]
