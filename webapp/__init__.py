import hmac
import html
import json
import csv
import re
import secrets
import subprocess
import sys
import zipfile
from difflib import HtmlDiff
from io import BytesIO
from datetime import datetime, timedelta
from pathlib import Path

from flask import (
    Flask, Response, abort, flash, jsonify, redirect, render_template, request,
    send_file, session, url_for,
)

from config import BASE_SQLITE, DOSSIER_RAPPORTS, DOSSIER_SAUVEGARDES
from modules.base_donnees import (
    alertes_immediates_actives,
    changer_statut_alerte,
    configurer_preferences_alertes,
    configurer_alertes_immediates,
    lire_alertes,
    lire_preferences_alertes,
    lire_executions_veille,
    lire_collectes_recentes,
    lire_collectes_societe,
    lire_derniere_collecte,
    lire_document_inpi,
    lire_documents_inpi,
    creer_portefeuille, lire_portefeuilles, affecter_portefeuille,
    lire_societes_portefeuille, demander_arret_collecte,
    lire_taches_recentes,
    lire_erreurs_taches_entre,
    configurer_destinataire_portefeuille,
    lire_documents_inpi_tous,
    compter_documents_inpi,
    configurer_cible_notion,
    lire_cible_notion,
    lire_reglages_conservation,
    configurer_reglages_conservation,
    enregistrer_audit,
    lire_audit,
)
from modules.comparaison import CATEGORIES_ALERTES, detecter_changements
from modules.import_excel import (
    analyser_televersement_excel,
    creer_modele_import_excel,
    importer_apercu,
)
from modules.logger import FICHIER_LOG
from modules.exports import exporter_excel, exporter_pdf
from modules.planification import installer_tache, lancer_tache, lire_etat_tache
from modules.courriel import ErreurCourriel, verifier_connexion_smtp
from modules.notion import ErreurNotion, verifier_connexion_notion
from modules.sources import (
    SourceAnnuaireEntreprises, SourceBODACC, SourceINPI, SourceINSEE,
)
from modules.sauvegarde import creer_sauvegarde, verifier_restauration, ErreurSauvegarde
from modules.secrets_windows import (
    lire_cle_insee, lire_configuration_smtp, lire_identifiants_inpi,
    lire_jeton_notion, proteger_cle_insee, proteger_configuration_smtp,
    proteger_identifiants_inpi, proteger_jeton_notion,
)
from modules.diagnostic import diagnostiquer_application
from modules.espace_travail import (
    CHAMPS_REGLES, OPERATEURS_REGLES, PRIORITES_TACHES, STATUTS_TACHES,
    activer_modele_rapport, ajouter_echeance, ajouter_lien_societes, ajouter_note, ajouter_tache,
    appliquer_profil_societe, changer_statut_tache, enregistrer_generation,
    enregistrer_modele_rapport, enregistrer_profil, enregistrer_progression_demarrage,
    enregistrer_regle, epingler_note, evaluer_regle, exporter_echeances_ics,
    exporter_notes_csv, exporter_taches_csv, lire_echeances, lire_liens_societe, lire_modeles_rapports,
    lire_notes, lire_profil_societe, lire_profils, lire_progression_demarrage,
    lire_regles, lire_taches, simuler_regle,
)
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
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
    )
    if configuration:
        application.config.update(configuration)

    @application.after_request
    def ajouter_entetes_securite(reponse):
        reponse.headers.setdefault("X-Content-Type-Options", "nosniff")
        reponse.headers.setdefault("X-Frame-Options", "DENY")
        reponse.headers.setdefault("Referrer-Policy", "no-referrer")
        reponse.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'",
        )
        return reponse

    @application.before_request
    def limiter_api_au_poste_local():
        if request.path.startswith("/api") and request.remote_addr not in {
            "127.0.0.1", "::1", None,
        }:
            abort(403)

    apercus_import: dict[str, tuple[datetime, object]] = {}

    def chemin_base() -> Path:
        return Path(application.config["BASE_SQLITE"])

    def auditer(action: str, cible: str = "", detail: str = "") -> None:
        enregistrer_audit(action, cible, detail, chemin=chemin_base())

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

    @application.context_processor
    def contexte_espace_travail():
        progression = lire_progression_demarrage(chemin_base())
        return {
            "progression_demarrage": progression,
            "nombre_taches_ouvertes": len([
                t for t in lire_taches(chemin=chemin_base())
                if t["statut"] != "terminee"
            ]),
        }

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
        recherche = request.args.get("q", "").strip().casefold()
        etat_filtre = request.args.get("etat", "")
        anciennete = request.args.get("anciennete", type=int)
        modification_filtre = request.args.get("modification", "")
        erreur_filtre = request.args.get("erreur", "")
        source_filtre = request.args.get("source", "").casefold()
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
        lignes = []
        for societe in societes:
            historique = lire_collectes_societe(societe.siren, chemin_base())
            collecte = historique[-1] if historique else None
            changements = (
                detecter_changements(historique[-2], historique[-1])
                if len(historique) >= 2 else []
            )
            lignes.append({
                "surveillance": societe,
                "collecte": collecte,
                "changements": changements,
                "alertes": lire_alertes(20, siren=societe.siren, chemin=chemin_base()),
            })
            champs_essentiels = (
                "raison_sociale", "statut", "forme_juridique", "adresse"
            )
            manquants = (
                sum(not getattr(collecte, champ, "") for champ in champs_essentiels)
                if collecte else len(champs_essentiels)
            )
            lignes[-1]["qualite"] = max(
                0, 100 - manquants * 20
                - (15 if collecte and collecte.contradictions else 0)
                - (10 if collecte and collecte.erreurs_sources else 0)
            )
        if recherche:
            lignes = [l for l in lignes if recherche in l["surveillance"].siren or recherche in ((l["collecte"].raison_sociale if l["collecte"] else "").casefold())]
        if etat_filtre == "active": lignes = [l for l in lignes if l["surveillance"].actif and not l["surveillance"].date_archivage]
        elif etat_filtre == "inactive": lignes = [l for l in lignes if not l["surveillance"].actif and not l["surveillance"].date_archivage]
        elif etat_filtre == "archivee": lignes = [l for l in lignes if l["surveillance"].date_archivage]
        if anciennete:
            limite = datetime.now() - timedelta(days=anciennete)
            lignes = [l for l in lignes if not l["collecte"] or l["collecte"].date_collecte < limite]
        if modification_filtre == "oui": lignes=[l for l in lignes if l["changements"]]
        elif modification_filtre == "non": lignes=[l for l in lignes if not l["changements"]]
        if erreur_filtre == "oui": lignes=[l for l in lignes if l["collecte"] and l["collecte"].erreurs_sources]
        if source_filtre: lignes=[l for l in lignes if l["collecte"] and source_filtre in l["collecte"].source.casefold()]
        priorite = {"critique":0,"important":1,"informatif":2}
        lignes.sort(key=lambda l: min([priorite.get(a["niveau"],3) for a in l["alertes"]] or [4]))
        limite_obsolete = datetime.now() - timedelta(days=7)
        actions_prioritaires = [
            ligne for ligne in lignes
            if (
                not ligne["collecte"]
                or ligne["collecte"].date_collecte < limite_obsolete
                or (ligne["collecte"] and ligne["collecte"].erreurs_sources)
                or any(
                    a["statut"] == "nouvelle"
                    and a["niveau"] in {"critique", "important"}
                    for a in ligne["alertes"]
                )
            )
        ]
        return render_template(
            "tableau_de_bord.html",
            lignes_modifiees=[ligne for ligne in lignes if ligne["changements"]],
            lignes_sans_modification=[
                ligne for ligne in lignes if not ligne["changements"]
            ],
            nombre_actives=len(actives),
            nombre_inactives=len(societes) - len(actives) - len(archivees),
            nombre_archivees=len(archivees),
            nombre_jamais=sum(l["collecte"] is None for l in lignes),
            nombre_erreurs=sum(bool(l["collecte"] and l["collecte"].erreurs_sources) for l in lignes),
            nombre_alertes=sum(
                any(a["statut"] == "nouvelle" for a in l["alertes"])
                for l in lignes
            ),
            nombre_obsoletes=sum(
                bool(l["collecte"] and l["collecte"].date_collecte < limite_obsolete)
                for l in lignes
            ),
            actions_prioritaires=actions_prioritaires[:10],
            recherche=request.args.get("q", ""), etat_filtre=etat_filtre,
            modification_filtre=modification_filtre, erreur_filtre=erreur_filtre,
            source_filtre=request.args.get("source", ""),
        )

    @application.get("/alertes")
    def alertes():
        niveau = request.args.get("niveau", "")
        statut = request.args.get("statut", "")
        if niveau not in {"", "critique", "important", "informatif"}:
            abort(400)
        if statut not in {"", "nouvelle", "lue", "traitee"}:
            abort(400)
        return render_template(
            "alertes.html",
            alertes=lire_alertes(
                200, niveau=niveau, statut=statut, chemin=chemin_base()
            ),
            niveau_selectionne=niveau,
            statut_selectionne=statut,
            alertes_immediates=alertes_immediates_actives(chemin_base()),
        )

    @application.get("/erreurs")
    def erreurs():
        executions = [
            e for e in lire_executions_veille(100, chemin_base())
            if e["erreurs"] or e["statut"] == "echec"
        ]
        for execution in executions:
            execution["rapport_nom"] = None
            chemin_rapport = Path(execution.get("rapport") or "")
            candidat = DOSSIER_RAPPORTS / chemin_rapport.name
            if chemin_rapport.name and candidat.is_file():
                execution["rapport_nom"] = candidat.name

            erreurs_detaillees: list[tuple[str, str]] = []
            try:
                debut = datetime.fromisoformat(execution["date_debut"])
                fin = datetime.fromisoformat(execution["date_fin"])
                erreurs_detaillees = lire_erreurs_taches_entre(
                    debut, fin + timedelta(seconds=1), chemin_base()
                )
            except (TypeError, ValueError):
                pass

            if not erreurs_detaillees and execution["rapport_nom"]:
                contenu = candidat.read_text(encoding="utf-8", errors="replace")
                for siren, message in re.findall(
                    r"<li><strong>(\d{9})</strong>\s*(?:—|-)\s*(.*?)</li>",
                    contenu,
                    flags=re.DOTALL | re.IGNORECASE,
                ):
                    message = re.sub(r"<br\s*/?>", "\n", message, flags=re.I)
                    message = re.sub(r"<[^>]+>", "", message)
                    erreurs_detaillees.append(
                        (siren, html.unescape(message).strip())
                    )

            entreprises = []
            deja_vues = set()
            for siren, message in erreurs_detaillees:
                if siren in deja_vues:
                    continue
                deja_vues.add(siren)
                societe = lire_societe_surveillee(siren, chemin=chemin_base())
                derniere_collecte = lire_derniere_collecte(siren, chemin_base())
                entreprises.append({
                    "siren": siren,
                    "nom": (
                        getattr(derniere_collecte, "raison_sociale", "")
                        if derniere_collecte else ""
                    ),
                    "message": message,
                    "surveillee": societe is not None,
                })
            execution["entreprises"] = entreprises
        return render_template("erreurs.html", executions=executions)

    @application.post("/erreurs/<siren>/reprendre")
    def reprendre_siren(siren):
        verifier_csrf()
        if not re.fullmatch(r"\d{9}", siren): abort(400)
        subprocess.Popen([sys.executable, "main.py", "--sans-interface", "--source", "multisource", "--siren", siren], cwd=Path(__file__).resolve().parent.parent)
        auditer("relance_collecte", siren)
        flash(f"Reprise du SIREN {siren} lancée.", "succes")
        return redirect(url_for("erreurs"))

    @application.post("/alertes/configuration")
    def modifier_configuration_alertes():
        verifier_csrf()
        active = request.form.get("alertes_immediates") == "1"
        configurer_alertes_immediates(active, chemin_base())
        flash(
            "Alertes immédiates activées." if active
            else "Alertes immédiates désactivées.", "succes",
        )
        return redirect(url_for("alertes"))

    @application.post("/alertes/<identifiant>/statut")
    def modifier_statut_alerte(identifiant: str):
        verifier_csrf()
        try:
            changer_statut_alerte(
                identifiant, request.form.get("statut", ""), chemin_base()
            )
        except ValueError as erreur:
            flash(str(erreur), "erreur")
        except KeyError:
            abort(404)
        else:
            flash("État de l'alerte mis à jour.", "succes")
        siren_retour = request.form.get("siren", "").strip()
        if (
            request.form.get("retour") == "fiche"
            and re.fullmatch(r"\d{9}", siren_retour)
            and lire_societe_surveillee(siren_retour, chemin_base()) is not None
        ):
            return redirect(url_for("historique_societe", siren=siren_retour))
        return redirect(url_for("alertes"))

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

    @application.get("/imports/modele.xlsx")
    def telecharger_modele_import():
        return send_file(
            creer_modele_import_excel(),
            as_attachment=True,
            download_name="modele_import_siren.xlsx",
            mimetype=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )

    @application.get("/automatisation")
    def automatisation():
        executions = lire_executions_veille(20, chemin_base())
        for execution in executions:
            rapport = Path(execution.get("rapport") or "")
            execution["rapport_nom"] = (
                rapport.name
                if rapport.name and (DOSSIER_RAPPORTS / rapport.name).is_file()
                else ""
            )
        progression = lire_taches_recentes(100, chemin_base())
        for tache in progression:
            message = (tache.get("message") or "").casefold()
            tache["categorie_erreur"] = (
                "permanente" if any(code in message for code in ("401", "403", "invalide"))
                else "temporaire" if any(mot in message for mot in ("timeout", "délai", "connexion"))
                else "technique" if tache.get("statut") == "echec" else ""
            )
        planification = lire_etat_tache()
        for cle in ("prochaine", "derniere"):
            valeur = planification.get(cle, "")
            if valeur:
                try:
                    planification[cle] = datetime.fromisoformat(valeur).strftime(
                        "%d/%m/%Y à %H:%M"
                    )
                except ValueError:
                    pass
        return render_template(
            "automatisation.html",
            planification=planification,
            executions=executions,
            progression=progression,
            bilan={
                "succes": sum(e["statut"] == "succes" for e in executions),
                "echecs": sum(e["statut"] == "echec" for e in executions),
                "societes": sum(e["societes"] for e in executions),
                "modifications": sum(e["modifications"] for e in executions),
                "erreurs": sum(e["erreurs"] for e in executions),
            },
        )

    @application.post("/automatisation/configurer")
    def configurer_automatisation():
        verifier_csrf()
        try:
            jour = int(request.form.get("jour", "0"))
            heure = int(request.form.get("heure", "7"))
            minute = int(request.form.get("minute", "0"))
            installer_tache(
                source=request.form.get("source", "multisource"),
                jour_semaine=jour, heure=heure, minute=minute,
            )
        except (OSError, RuntimeError, ValueError) as erreur:
            flash(f"Planification invalide : {erreur}", "erreur")
        else:
            flash("La planification hebdomadaire a été mise à jour.", "succes")
        return redirect(url_for("automatisation"))

    @application.post("/automatisation/lancer")
    def lancer_automatisation():
        verifier_csrf()
        try:
            lancer_tache()
        except (OSError, RuntimeError) as erreur:
            flash(f"Impossible de lancer la collecte : {erreur}", "erreur")
        else:
            flash("La collecte hebdomadaire a été demandée.", "succes")
        return redirect(url_for("automatisation"))

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
        auditer(
            "import_excel", "societes",
            f"{bilan.ajouts} ajout(s), {bilan.mises_a_jour} mise(s) à jour",
        )
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
        chronologie = []
        for entree in historique:
            changements = [
                changement for changement in entree["changements"]
                if changement.champ != "derniere_publication_bodacc"
            ]
            chronologie.append({
                "type": "collecte", "date": entree["collecte"].date_collecte,
                "collecte": entree["collecte"], "changements": changements,
            })
            for changement in entree["changements"]:
                if (changement.champ == "derniere_publication_bodacc"
                        and changement.nouvelle_valeur):
                    chronologie.append({
                        "type": "publication",
                        "date": entree["collecte"].date_collecte,
                        "publication": changement.nouvelle_valeur,
                        "source": (
                            entree["collecte"].provenance.get(
                                "derniere_publication_bodacc"
                            ) or entree["collecte"].source
                        ),
                    })
        for alerte in lire_alertes(500, siren=siren, chemin=chemin_base()):
            try:
                date_alerte = datetime.fromisoformat(
                    alerte["date_detection"].replace("Z", "+00:00")
                ).replace(tzinfo=None)
            except (TypeError, ValueError):
                date_alerte = datetime.min
            chronologie.append({
                "type": "alerte", "date": date_alerte, "alerte": alerte,
            })
        chronologie.sort(key=lambda evenement: evenement["date"], reverse=True)
        derniere_collecte = historique[0]["collecte"] if historique else None
        liens_officiels = {
            "Annuaire des entreprises": "https://annuaire-entreprises.data.gouv.fr/rechercher" f"?terme={siren}",
            "Registre national des entreprises (INPI)": f"https://data.inpi.fr/entreprises/{siren}",
            "Avis de situation Sirene (INSEE)": "https://avis-situation-sirene.insee.fr/",
            "BODACC": f"https://www.bodacc.fr/pages/annonces-commerciales/?q={siren}",
        }
        return render_template(
            "historique_societe.html",
            surveillance=surveillance,
            historique=historique,
            chronologie=chronologie,
            derniere_collecte=derniere_collecte,
            liens_officiels=liens_officiels,
            documents_inpi=lire_documents_inpi(siren, chemin_base()),
            categories_alertes=CATEGORIES_ALERTES,
            preferences_alertes=lire_preferences_alertes(siren, chemin_base()),
            profils=lire_profils(chemin_base()),
            profil_societe=lire_profil_societe(siren, chemin_base()),
            taches_societe=lire_taches(siren=siren, chemin=chemin_base()),
            notes_societe=lire_notes(siren=siren, chemin=chemin_base()),
            liens_societe=lire_liens_societe(siren, chemin_base()),
        )

    @application.get("/documents-inpi/<type_document>/<identifiant>/telecharger")
    def telecharger_document_inpi(type_document: str, identifiant: str):
        if type_document not in {"acte", "bilan", "bilan_saisi"}:
            abort(404)
        document = lire_document_inpi(
            identifiant, type_document, chemin_base()
        )
        if document is None:
            abort(404)
        try:
            contenu, type_mime = SourceINPI().telecharger_document(
                type_document, identifiant
            )
        except (ConnectionError, RuntimeError, ValueError) as erreur:
            flash(f"Téléchargement INPI impossible : {erreur}", "erreur")
            return redirect(url_for(
                "historique_societe", siren=document["siren"]
            ))
        nom = document["nom_document"] or f"{type_document}_{document['siren']}"
        nom = re.sub(r"[^A-Za-z0-9._-]+", "_", nom).strip("._") or "document_inpi"
        est_json = (
            type_document == "bilan_saisi"
            or type_mime == "application/json"
            or contenu.lstrip().startswith((b"{", b"["))
        )
        if est_json:
            try:
                contenu = json.dumps(
                    json.loads(contenu.decode("utf-8")),
                    ensure_ascii=False, indent=2,
                ).encode("utf-8")
            except (UnicodeDecodeError, json.JSONDecodeError):
                flash("Les données de compte reçues de l'INPI sont invalides.", "erreur")
                return redirect(url_for(
                    "historique_societe", siren=document["siren"]
                ))
            type_mime, extension = "application/json", ".json"
        elif contenu.startswith(b"%PDF-"):
            type_mime, extension = "application/pdf", ".pdf"
        else:
            flash("L'INPI n'a pas renvoyé un fichier PDF valide.", "erreur")
            return redirect(url_for(
                "historique_societe", siren=document["siren"]
            ))
        if not nom.lower().endswith(extension):
            nom = str(Path(nom).with_suffix(extension))
        auditer(
            "telechargement_document", document["siren"],
            f"{type_document}:{identifiant}",
        )
        return send_file(
            BytesIO(contenu), mimetype=type_mime,
            as_attachment=True, download_name=nom,
        )

    @application.post("/societes/<siren>/preferences-alertes")
    def modifier_preferences_alertes(siren: str):
        verifier_csrf()
        if lire_societe_surveillee(siren, chemin_base()) is None:
            abort(404)
        try:
            configurer_preferences_alertes(
                siren, request.form.getlist("categories"), chemin_base()
            )
        except ValueError as erreur:
            flash(str(erreur), "erreur")
        else:
            flash("Préférences d'alertes enregistrées.", "succes")
        return redirect(url_for("historique_societe", siren=siren))

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
        return render_template("rapports.html", fichiers=fichiers, societes=lire_societes_surveillees(actives_uniquement=True, chemin=chemin_base()))

    @application.get("/exports/<format_export>")
    def exporter(format_export):
        sirens = request.args.getlist("siren") or [s.siren for s in lire_societes_surveillees(actives_uniquement=True, chemin=chemin_base())]
        if format_export == "xlsx":
            return send_file(exporter_excel(sirens, chemin_base()), as_attachment=True, download_name="veille-siren.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        if format_export == "pdf":
            return send_file(exporter_pdf(sirens, chemin_base()), as_attachment=True, download_name="veille-siren.pdf", mimetype="application/pdf")
        abort(404)

    @application.get("/sauvegardes")
    def sauvegardes():
        conservation = lire_reglages_conservation(chemin_base())
        archives = sorted(DOSSIER_SAUVEGARDES.glob("veille-siren_*.zip"), key=lambda p:p.stat().st_mtime, reverse=True)
        controles = []
        for archive in archives[:conservation["sauvegardes_nombre"]]:
            try:
                controle=verifier_restauration(archive); controle["nom"]=archive.name; controles.append(controle)
            except ErreurSauvegarde as e: controles.append({"archive":str(archive),"nom":archive.name,"integrite":str(e),"date":"","fichiers":0,"tables":0})
        return render_template("sauvegardes.html", sauvegardes=controles)

    @application.post("/sauvegardes/creer")
    def creer_sauvegarde_web():
        verifier_csrf(); conservation=lire_reglages_conservation(chemin_base()); creer_sauvegarde(chemin_base=chemin_base(), conserver=conservation["sauvegardes_nombre"]); auditer("creation_sauvegarde", "base_locale"); flash("Sauvegarde créée et vérifiée.", "succes"); return redirect(url_for("sauvegardes"))

    @application.get("/sauvegardes/<nom>")
    def telecharger_sauvegarde(nom):
        cible = DOSSIER_SAUVEGARDES / Path(nom).name
        if cible.name != nom or not cible.is_file(): abort(404)
        return send_file(cible, as_attachment=True)

    @application.post("/sauvegardes/previsualiser")
    def previsualiser_restauration():
        verifier_csrf(); fichier=request.files.get("archive")
        if not fichier or not fichier.filename.lower().endswith(".zip"): flash("Archive ZIP requise.","erreur"); return redirect(url_for("sauvegardes"))
        DOSSIER_SAUVEGARDES.mkdir(parents=True, exist_ok=True); cible=DOSSIER_SAUVEGARDES/("a_restaurer_"+secrets.token_hex(6)+".zip"); fichier.save(cible)
        try: resume=verifier_restauration(cible)
        except ErreurSauvegarde as e: cible.unlink(missing_ok=True); flash(str(e),"erreur"); return redirect(url_for("sauvegardes"))
        session["restauration_candidate"]=str(cible); return render_template("restauration.html", resume=resume)

    @application.post("/sauvegardes/confirmer")
    def confirmer_restauration():
        verifier_csrf(); archive=Path(session.pop("restauration_candidate", ""))
        if not archive.is_file(): abort(400)
        verifier_restauration(archive)
        with zipfile.ZipFile(archive) as z: donnees=z.read("donnees/veille.sqlite")
        candidate=Path(chemin_base()).with_name("veille_restauree_a_valider.sqlite"); candidate.write_bytes(donnees)
        auditer("preparation_restauration", candidate.name)
        flash(f"Restauration préparée sans écraser la base active : {candidate.name}","succes"); return redirect(url_for("sauvegardes"))

    @application.get("/portefeuilles")
    def portefeuilles():
        return render_template("portefeuilles.html", portefeuilles=lire_portefeuilles(chemin_base()), societes=lire_societes_surveillees(actives_uniquement=True, chemin=chemin_base()), profils=lire_profils(chemin_base()))

    @application.post("/portefeuilles")
    def ajouter_portefeuille():
        verifier_csrf(); creer_portefeuille(request.form.get("nom"),request.form.get("categorie",""),request.form.get("responsable",""),request.form.get("regle","standard"),request.form.get("destinataire",""),chemin_base()); auditer("creation_portefeuille", request.form.get("nom", "")); flash("Portefeuille créé.","succes"); return redirect(url_for("portefeuilles"))

    @application.post("/portefeuilles/<int:identifiant>/destinataire")
    def modifier_destinataire_portefeuille(identifiant):
        verifier_csrf()
        try:
            configurer_destinataire_portefeuille(
                identifiant, request.form.get("destinataire", ""), chemin_base()
            )
        except (KeyError, ValueError) as erreur:
            flash(str(erreur), "erreur")
        else:
            auditer("configuration_destinataire", str(identifiant))
            flash("Adresse de réception enregistrée.", "succes")
        return redirect(url_for("portefeuilles"))

    @application.post("/portefeuilles/<int:identifiant>/affecter")
    def affecter_societe_portefeuille(identifiant):
        verifier_csrf(); affecter_portefeuille(identifiant,request.form.get("siren"),request.form.get("etiquettes",""),request.form.get("contact",""),chemin_base()); return redirect(url_for("portefeuilles"))

    @application.post("/portefeuilles/<int:identifiant>/profil")
    def modifier_profil_portefeuille(identifiant):
        verifier_csrf(); code=request.form.get("profil", "")
        try:
            membres=lire_societes_portefeuille(identifiant,chemin_base())
            for membre in membres: appliquer_profil_societe(membre["siren"],code,chemin=chemin_base())
        except ValueError as erreur: flash(str(erreur),"erreur")
        else: auditer("profil_portefeuille",str(identifiant),code); flash(f"Profil appliqué à {len(membres)} société(s).","succes")
        return redirect(url_for("portefeuilles"))

    @application.get("/portefeuilles/<int:identifiant>/export.csv")
    def exporter_portefeuille(identifiant):
        flux=BytesIO(); texte="SIREN;Etiquettes;Contact interne\n"+"\n".join(f"{x['siren']};{x['etiquettes']};{x['contact_interne']}" for x in lire_societes_portefeuille(identifiant,chemin_base())); flux.write(texte.encode("utf-8-sig")); flux.seek(0)
        return send_file(flux,as_attachment=True,download_name=f"portefeuille_{identifiant}.csv",mimetype="text/csv")

    @application.post("/portefeuilles/<int:identifiant>/import.csv")
    def importer_portefeuille(identifiant):
        verifier_csrf(); fichier=request.files.get("fichier")
        if not fichier: abort(400)
        lignes=csv.DictReader(fichier.stream.read().decode("utf-8-sig").splitlines(),delimiter=";")
        for ligne in lignes: affecter_portefeuille(identifiant,ligne.get("SIREN",""),ligne.get("Etiquettes",""),ligne.get("Contact interne",""),chemin_base())
        flash("Portefeuille importé.","succes"); return redirect(url_for("portefeuilles"))

    @application.post("/collecte/arreter")
    def arreter_collecte():
        verifier_csrf(); demander_arret_collecte(True, chemin_base()); auditer("arret_collecte", "execution_courante"); flash("Arrêt propre demandé ; la collecte s'arrêtera après la société en cours.","succes"); return redirect(url_for("automatisation"))

    @application.get("/documents")
    def documents():
        recherche = request.args.get("q", "").strip()
        type_document = request.args.get("type", "").strip()
        page = max(1, request.args.get("page", 1, type=int) or 1)
        par_page = 30
        if type_document not in {"", "acte", "bilan", "bilan_saisi"}:
            abort(400)
        total = compter_documents_inpi(recherche, type_document, chemin_base())
        nombre_pages = max(1, (total + par_page - 1) // par_page)
        page = min(page, nombre_pages)
        return render_template(
            "documents.html",
            documents=lire_documents_inpi_tous(
                recherche, type_document, par_page, chemin_base(),
                (page - 1) * par_page,
            ),
            recherche=recherche, type_selectionne=type_document,
            total=total, page=page, nombre_pages=nombre_pages,
        )

    @application.get("/recherche")
    def recherche_globale():
        terme = request.args.get("q", "").strip()
        societes, alertes_trouvees, rapports_trouves = [], [], []
        if terme:
            minuscule = terme.casefold()
            for surveillance in lire_societes_surveillees(
                inclure_archivees=True, chemin=chemin_base()
            ):
                collecte = lire_derniere_collecte(
                    surveillance.siren, chemin_base()
                )
                nom = collecte.raison_sociale if collecte else ""
                if minuscule in surveillance.siren or minuscule in nom.casefold():
                    societes.append({
                        "siren": surveillance.siren, "nom": nom,
                        "active": surveillance.actif,
                    })
            alertes_trouvees = [
                alerte for alerte in lire_alertes(500, chemin=chemin_base())
                if minuscule in " ".join(str(v) for v in alerte.values()).casefold()
            ][:50]
            rapports_trouves = [
                fichier for fichier in DOSSIER_RAPPORTS.iterdir()
                if fichier.is_file() and minuscule in fichier.name.casefold()
            ][:30] if DOSSIER_RAPPORTS.is_dir() else []
        return render_template(
            "recherche.html", terme=terme, societes=societes,
            alertes=alertes_trouvees,
            documents=lire_documents_inpi_tous(terme, chemin=chemin_base()) if terme else [],
            rapports=rapports_trouves,
        )

    @application.get("/audit")
    def audit():
        return render_template("audit.html", actions=lire_audit(250, chemin_base()))

    @application.get("/diagnostic")
    def diagnostic():
        controles = diagnostiquer_application(chemin_base())
        return render_template(
            "diagnostic.html", controles=controles,
            pret=all(controle["ok"] for controle in controles),
        )

    @application.get("/configuration")
    def configuration_centrale():
        """Présente les réglages sans transmettre les secrets au navigateur."""
        erreurs_configuration = []

        def lire_sans_erreur(nom, fonction, defaut):
            try:
                return fonction()
            except (OSError, ValueError) as erreur:
                erreurs_configuration.append(f"{nom} : {erreur}")
                return defaut

        cle_insee = lire_sans_erreur("INSEE", lire_cle_insee, "")
        identifiant_inpi, mot_de_passe_inpi = lire_sans_erreur(
            "INPI", lire_identifiants_inpi, ("", "")
        )
        smtp = lire_sans_erreur("SMTP", lire_configuration_smtp, {})
        jeton_notion = lire_sans_erreur("Notion", lire_jeton_notion, "")
        planification = lire_etat_tache()
        conservation = lire_reglages_conservation(chemin_base())
        return render_template(
            "configuration.html",
            connecteurs={
                "annuaire": {"configure": True, "detail": "API publique sans clé"},
                "insee": {"configure": bool(cle_insee), "detail": "Clé DPAPI protégée"},
                "inpi": {
                    "configure": bool(identifiant_inpi and mot_de_passe_inpi),
                    "detail": "Identifiants DPAPI protégés",
                },
                "bodacc": {"configure": True, "detail": "API publique sans clé"},
                "smtp": {"configure": bool(smtp), "detail": "Configuration DPAPI protégée"},
                "notion": {"configure": bool(jeton_notion), "detail": "Jeton DPAPI protégé"},
            },
            identifiant_inpi=identifiant_inpi,
            smtp_public={
                cle: smtp.get(cle, "")
                for cle in (
                    "hote", "port", "utilisateur", "expediteur", "destinataire"
                )
            },
            notion={
                "rapports_veille": lire_cible_notion(
                    "rapports_veille", chemin_base()
                ),
                "rapports_developpement": lire_cible_notion(
                    "rapports_developpement", chemin_base()
                ),
            },
            planification=planification,
            sauvegardes=len(list(DOSSIER_SAUVEGARDES.glob("veille-siren_*.zip"))),
            erreurs_configuration=erreurs_configuration,
            conservation=conservation,
        )

    @application.post("/configuration/conservation")
    def configurer_conservation_web():
        verifier_csrf()
        try:
            configurer_reglages_conservation(
                request.form.get("rapports_jours", ""),
                request.form.get("sauvegardes_nombre", ""),
                chemin_base(),
            )
        except (TypeError, ValueError) as erreur:
            flash(str(erreur), "erreur")
        else:
            auditer("configuration_conservation", "stockage_local")
            flash("Les règles de conservation sont enregistrées.", "succes")
        return redirect(url_for("configuration_centrale"))

    @application.post("/configuration/insee")
    def configurer_insee_web():
        verifier_csrf()
        try:
            proteger_cle_insee(request.form.get("cle_api", ""))
        except (OSError, ValueError) as erreur:
            flash(str(erreur), "erreur")
        else:
            auditer("configuration_connecteur", "INSEE")
            flash("La clé INSEE est protégée dans le coffre Windows.", "succes")
        return redirect(url_for("configuration_centrale"))

    @application.post("/configuration/inpi")
    def configurer_inpi_web():
        verifier_csrf()
        try:
            proteger_identifiants_inpi(
                request.form.get("identifiant", ""),
                request.form.get("mot_de_passe", ""),
            )
        except (OSError, ValueError) as erreur:
            flash(str(erreur), "erreur")
        else:
            auditer("configuration_connecteur", "INPI")
            flash("Les identifiants INPI sont protégés dans le coffre Windows.", "succes")
        return redirect(url_for("configuration_centrale"))

    @application.post("/configuration/smtp")
    def configurer_smtp_web():
        verifier_csrf()
        existante = {}
        try:
            existante = lire_configuration_smtp()
        except (OSError, ValueError):
            pass
        configuration = {
            cle: request.form.get(cle, "").strip()
            for cle in (
                "hote", "port", "utilisateur", "mot_de_passe",
                "expediteur", "destinataire",
            )
        }
        if not configuration["mot_de_passe"]:
            configuration["mot_de_passe"] = existante.get("mot_de_passe", "")
        try:
            proteger_configuration_smtp(configuration)
        except (OSError, ValueError) as erreur:
            flash(str(erreur), "erreur")
        else:
            auditer("configuration_connecteur", "SMTP")
            flash("La configuration SMTP est protégée dans le coffre Windows.", "succes")
        return redirect(url_for("configuration_centrale"))

    @application.post("/configuration/notion")
    def configurer_notion_web():
        verifier_csrf()
        jeton = request.form.get("jeton", "").strip()
        try:
            if jeton:
                proteger_jeton_notion(jeton)
            configurer_cible_notion(
                "rapports_veille", request.form.get("rapports_veille", ""),
                chemin_base(),
            )
            configurer_cible_notion(
                "rapports_developpement",
                request.form.get("rapports_developpement", ""), chemin_base(),
            )
        except (OSError, ValueError) as erreur:
            flash(str(erreur), "erreur")
        else:
            auditer("configuration_connecteur", "Notion")
            flash("La configuration Notion est enregistrée.", "succes")
        return redirect(url_for("configuration_centrale"))

    @application.post("/configuration/tester/<connecteur>")
    def tester_connecteur(connecteur: str):
        verifier_csrf()
        tests = {
            "annuaire": lambda: SourceAnnuaireEntreprises().collecter("356000000"),
            "insee": lambda: SourceINSEE().collecter("356000000"),
            "inpi": lambda: SourceINPI().verifier_connexion(),
            "bodacc": lambda: SourceBODACC().collecter("356000000"),
            "smtp": verifier_connexion_smtp,
            "notion": verifier_connexion_notion,
        }
        if connecteur not in tests:
            abort(404)
        try:
            tests[connecteur]()
        except Exception as erreur:
            auditer("test_connecteur_echec", connecteur)
            flash(f"Échec du test {connecteur.upper()} : {erreur}", "erreur")
        else:
            auditer("test_connecteur_succes", connecteur)
            flash(f"Connexion {connecteur.upper()} validée.", "succes")
        return redirect(url_for("configuration_centrale"))

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

    @application.route("/demarrage", methods=["GET", "POST"])
    def assistant_demarrage():
        progression = lire_progression_demarrage(chemin_base())
        if request.method == "POST":
            verifier_csrf()
            action = request.form.get("action", "suivant")
            try:
                if action == "ajouter_siren":
                    ajouter_societe_surveillee(
                        request.form.get("siren", ""), chemin=chemin_base()
                    )
                    etape = max(progression["etape"], 4)
                elif action == "terminer":
                    enregistrer_progression_demarrage(6, True, chemin_base())
                    auditer("assistant_termine")
                    flash("Assistant terminé. Veille-SIREN est prêt.", "succes")
                    return redirect(url_for("tableau_de_bord"))
                else:
                    etape = int(request.form.get("etape", progression["etape"] + 1))
                enregistrer_progression_demarrage(etape, False, chemin_base())
            except ValueError as erreur:
                flash(str(erreur), "erreur")
            else:
                flash("Progression enregistrée.", "succes")
            return redirect(url_for("assistant_demarrage"))
        return render_template("demarrage.html", progression=progression)

    @application.route("/profils", methods=["GET", "POST"])
    def profils_surveillance():
        if request.method == "POST":
            verifier_csrf()
            try:
                enregistrer_profil(
                    request.form.get("code", ""), request.form.get("nom", ""),
                    request.form.get("description", ""), request.form.get("sources", ""),
                    request.form.getlist("categories"), request.form.get("profondeur", "metadonnees"),
                    request.form.get("notification", "hebdomadaire"), chemin_base(),
                )
            except ValueError as erreur: flash(str(erreur), "erreur")
            else: auditer("profil_enregistre", request.form.get("code", "")); flash("Profil enregistré.", "succes")
            return redirect(url_for("profils_surveillance"))
        return render_template("profils.html", profils=lire_profils(chemin_base()), categories=CATEGORIES_ALERTES)

    @application.post("/societes/<siren>/profil")
    def modifier_profil_societe(siren):
        verifier_csrf()
        if lire_societe_surveillee(siren, chemin_base()) is None: abort(404)
        try: appliquer_profil_societe(siren, request.form.get("profil", ""), chemin=chemin_base())
        except ValueError as erreur: flash(str(erreur), "erreur")
        else: auditer("profil_societe", siren, request.form.get("profil", "")); flash("Profil appliqué.", "succes")
        return redirect(url_for("historique_societe", siren=siren))

    @application.route("/calendrier", methods=["GET", "POST"])
    def calendrier():
        if request.method == "POST":
            verifier_csrf()
            try:
                ajouter_echeance(
                    request.form.get("libelle", ""), request.form.get("date_echeance", ""),
                    request.form.get("siren", ""), commentaire=request.form.get("commentaire", ""),
                    responsable=request.form.get("responsable", ""), rappel_jours=request.form.get("rappel_jours", 7),
                    chemin=chemin_base(),
                )
            except (ValueError, TypeError) as erreur: flash(str(erreur), "erreur")
            else: auditer("echeance_ajoutee", request.form.get("siren", "")); flash("Échéance ajoutée.", "succes")
            return redirect(url_for("calendrier"))
        dates_officielles = [
            {
                "date_echeance": document["date_depot"],
                "libelle": document["libelle"] or document["nom_document"] or "Document INPI",
                "siren": document["siren"],
                "raison_sociale": document["raison_sociale"],
                "origine": "INPI",
            }
            for document in lire_documents_inpi_tous(limite=100, chemin=chemin_base())
            if document.get("date_depot")
        ]
        return render_template(
            "calendrier.html",
            echeances=lire_echeances(chemin=chemin_base()),
            dates_officielles=dates_officielles,
        )

    @application.get("/calendrier.ics")
    def exporter_calendrier():
        return Response(exporter_echeances_ics(lire_echeances(chemin=chemin_base())), mimetype="text/calendar", headers={"Content-Disposition": "attachment; filename=veille-siren.ics"})

    @application.route("/taches", methods=["GET", "POST"])
    def taches():
        if request.method == "POST":
            verifier_csrf()
            try:
                ajouter_tache(
                    request.form.get("titre", ""), request.form.get("siren", ""),
                    request.form.get("description", ""), request.form.get("origine_type", "societe"),
                    request.form.get("origine_id", ""), request.form.get("responsable", ""),
                    request.form.get("date_echeance", ""), request.form.get("priorite", "normale"), chemin_base(),
                )
            except ValueError as erreur: flash(str(erreur), "erreur")
            else: auditer("tache_ajoutee", request.form.get("siren", "")); flash("Tâche ajoutée.", "succes")
            retour=request.form.get("retour_siren", "")
            return redirect(url_for("historique_societe", siren=retour) if retour else url_for("taches"))
        statut=request.args.get("statut", "")
        if statut and statut not in STATUTS_TACHES: abort(400)
        return render_template("taches.html", taches=lire_taches(statut=statut, chemin=chemin_base()), statuts=STATUTS_TACHES, priorites=PRIORITES_TACHES, statut_selectionne=statut)

    @application.post("/taches/<int:identifiant>/statut")
    def modifier_statut_tache(identifiant):
        verifier_csrf()
        try: changer_statut_tache(identifiant, request.form.get("statut", ""), chemin_base())
        except ValueError as erreur: flash(str(erreur), "erreur")
        except KeyError: abort(404)
        else: flash("Tâche mise à jour.", "succes")
        retour=request.form.get("retour_siren", "")
        return redirect(url_for("historique_societe", siren=retour) if retour else url_for("taches"))

    @application.get("/taches.csv")
    def exporter_taches():
        return Response(exporter_taches_csv(lire_taches(chemin=chemin_base())), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=taches-veille-siren.csv"})

    @application.route("/notes", methods=["GET", "POST"])
    def notes():
        if request.method == "POST":
            verifier_csrf()
            try: ajouter_note(request.form.get("contenu", ""), request.form.get("siren", ""), request.form.get("cible_type", "societe"), request.form.get("cible_id", ""), bool(request.form.get("epinglee")), chemin_base())
            except ValueError as erreur: flash(str(erreur), "erreur")
            else: auditer("note_ajoutee", request.form.get("siren", "")); flash("Note ajoutée.", "succes")
            retour=request.form.get("retour_siren", "")
            return redirect(url_for("historique_societe", siren=retour) if retour else url_for("notes"))
        return render_template("notes.html", notes=lire_notes(request.args.get("q", ""), chemin=chemin_base()), recherche=request.args.get("q", ""))

    @application.post("/notes/<int:identifiant>/epingler")
    def modifier_epingle_note(identifiant):
        verifier_csrf(); epingler_note(identifiant, request.form.get("epinglee") == "1", chemin_base()); auditer("note_epinglee", str(identifiant)); return redirect(url_for("notes"))

    @application.get("/notes.csv")
    def exporter_notes():
        return Response(exporter_notes_csv(lire_notes(chemin=chemin_base())),mimetype="text/csv",headers={"Content-Disposition":"attachment; filename=notes-veille-siren.csv"})

    @application.post("/societes/<siren>/lier")
    def lier_societe(siren):
        verifier_csrf()
        try: ajouter_lien_societes(siren, request.form.get("siren_cible", ""), request.form.get("libelle", ""), chemin_base())
        except ValueError as erreur: flash(str(erreur), "erreur")
        else: auditer("societes_liees", siren, request.form.get("siren_cible", "")); flash("Lien ajouté.", "succes")
        return redirect(url_for("historique_societe", siren=siren))

    @application.route("/documents/comparer", methods=["GET", "POST"])
    def comparer_documents():
        resultat=None; erreur=None; siren=request.values.get("siren", "")
        documents=lire_documents_inpi(siren, chemin_base()) if siren else []
        if request.method == "POST":
            verifier_csrf(); selection=request.form.getlist("documents")
            if len(selection)!=2: erreur="Sélectionnez exactement deux documents."
            else:
                try:
                    from pypdf import PdfReader
                    textes=[]
                    for valeur in selection:
                        type_document,identifiant=valeur.split(":",1)
                        contenu,mime=SourceINPI().telecharger_document(type_document,identifiant)
                        if not contenu.startswith(b"%PDF-"): raise ValueError("Un document sélectionné n'est pas un PDF.")
                        lecteur=PdfReader(BytesIO(contenu)); texte="\n".join(page.extract_text() or "" for page in lecteur.pages).strip()
                        if not texte: raise ValueError("PDF scanné non exploitable sans OCR.")
                        textes.append(texte.splitlines())
                    resultat=HtmlDiff(wrapcolumn=100).make_table(textes[0],textes[1],"Document 1","Document 2",context=True,numlines=3)
                except Exception as exc: erreur=str(exc)
        return render_template("comparaison_documents.html", documents=documents, siren=siren, resultat=resultat, erreur=erreur)

    @application.route("/regles", methods=["GET", "POST"])
    def regles_personnalisees():
        simulation=[]
        if request.method == "POST":
            verifier_csrf()
            try:
                enregistrer_regle(request.form.get("nom", ""),request.form.get("champ", ""),request.form.get("operateur", ""),request.form.get("valeur", ""),request.form.get("niveau", "important"),request.form.get("libelle", ""),request.form.get("destinataires", ""),bool(request.form.get("active")),chemin=chemin_base())
            except ValueError as erreur: flash(str(erreur),"erreur")
            else: auditer("regle_ajoutee",request.form.get("nom", "")); flash("Règle enregistrée.","succes")
            return redirect(url_for("regles_personnalisees"))
        identifiant=request.args.get("simuler",type=int); siren=request.args.get("siren","")
        if identifiant and siren:
            regle=next((r for r in lire_regles(chemin_base()) if r["id"]==identifiant),None)
            if regle: simulation=simuler_regle(regle,lire_collectes_societe(siren,chemin_base()))
        return render_template("regles.html",regles=lire_regles(chemin_base()),champs=CHAMPS_REGLES,operateurs=OPERATEURS_REGLES,simulation=simulation)

    @application.route("/modeles-rapports", methods=["GET", "POST"])
    def modeles_rapports():
        if request.method=="POST":
            verifier_csrf()
            try: enregistrer_modele_rapport(request.form.get("nom", ""),request.form.get("portefeuille_id",type=int),request.form.get("periode",7),request.form.getlist("niveaux"),request.form.getlist("sections"),request.form.get("format_sortie","html"),request.form.get("cadence","hebdomadaire"),request.form.get("destinataire",""),False,chemin_base())
            except (ValueError,sqlite3.IntegrityError) as erreur: flash(str(erreur),"erreur")
            else: auditer("modele_rapport_ajoute",request.form.get("nom", "")); flash("Modèle de rapport enregistré.","succes")
            return redirect(url_for("modeles_rapports"))
        return render_template("modeles_rapports.html",modeles=lire_modeles_rapports(chemin_base()),portefeuilles=lire_portefeuilles(chemin_base()))

    @application.get("/modeles-rapports/<int:identifiant>/previsualiser")
    def previsualiser_modele_rapport(identifiant):
        modele=next((m for m in lire_modeles_rapports(chemin_base()) if m["id"]==identifiant),None)
        if modele is None: abort(404)
        return render_template("previsualisation_modele.html",modele=modele)

    @application.post("/modeles-rapports/<int:identifiant>/activation")
    def modifier_activation_modele_rapport(identifiant):
        verifier_csrf()
        try: activer_modele_rapport(identifiant,request.form.get("actif")=="1",chemin_base())
        except KeyError: abort(404)
        auditer("modele_rapport_activation",str(identifiant),request.form.get("actif","0")); flash("Activation du modèle mise à jour.","succes")
        return redirect(url_for("modeles_rapports"))

    @application.get("/api/v1/societes")
    def api_societes():
        return jsonify({"version":"v1","donnees":[{"siren":s.siren,"actif":s.actif,"commentaire":s.commentaire} for s in lire_societes_surveillees(inclure_archivees=True,chemin=chemin_base())]})

    @application.get("/api/v1/alertes")
    def api_alertes(): return jsonify({"version":"v1","donnees":lire_alertes(500,chemin=chemin_base())})
    @application.get("/api/v1/documents")
    def api_documents(): return jsonify({"version":"v1","donnees":lire_documents_inpi_tous(limite=500,decalage=0,chemin=chemin_base())})
    @application.get("/api/v1/portefeuilles")
    def api_portefeuilles(): return jsonify({"version":"v1","donnees":lire_portefeuilles(chemin_base())})
    @application.get("/api/v1/executions")
    def api_executions(): return jsonify({"version":"v1","donnees":lire_executions_veille(100,chemin_base())})
    @application.get("/api")
    def documentation_api(): return render_template("api.html")

    return application
