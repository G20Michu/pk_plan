from django.db import models
from django.utils import timezone
from dataclasses import dataclass, field
from typing import List

@dataclass
class group:
    name: str
    section : List[str] = field(default_factory=list)
    descriotion : str = ""
    
###
excersise_group = group(name="C", section=['C1', 'C2', 'C3','C4','C5'], descriotion="This group is for excersises, your presence is mandatory")    
lecture_group = group(name="W", section=['W1', 'W2'], descriotion="This group is for lectures, your presence is not mandatory")
seminar_group = group(name="S", section=['S1', 'S2','S3','S4','S5'], descriotion="This group is for seminars, your presence is mandatory")
lectorship_group = group(name="L", section=['Lek1', 'Lek2','Lek3','Lek4','Lek5','Lek6','Lek7'], descriotion="This group is for lectorship, your presence is mandatory")
laboratory_group = group(name="Lab", section=['L1', 'L2','L3','L4','L5','L6','L7','L8','L9','L10','L11','L12','L13','L14'], descriotion="This group is for laboratory, your presence is mandatory")
computer_lab_group = group(name="CompLab", section=['LK1','LK2','LK3','LK4','LK5','LK6','Lk7','LK8','LK9'], descriotion="This group is for computer laboratory, your presence is mandatory")
###
Group_types = [
    excersise_group,
    lecture_group,
    seminar_group,
    lectorship_group,
    laboratory_group,
    computer_lab_group
]


class Student_Group(models.Model):
    groups = models.CharField(max_length=100, choices=[(g.name, g.name) for g in Group_types])
    section = models.CharField(max_length=100, choices=[(s, s) for g in Group_types for s in g.section], null=True, blank=True)

    def __str__(self):
        return f"{self.groups} - {self.section}"

class Student(models.Model):
    number = models.IntegerField(unique=True)
    student_groups = models.ManyToManyField(Student_Group, blank=True)

    def __str__(self):
        return f"Student {self.number}"


class ScheduleEvent(models.Model):
    remote_id = models.CharField(max_length=100, unique=True)
    event_type = models.CharField(max_length=250)
    group_label = models.CharField(max_length=100)
    instructor = models.CharField(max_length=250, blank=True)
    room = models.CharField(max_length=100, blank=True)
    faculty = models.CharField(max_length=100, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField()
    duration_min = models.PositiveIntegerField()
    interval_weeks = models.PositiveSmallIntegerField(default=1)
    excluded_dates = models.JSONField(default=list)
    overrides = models.JSONField(default=dict)
    synced_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("start_date", "start_time", "event_type")

    def __str__(self):
        return f"{self.event_type} ({self.group_label})"
    
    