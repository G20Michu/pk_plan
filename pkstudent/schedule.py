from datetime import datetime, time, timedelta


WEEKDAYS = (
    "Poniedziałek",
    "Wtorek",
    "Środa",
    "Czwartek",
    "Piątek",
    "Sobota",
    "Niedziela",
)


def event_matches_student_groups(event_group, student_sections):
    sections = {section.casefold() for section in student_sections if section}
    for label in (part.strip().casefold() for part in event_group.split(",")):
        if label in sections:
            return True
        if label in {"c", "s"} and any(section.startswith(label) for section in sections):
            return True
        if label == "w" and "w1" in sections:
            return True
        if label == "l" and any(
            section.startswith("l") and not section.startswith(("lk", "lek"))
            for section in sections
        ):
            return True
        if label == "lk" and any(section.startswith("lk") for section in sections):
            return True
    return False


def display_group_for_student(event_group, student_sections):
    labels = [label.strip() for label in event_group.split(",")]
    if len(labels) != 1:
        return event_group

    label = labels[0].casefold()
    sections = [section for section in student_sections if section]
    for section in sections:
        normalized_section = section.casefold()
        if label in {"c", "s"} and normalized_section.startswith(label):
            return section
        if label == "w" and normalized_section == "w1":
            return section
        if label == "l" and normalized_section.startswith("l") and not normalized_section.startswith(("lk", "lek")):
            return section
        if label == "lk" and normalized_section.startswith("lk"):
            return section
    return event_group


def infer_student_faculties(events, student_sections):
    sections = {section.casefold() for section in student_sections if section}
    faculties_by_section = {section: set() for section in sections}

    for event in events:
        event_faculties = {
            faculty.strip().casefold()
            for faculty in (event.faculty or "").split(",")
            if faculty.strip()
        }
        if not event_faculties:
            continue
        for label in event.group_label.split(","):
            section = label.strip().casefold()
            if section in faculties_by_section:
                faculties_by_section[section].update(event_faculties)

    known_faculty_sets = [values for values in faculties_by_section.values() if values]
    if not known_faculty_sets:
        return set()
    return set.intersection(*known_faculty_sets)


def event_matches_student_schedule(event_group, event_faculty, student_sections, student_faculties):
    if event_faculty and student_faculties:
        event_faculties = {value.strip().casefold() for value in event_faculty.split(",") if value.strip()}
        if not event_faculties.intersection(student_faculties):
            return False
    if event_matches_student_groups(event_group, student_sections):
        return True
    if not student_faculties:
        return False

    sections = {section.casefold() for section in student_sections if section}
    for label in (part.strip().casefold() for part in event_group.split(",")):
        if label in {"c", "s"} and any(section.startswith(label) for section in sections):
            return True
        if label == "w" and "w1" in sections:
            return True
        if label == "l" and any(
            section.startswith("l") and not section.startswith(("lk", "lek"))
            for section in sections
        ):
            return True
        if label == "lk" and any(section.startswith("lk") for section in sections):
            return True
    return False


def build_week_plan(events, student_sections, week_start):
    events = list(events)
    student_sections = list(student_sections)
    student_faculties = infer_student_faculties(events, student_sections)
    days = [
        {"date": week_start + timedelta(days=offset), "weekday": WEEKDAYS[offset], "events": []}
        for offset in range(7)
    ]

    for event in events:
        overrides = event.overrides if isinstance(event.overrides, dict) else {}
        excluded_dates = set(event.excluded_dates or [])
        for day in days:
            event_date = day["date"]
            date_key = event_date.isoformat()
            override = overrides.get(date_key, {})
            if not isinstance(override, dict) or override.get("cancelled", False):
                continue

            is_extra = override.get("_add") is True
            if not is_extra:
                if not event.start_date <= event_date <= event.end_date:
                    continue
                days_from_start = (event_date - event.start_date).days
                if event_date.weekday() != event.start_date.weekday():
                    continue
                if days_from_start // 7 % max(event.interval_weeks, 1):
                    continue
                if date_key in excluded_dates:
                    continue

            group_label = override.get("group", event.group_label)
            if not event_matches_student_schedule(
                group_label,
                override.get("faculty", event.faculty),
                student_sections,
                student_faculties,
            ):
                continue

            start_time = time.fromisoformat(override.get("startTime", event.start_time.isoformat()))
            duration_min = int(override.get("durationMin", event.duration_min))
            end = datetime.combine(event_date, start_time) + timedelta(minutes=duration_min)
            day["events"].append({
                "event_type": override.get("eventType", event.event_type),
                "group_label": display_group_for_student(group_label, student_sections),
                "instructor": override.get("instructor", event.instructor),
                "room": override.get("room", event.room),
                "faculty": override.get("faculty", event.faculty),
                "start_time": start_time,
                "end_time": end.time(),
            })

    for day in days:
        day["events"].sort(key=lambda item: item["start_time"])
    return days