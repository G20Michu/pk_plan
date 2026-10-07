from datetime import date, time

from django.test import SimpleTestCase, TestCase

from pkstudent.models import ScheduleEvent, Student, Student_Group
from pkstudent.schedule import (
	build_week_plan,
	event_matches_student_groups,
	event_matches_student_schedule,
	infer_student_faculties,
)
from pkstudent.views import student_schedule


class ScheduleMatchingTests(SimpleTestCase):
	def make_event(self, **values):
		defaults = {
			"remote_id": "event-1",
			"event_type": "Matematyka",
			"group_label": "W",
			"instructor": "",
			"room": "A1",
			"faculty": "",
			"start_date": date(2026, 10, 5),
			"end_date": date(2027, 2, 1),
			"start_time": time(8, 30),
			"duration_min": 90,
			"interval_weeks": 1,
			"excluded_dates": [],
			"overrides": {},
		}
		defaults.update(values)
		return ScheduleEvent(**defaults)

	def test_generic_and_comma_separated_groups_match(self):
		self.assertFalse(event_matches_student_groups("W, L, P", ["W2"]))
		self.assertTrue(event_matches_student_groups("Lk1, Lk2", ["Lk2"]))
		self.assertFalse(event_matches_student_groups("Lek", ["Lek4"]))
		self.assertTrue(event_matches_student_groups("Lek4", ["Lek4"]))
		self.assertFalse(event_matches_student_groups("P1", ["C1", "S1"]))

	def test_w2_student_does_not_match_w1_events(self):
		self.assertTrue(event_matches_student_groups("W2", ["W2"]))
		self.assertFalse(event_matches_student_groups("W1", ["W2"]))
		self.assertFalse(
			event_matches_student_schedule("W1", "EiAs1", ["W2"], {"eias1"})
		)

	def test_generic_events_are_limited_to_inferred_faculty(self):
		events = [
			self.make_event(remote_id="specific", group_label="C4", faculty="EiAs1"),
			self.make_event(remote_id="own-course", group_label="C", faculty="EiAs1"),
			self.make_event(remote_id="other-course", group_label="C", faculty="EiAs5"),
		]
		faculties = infer_student_faculties(events, ["C4", "W2"])

		self.assertEqual(faculties, {"eias1"})
		self.assertTrue(event_matches_student_schedule("C", "EiAs1", ["C4", "W2"], faculties))
		self.assertFalse(event_matches_student_schedule("C", "EiAs5", ["C4", "W2"], faculties))
		self.assertFalse(event_matches_student_schedule("W", "EiAs1", ["C4", "W2"], faculties))

	def test_week_plan_applies_alternating_weeks_and_exceptions(self):
		event = self.make_event(
			group_label="Lk1",
			interval_weeks=2,
			excluded_dates=["2026-10-19"],
			overrides={
				"2026-10-19": {"_add": True, "cancelled": False, "startTime": "17:00"},
				"2026-11-02": {"_add": False, "cancelled": True},
			},
		)

		first_week = build_week_plan([event], ["Lk1"], date(2026, 10, 5))
		extra_week = build_week_plan([event], ["Lk1"], date(2026, 10, 19))
		cancelled_week = build_week_plan([event], ["Lk1"], date(2026, 11, 2))

		self.assertEqual(len(first_week[0]["events"]), 1)
		self.assertEqual(extra_week[0]["events"][0]["start_time"], time(17, 0))
		self.assertEqual(cancelled_week[0]["events"], [])

	def test_german_language_group_does_not_match_english_section(self):
		german_event = self.make_event(
			remote_id="german",
			event_type="Język niemiecki",
			group_label="Lek",
			faculty="EiAs3",
		)
		english_event = self.make_event(
			remote_id="english",
			event_type="Język angielski",
			group_label="Lek4",
			faculty="EiAs3",
		)

		week = build_week_plan([german_event, english_event], ["Lek4"], date(2026, 10, 5))

		self.assertEqual([event["event_type"] for event in week[0]["events"]], ["Język angielski"])
		self.assertEqual(week[0]["events"][0]["group_label"], "Lek4")


class StudentScheduleViewTests(TestCase):
	def test_student_sees_matching_groups_only(self):
		student = Student.objects.create(number=127)
		student.student_groups.add(Student_Group.objects.create(groups="W", section="W1"))
		ScheduleEvent.objects.create(
			remote_id="lecture-w",
			event_type="Wykład wspólny",
			group_label="W",
			start_date=date(2026, 10, 5),
			end_date=date(2027, 2, 1),
			start_time=time(8, 30),
			duration_min=90,
		)
		ScheduleEvent.objects.create(
			remote_id="lab-lk2",
			event_type="Laboratorium innej grupy",
			group_label="Lk2",
			start_date=date(2026, 10, 5),
			end_date=date(2027, 2, 1),
			start_time=time(10, 30),
			duration_min=90,
		)

		response = self.client.get("/", {"number": "127", "week": "2026-10-05"})

		self.assertContains(response, "Wykład wspólny")
		self.assertNotContains(response, "Laboratorium innej grupy")
		self.assertContains(response, "W1")
		self.assertContains(response, "Ostatnia aktualizacja:")
		self.assertContains(response, 'id="week-picker"')
		self.assertContains(response, 'value="2026-10-05"')
