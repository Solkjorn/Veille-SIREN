import hmac
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from flask import (
    Flask, abort, flash, redirect, render_template, request, send_file,
    session, url_for,
)

from config import BASE_SQLITE, DOSSIER_RAPPORTS
from modules.base_donnees import (
    lire_collectes_recentes,
    lire_collectes_societe,
    lire_derniere_collecte,
)
from modules.comparaison import detecter_changements
from modules.import_excel import (
    analyser_televersement_excel,
    importer_apercu,
)
from modules.logger import FICHIER_LOG
from modules.societes_surveillees import (
    activer_societe_surveillee,
    ajouter_societe_surveillee,
    desactiver_societe_surveillee,
    lire_societe_surveillee,
    lire_societes_surveillees,
    modifier_societe_surveillee,
    restaurer_societe_surveillee,
    supprimer_societe_surveillee,
)


def creer_application(configuration: dict | None = None) -> Flask:
    """Crée l'application web Veille-SIREN."""
    application = Flask(__name__)
    application.config.from_mapping(
        BASE_SQLITE=BASE_SQLITE,
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,
        SECRET_KEY=secrets.token_hex(32),
        CSRF_ACTIVE=True,
    )
    if configuration:
        application.config.update(configuration)

    apercus_import: dict[str, tuple[datetime, object]] = {}

    def chemin_base() -> Path:
        return Path(application.config["BASE_SQLITE"])

    def jeton_csrf() -> str:
        if "jeton_csrf" not in session:
            session["jeton_csrf"] = secrets.token_urlsafe(32)
        return session["jeton_csrf"]

    def verifier_csrf() -> None:
        if not application.config["CSRF_ACTIVE"]:
            return
        recu = request.form.get("jeton_csrf", "")
        attendu = session.get("jeton_csrf", "")
        if not attendu or not hmac.compare_digest(recu, attendu):
            abort(400)

    application.jinja_env.globals["jeton_csrf"] = jeton_csrf

    def nettoyer_apercus() -> None:
        limite = datetime.now() - timedelta(minutes=30)
        expires = [
            identifiant for identifiant, (creation, _) in apercus_import.items()
            if creation < limite
        ]
        for identifiant in expires:
            apercus_import.pop(identifiant, None)

    @application.get("/")
    def tableau_de_bord():
        societes = lire_societes_surveillees(
            inclure_archivees=True,
            chemin=chemin_base(),
        )
        actives = [
            societe for societe in societes
            if societe.actif and societe.date_archivage is None
        ]
        archivees = [
            societe for societe in societes
            if societe.date_archivage is not None
        ]
        lignes = [
            {
                "surveillance": societe,
                "collecte": lire_derniere_collecte(
                    societe.siren, chemin_base(),
                ),
            }
            for societe in societes
        ]
        return render_template(
            "tableau_de_bord.html",
            lignes=lignes,
            nombre_actives=len(actives),
            nombre_inactives=len(societes) - len(actives) - len(archivees),
            nombre_archivees=len(archivees),
        )

    @application.post("/societes")
    def ajouter_societe():
        verifier_csrf()
        try:
            ajouter_societe_surveillee(
                request.form.get("siren", ""),
                actif=request.form.get("actif") == "1",
                commentaire=request.form.get("commentaire", ""),
                chemin=chemin_base(),
            )
        except ValueError as erreur:
            flash(str(erreur), "erreur")
        else:
            flash("La société a été ajoutée.", "succes")
        return redirect(url_for("tableau_de_bord"))

    @application.post("/societes/<siren>/modifier")
    def modifier_societe(siren: str):
        verifier_csrf()
        try:
            modifier_societe_surveillee(
                siren,
                commentaire=request.form.get("commentaire", ""),
                chemin=chemin_base(),
            )
        except (KeyError, ValueError) as erreur:
            flash(str(erreur), "erreur")
        else:
            flash("Le commentaire a été modifié.", "succes")
        return redirect(url_for("tableau_de_bord"))

    def executer_transition(siren: str, operation, message: str):
        verifier_csrf()
        try:
            operation(siren, chemin=chemin_base())
        except (KeyError, ValueError) as erreur:
            flash(str(erreur), "erreur")
        else:
            flash(message, "succes")
        return redirect(url_for("tableau_de_bord"))

    @application.post("/societes/<siren>/activer")
    def activer_societe(siren: str):
        return executer_transition(
            siren, activer_societe_surveillee, "La société a été activée."
        )

    @application.post("/societes/<siren>/desactiver")
    def desactiver_societe(siren: str):
        return executer_transition(
            siren, desactiver_societe_surveillee,
            "La société a été désactivée."
        )

    @application.post("/societes/<siren>/archiver")
    def archiver_societe(siren: str):
        return executer_transition(
            siren, supprimer_societe_surveillee,
            "La société a été archivée."
        )

    @application.post("/societes/<siren>/restaurer")
    def restaurer_societe(siren: str):
        return executer_transition(
            siren, restaurer_societe_surveillee,
            "La société a été restaurée."
        )

    @application.get("/imports")
    def imports():
        return render_template("imports.html")

    @application.post("/import-excel/previsualiser")
    def previsualiser_import():
        verifier_csrf()
        fichier = request.files.get("fichier_excel")
        if fichier is None or not fichier.filename:
            flash("Sélectionnez un fichier Excel.", "erreur")
            return redirect(url_for("imports"))
        try:
            apercu = analyser_televersement_excel(
                fichier.filename, fichier.read()
            )
        except (ValueError, OSError) as erreur:
            flash(str(erreur), "erreur")
            return redirect(url_for("imports"))

        nettoyer_apercus()
        identifiant = secrets.token_urlsafe(24)
        apercus_import[identifiant] = (datetime.now(), apercu)
        return render_template(
            "previsualisation_import.html",
            apercu=apercu,
            identifiant_import=identifiant,
        )

    @application.post("/import-excel/confirmer")
    def confirmer_import():
        verifier_csrf()
        nettoyer_apercus()
        identifiant = request.form.get("identifiant_import", "")
        entree = apercus_import.pop(identifiant, None)
        if entree is None:
            flash(
                "Cette prévisualisation a expiré. Sélectionnez à nouveau le fichier.",
                "erreur",
            )
            return redirect(url_for("imports"))

        _, apercu = entree
        bilan = importer_apercu(apercu, chemin_base())
        flash(
            f"Import terminé : {bilan.ajouts} ajout(s), "
            f"{bilan.mises_a_jour} mise(s) à jour et "
            f"{bilan.lignes_ignorees} ligne(s) ignorée(s).",
            "succes",
        )
        return redirect(url_for("imports"))

    @application.get("/societes/<siren>/historique")
    def historique_societe(siren: str):
        surveillance = lire_societe_surveillee(siren, chemin_base())
        if surveillance is None:
            abort(404)
        collectes = lire_collectes_societe(siren, chemin_base())
        historique = []
        precedente = None
        for collecte in collectes:
            historique.append({
                "collecte": collecte,
                "changements": detecter_changements(precedente, collecte),
            })
            precedente = collecte
        historique.reverse()
        return render_template(
            "historique_societe.html",
            surveillance=surveillance,
            historique=historique,
        )

    @application.get("/collectes")
    def collectes():
        return render_template(
            "collectes.html",
            collectes=lire_collectes_recentes(100, chemin_base()),
        )

    @application.get("/journal")
    def journal():
        lignes = []
        if FICHIER_LOG.is_file():
            lignes = FICHIER_LOG.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()[-200:]
        return render_template("journal.html", lignes=lignes)

    @application.get("/rapports")
    def rapports():
        fichiers = sorted(
            list(DOSSIER_RAPPORTS.glob("*.html"))
            + list(DOSSIER_RAPPORTS.glob("*.md")),
            key=lambda fichier: fichier.stat().st_mtime,
            reverse=True,
        )
        return render_template("rapports.html", fichiers=fichiers)

    @application.get("/rapports/<nom_fichier>")
    def consulter_rapport(nom_fichier: str):
        chemin = DOSSIER_RAPPORTS / Path(nom_fichier).name
        if nom_fichier != chemin.name or chemin.suffix.casefold() not in {
            ".html", ".md"
        }:
            abort(404)
        if not chemin.is_file():
            abort(404)
        if chemin.suffix.casefold() == ".html":
            return send_file(chemin, mimetype="text/html")
        return render_template(
            "rapport.html",
            nom_fichier=chemin.name,
            contenu=chemin.read_text(encoding="utf-8", errors="replace"),
        )

    @application.get("/rapports/<nom_fichier>/telecharger")
    def telecharger_rapport(nom_fichier: str):
        chemin = DOSSIER_RAPPORTS / Path(nom_fichier).name
        if nom_fichier != chemin.name or chemin.suffix.casefold() not in {
            ".html", ".md"
        }:
            abort(404)
        if not chemin.is_file():
            abort(404)
        return send_file(chemin, as_attachment=True, download_name=chemin.name)

    return application
