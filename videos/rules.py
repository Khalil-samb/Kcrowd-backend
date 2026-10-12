# Qui peut mettre une vidéo, sur quel événement, quel fichier est accepté.
from django.utils import timezone

TAILLE_MAX_OCTETS = 300 * 1024 * 1024      # 300 Mo
NB_VIDEOS_MAX_PAR_EVENEMENT = 20
EXTENSIONS_ACCEPTEES = {'mp4': 'video/mp4', 'webm': 'video/webm'}


def raison_de_refuser_la_video(evenement, nb_videos_existantes, maintenant=None):
    """Texte du refus (pour l'organisateur), ou None si l'ajout est permis."""
    maintenant = maintenant or timezone.now()
    if evenement.status not in ('published', 'sold_out'):
        if evenement.status == 'finished':
            return "Cet événement est terminé : on ne peut plus lui ajouter de vidéo."
        return "Publiez d'abord l'événement : les vidéos ne sont visibles que pour les événements publiés."
    if evenement.end_date <= maintenant:
        return "Cet événement est terminé : on ne peut plus lui ajouter de vidéo."
    if nb_videos_existantes >= NB_VIDEOS_MAX_PAR_EVENEMENT:
        return f"Limite atteinte : {NB_VIDEOS_MAX_PAR_EVENEMENT} vidéos par événement. Supprimez-en une pour en ajouter."
    return None


def erreur_de_fichier(fichier):
    """Texte de l'erreur si le fichier n'est pas une vidéo MP4/WebM acceptable, sinon None.
    Le contenu est vérifié (et pas seulement le nom) : renommer un .exe en .mp4 ne passe pas."""
    if fichier is None:
        return "Choisissez un fichier vidéo."
    nom = (fichier.name or '').lower()
    extension = nom.rsplit('.', 1)[-1] if '.' in nom else ''
    if extension not in EXTENSIONS_ACCEPTEES:
        return "Format non accepté : envoyez une vidéo MP4 ou WebM."
    if fichier.size <= 0:
        return "Le fichier est vide."
    if fichier.size > TAILLE_MAX_OCTETS:
        return f"Vidéo trop lourde (maximum {TAILLE_MAX_OCTETS // (1024 * 1024)} Mo)."

    debut = fichier.read(12)
    fichier.seek(0)
    est_mp4 = len(debut) >= 8 and debut[4:8] == b'ftyp'
    est_webm = debut[:4] == b'\x1a\x45\xdf\xa3'
    if extension == 'mp4' and not est_mp4:
        return "Ce fichier n'est pas une vraie vidéo MP4."
    if extension == 'webm' and not est_webm:
        return "Ce fichier n'est pas une vraie vidéo WebM."
    return None


def type_mime_du_fichier(nom):
    return EXTENSIONS_ACCEPTEES[nom.lower().rsplit('.', 1)[-1]]
