# Une "permission" DRF est une classe dont la méthode has_permission() est
# appelée AUTOMATIQUEMENT par DRF avant d'exécuter le code d'une vue.
# Si elle retourne False, la requête est rejetée (erreur 403) et le code
# de la vue n'est même pas exécuté — c'est un vrai mur de sécurité, pas
# juste une vérification qu'on pourrait oublier de faire dans chaque vue.


from rest_framework.permissions import BasePermission


class IsOrganizer(BasePermission):
    message = "Accès réservé aux organisateurs."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == 'organizer' and u.status == 'active')


class IsAdmin(BasePermission):
    message = "Accès réservé aux administrateurs."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == 'admin')