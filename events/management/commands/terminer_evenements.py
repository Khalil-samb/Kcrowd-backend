from django.core.management.base import BaseCommand

from events.lifecycle import terminer_les_evenements_passes


class Command(BaseCommand):
    help = "Passe à « terminé » les événements publiés dont la date de fin est dépassée."

    def handle(self, *args, **options):
        n = terminer_les_evenements_passes()
        self.stdout.write(f"{n} événement(s) passé(s) à « terminé ».")