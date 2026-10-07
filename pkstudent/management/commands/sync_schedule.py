from django.core.management.base import BaseCommand

from pkstudent.schedule_sync import run_schedule_sync_loop, sync_schedule


class Command(BaseCommand):
    help = "Synchronizuje plan zajęć ze źródłowego API."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Wykonaj pojedynczą synchronizację i zakończ.",
        )

    def handle(self, *args, **options):
        if options["once"]:
            count = sync_schedule()
            self.stdout.write(self.style.SUCCESS(f"Zapisano {count} wydarzeń."))
            return

        self.stdout.write("Synchronizacja co 10 min 30 s. Przerwij Ctrl+C.")
        run_schedule_sync_loop()