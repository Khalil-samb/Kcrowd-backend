# Lecture d'un fichier vidéo « par morceaux » (en-tête HTTP Range).
#
# Pourquoi : sans cela, le navigateur doit tout télécharger avant de pouvoir avancer dans la vidéo,
# et Safari / iPhone refusent même de la lire. Avec Range, il demande « les octets 5 000 000 à la fin »
# et le serveur répond 206 (contenu partiel). Django seul ne sait pas faire cela pour des fichiers.
import os
import re

from django.http import HttpResponse, StreamingHttpResponse

TAILLE_MORCEAU = 1024 * 1024


def _lire(chemin, debut, longueur):
    with open(chemin, 'rb') as f:
        f.seek(debut)
        restant = longueur
        while restant > 0:
            morceau = f.read(min(TAILLE_MORCEAU, restant))
            if not morceau:
                break
            restant -= len(morceau)
            yield morceau


def reponse_avec_range(request, chemin, type_mime):
    taille = os.path.getsize(chemin)
    entete = (request.headers.get('Range') or '').strip()

    debut, fin, statut = 0, taille - 1, 200
    # Une seule plage est gérée (c'est ce que demandent les navigateurs) ; sinon on renvoie tout le fichier.
    if entete and ',' not in entete:
        m = re.fullmatch(r'bytes=(\d*)-(\d*)', entete)
        if not m or (m.group(1) == '' and m.group(2) == ''):
            r = HttpResponse(status=416)
            r['Content-Range'] = f'bytes */{taille}'
            return r
        if m.group(1) == '':                       # « bytes=-500 » : les 500 derniers octets
            debut = max(0, taille - int(m.group(2)))
        else:
            debut = int(m.group(1))
            if m.group(2) != '':
                fin = min(int(m.group(2)), taille - 1)
        if debut >= taille or debut > fin:
            r = HttpResponse(status=416)
            r['Content-Range'] = f'bytes */{taille}'
            return r
        statut = 206

    longueur = fin - debut + 1
    if request.method == 'HEAD':
        reponse = HttpResponse(status=statut, content_type=type_mime)
    else:
        reponse = StreamingHttpResponse(_lire(chemin, debut, longueur), status=statut, content_type=type_mime)
    reponse['Content-Length'] = str(longueur)
    reponse['Accept-Ranges'] = 'bytes'
    if statut == 206:
        reponse['Content-Range'] = f'bytes {debut}-{fin}/{taille}'
    reponse['Cache-Control'] = 'public, max-age=3600'
    return reponse
