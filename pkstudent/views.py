from datetime import date, timedelta

from django.db.models import Max
from django.shortcuts import render
from django.utils import timezone

from pkstudent.models import ScheduleEvent, Student
from pkstudent.schedule import build_week_plan


def student_schedule(request):
	number = request.GET.get("number", "").strip()
	week_value = request.GET.get("week", "").strip()
	selected_date = timezone.localdate()
	error = ""

	if week_value:
		try:
			selected_date = date.fromisoformat(week_value)
		except ValueError:
			error = "Nieprawidłowa data tygodnia."

	week_start = selected_date - timedelta(days=selected_date.weekday())
	week_end = week_start + timedelta(days=6)
	student = None
	days = None

	if number:
		try:
			student = Student.objects.prefetch_related("student_groups").get(number=int(number))
		except (Student.DoesNotExist, ValueError):
			error = "Nie znaleziono studenta o podanym numerze."
		else:
			sections = student.student_groups.values_list("section", flat=True)
			days = build_week_plan(ScheduleEvent.objects.all(), sections, week_start)

	return render(request, "pkstudent/schedule.html", {
		"number": number,
		"student": student,
		"days": days,
		"week_start": week_start,
		"week_end": week_end,
		"today": timezone.localdate(),
		"previous_week": week_start - timedelta(days=7),
		"next_week": week_start + timedelta(days=7),
		"error": error,
		"last_synced_at": ScheduleEvent.objects.aggregate(latest=Max("synced_at"))["latest"],
		"schedule_loaded": ScheduleEvent.objects.exists(),
	})