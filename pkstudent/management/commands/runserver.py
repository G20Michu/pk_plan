from threading import Thread

from django.contrib.staticfiles.management.commands.runserver import Command as StaticFilesRunserver

from pkstudent.schedule_sync import run_schedule_sync_loop


class Command(StaticFilesRunserver):
    def on_bind(self, server_port):
        super().on_bind(server_port)
        Thread(
            target=run_schedule_sync_loop,
            name="pkstudent-schedule-sync",
            daemon=True,
        ).start()
        self.stdout.write("Synchronizacja planu działa w tle co 10 min 30 s.")