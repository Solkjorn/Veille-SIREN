"""Fonctions locales des phases 27 à 34 de l'espace de travail juridique."""

import csv
import hashlib
import io
import json
import sqlite3
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

from config import BASE_SQLITE
from modules.base_donnees import initialiser_base, enregistrer_audit
from modules.comparaison import CATEGORIES_ALERTES


STATUTS_TACHES = ("a_faire", "en_cours", "en_attente", "terminee")
PRIORITES_TACHES = ("basse", "normale", "haute", "critique")
CHAMPS_REGLES = (
    "raison_sociale", "forme_juridique", "capital", "statut", "adresse",
    "dirigeant", "derniere_publication_bodacc", "dernier_changement",
)
OPERATEURS_REGLES = ("contient", "egal", "change", "commence_par", "termine_par")


def _lignes(requete, parametres=(), chemin=BASE_SQLITE):
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        connexion.row_factory = sqlite3.Row
        return [dict(x) for x in connexion.execute(requete, parametres).fetchall()]


def lire_progression_demarrage(chemin=BASE_SQLITE):
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        lignes = dict(connexion.execute(
            "SELECT cle,valeur FROM configuration WHERE cle LIKE 'assistant_%'"
        ).fetchall())
        table_societes = connexion.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='societes_surveillees'"
        ).fetchone()
        societes = (
            connexion.execute(
                "SELECT COUNT(*) FROM societes_surveillees WHERE date_archivage IS NULL"
            ).fetchone()[0]
            if table_societes else 0
        )
    etape = int(lignes.get("assistant_etape", "1"))
    return {"etape": etape, "termine": lignes.get("assistant_termine") == "1", "base_neuve": societes == 0}


def enregistrer_progression_demarrage(etape, termine=False, chemin=BASE_SQLITE):
    etape = max(1, min(6, int(etape)))
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion, connexion:
        connexion.executemany(
            "INSERT OR REPLACE INTO configuration(cle,valeur) VALUES (?,?)",
            (("assistant_etape", str(etape)), ("assistant_termine", "1" if termine else "0")),
        )
    return lire_progression_demarrage(chemin)


def lire_profils(chemin=BASE_SQLITE):
    return _lignes("SELECT * FROM profils_surveillance ORDER BY id", chemin=chemin)


def enregistrer_profil(code, nom, description, sources, categories, profondeur, notification, chemin=BASE_SQLITE):
    code = str(code).strip().casefold().replace(" ", "_")
    if not code or not nom.strip():
        raise ValueError("Le code et le nom du profil sont obligatoires.")
    categories = [c for c in categories if c in CATEGORIES_ALERTES]
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion, connexion:
        connexion.execute(
            "INSERT INTO profils_surveillance(code,nom,description,sources,categories,profondeur_documentaire,notification) "
            "VALUES(?,?,?,?,?,?,?) ON CONFLICT(code) DO UPDATE SET nom=excluded.nom,description=excluded.description,"
            "sources=excluded.sources,categories=excluded.categories,profondeur_documentaire=excluded.profondeur_documentaire,notification=excluded.notification",
            (code, nom.strip(), description.strip(), sources.strip(), ",".join(categories), profondeur, notification),
        )
    return code


def appliquer_profil_societe(siren, code, exceptions=None, chemin=BASE_SQLITE):
    profils = {p["code"]: p for p in lire_profils(chemin)}
    if code not in profils:
        raise ValueError("Profil de surveillance inconnu.")
    exceptions = exceptions or {}
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion, connexion:
        connexion.execute(
            "INSERT OR REPLACE INTO profils_societes(siren,profil_code,exceptions) VALUES(?,?,?)",
            (str(siren), code, json.dumps(exceptions, ensure_ascii=False)),
        )
        categories = set(filter(None, profils[code]["categories"].split(",")))
        connexion.execute("DELETE FROM preferences_alertes WHERE siren=?", (str(siren),))
        connexion.executemany(
            "INSERT INTO preferences_alertes(siren,categorie,active) VALUES(?,?,?)",
            [(str(siren), c, int(c in categories)) for c in CATEGORIES_ALERTES],
        )
    return profils[code]


def lire_profil_societe(siren, chemin=BASE_SQLITE):
    lignes = _lignes(
        "SELECT p.*,ps.exceptions FROM profils_societes ps JOIN profils_surveillance p ON p.code=ps.profil_code WHERE ps.siren=?",
        (str(siren),), chemin,
    )
    return lignes[0] if lignes else None


def ajouter_echeance(libelle, date_echeance, siren="", origine="interne", officielle=False, commentaire="", responsable="", rappel_jours=7, chemin=BASE_SQLITE):
    date.fromisoformat(str(date_echeance))
    if not str(libelle).strip():
        raise ValueError("Le libellé de l'échéance est obligatoire.")
    initialiser_base(chemin)
    maintenant = datetime.now().isoformat(timespec="seconds")
    with closing(sqlite3.connect(chemin)) as connexion, connexion:
        curseur = connexion.execute(
            "INSERT INTO echeances(siren,libelle,date_echeance,origine,officielle,commentaire,responsable,rappel_jours,date_creation) VALUES(?,?,?,?,?,?,?,?,?)",
            (str(siren), libelle.strip(), str(date_echeance), origine, int(officielle), commentaire.strip(), responsable.strip(), max(0, int(rappel_jours)), maintenant),
        )
        return curseur.lastrowid


def lire_echeances(siren="", chemin=BASE_SQLITE):
    filtre, params = (" WHERE e.siren=?", (str(siren),)) if siren else ("", ())
    return _lignes(
        "SELECT e.*,COALESCE((SELECT raison_sociale FROM collectes c WHERE c.siren=e.siren ORDER BY id DESC LIMIT 1),'') raison_sociale FROM echeances e"
        + filtre + " ORDER BY date_echeance,id", params, chemin,
    )


def exporter_echeances_ics(echeances):
    lignes = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Veille-SIREN//FR", "CALSCALE:GREGORIAN"]
    for e in echeances:
        texte = str(e["libelle"]).replace("\n", " ").replace(",", "\\,")
        lignes += ["BEGIN:VEVENT", f"UID:echeance-{e['id']}@veille-siren.local", f"DTSTART;VALUE=DATE:{e['date_echeance'].replace('-', '')}", f"SUMMARY:{texte}", f"DESCRIPTION:Origine : {e['origine']}", "END:VEVENT"]
    return "\r\n".join(lignes + ["END:VCALENDAR", ""])


def ajouter_tache(titre, siren="", description="", origine_type="societe", origine_id="", responsable="", date_echeance="", priorite="normale", chemin=BASE_SQLITE):
    if not str(titre).strip() or priorite not in PRIORITES_TACHES:
        raise ValueError("Titre ou priorité de tâche invalide.")
    if date_echeance:
        date.fromisoformat(str(date_echeance))
    maintenant = datetime.now().isoformat(timespec="seconds")
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion, connexion:
        curseur = connexion.execute(
            "INSERT INTO taches_internes(siren,titre,description,origine_type,origine_id,responsable,date_echeance,priorite,date_creation,date_modification) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (str(siren), titre.strip(), description.strip(), origine_type, str(origine_id), responsable.strip(), str(date_echeance), priorite, maintenant, maintenant),
        )
        connexion.execute("INSERT INTO historique_taches(tache_id,nouveau_statut,date_changement) VALUES(?,?,?)", (curseur.lastrowid, "a_faire", maintenant))
        return curseur.lastrowid


def lire_taches(statut="", siren="", chemin=BASE_SQLITE):
    clauses, params = [], []
    if statut: clauses.append("t.statut=?"); params.append(statut)
    if siren: clauses.append("t.siren=?"); params.append(str(siren))
    filtre = " WHERE " + " AND ".join(clauses) if clauses else ""
    return _lignes("SELECT t.*,COALESCE((SELECT raison_sociale FROM collectes c WHERE c.siren=t.siren ORDER BY id DESC LIMIT 1),'') raison_sociale FROM taches_internes t" + filtre + " ORDER BY CASE priorite WHEN 'critique' THEN 0 WHEN 'haute' THEN 1 WHEN 'normale' THEN 2 ELSE 3 END,date_echeance,id", params, chemin)


def changer_statut_tache(identifiant, statut, chemin=BASE_SQLITE):
    if statut not in STATUTS_TACHES:
        raise ValueError("Statut de tâche invalide.")
    initialiser_base(chemin); maintenant=datetime.now().isoformat(timespec="seconds")
    with closing(sqlite3.connect(chemin)) as connexion, connexion:
        ligne=connexion.execute("SELECT statut FROM taches_internes WHERE id=?",(int(identifiant),)).fetchone()
        if not ligne: raise KeyError("Tâche inconnue.")
        connexion.execute("UPDATE taches_internes SET statut=?,date_modification=? WHERE id=?",(statut,maintenant,int(identifiant)))
        connexion.execute("INSERT INTO historique_taches(tache_id,ancien_statut,nouveau_statut,date_changement) VALUES(?,?,?,?)",(int(identifiant),ligne[0],statut,maintenant))
    enregistrer_audit("tache.statut", str(identifiant), f"{ligne[0]} -> {statut}", chemin=chemin)


def exporter_taches_csv(taches):
    flux=io.StringIO(); writer=csv.writer(flux,delimiter=";")
    writer.writerow(("SIREN","Société","Tâche","Responsable","Échéance","Priorité","État"))
    for t in taches: writer.writerow((t["siren"],t["raison_sociale"],t["titre"],t["responsable"],t["date_echeance"],t["priorite"],t["statut"]))
    return "\ufeff"+flux.getvalue()


def ajouter_note(contenu, siren="", cible_type="societe", cible_id="", epinglee=False, chemin=BASE_SQLITE):
    if not str(contenu).strip(): raise ValueError("La note ne peut pas être vide.")
    maintenant=datetime.now().isoformat(timespec="seconds"); initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion, connexion:
        return connexion.execute("INSERT INTO notes_travail(siren,cible_type,cible_id,contenu,epinglee,date_creation,date_modification) VALUES(?,?,?,?,?,?,?)",(str(siren),cible_type,str(cible_id),contenu.strip(),int(epinglee),maintenant,maintenant)).lastrowid


def lire_notes(recherche="", siren="", chemin=BASE_SQLITE):
    clauses,params=[],[]
    if recherche: clauses.append("contenu LIKE ?"); params.append(f"%{recherche}%")
    if siren: clauses.append("siren=?"); params.append(str(siren))
    filtre=" WHERE "+" AND ".join(clauses) if clauses else ""
    return _lignes("SELECT * FROM notes_travail"+filtre+" ORDER BY epinglee DESC,date_creation DESC",params,chemin)


def epingler_note(identifiant, epinglee, chemin=BASE_SQLITE):
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion, connexion:
        connexion.execute("UPDATE notes_travail SET epinglee=?,date_modification=? WHERE id=?",(int(epinglee),datetime.now().isoformat(timespec="seconds"),int(identifiant)))


def exporter_notes_csv(notes):
    flux=io.StringIO(); writer=csv.writer(flux,delimiter=";")
    writer.writerow(("SIREN","Cible","Note","Épinglée","Date"))
    for n in notes: writer.writerow((n["siren"],n["cible_type"],n["contenu"],"Oui" if n["epinglee"] else "Non",n["date_creation"]))
    return "\ufeff"+flux.getvalue()


def ajouter_lien_societes(source, cible, libelle="", chemin=BASE_SQLITE):
    if source==cible: raise ValueError("Une société ne peut pas être liée à elle-même.")
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion, connexion:
        connexion.execute("INSERT OR REPLACE INTO liens_societes VALUES(?,?,?,?)",(str(source),str(cible),libelle.strip(),datetime.now().isoformat(timespec="seconds")))


def lire_liens_societe(siren, chemin=BASE_SQLITE):
    return _lignes("SELECT * FROM liens_societes WHERE siren_source=? OR siren_cible=? ORDER BY date_creation DESC",(str(siren),str(siren)),chemin)


def enregistrer_regle(nom, champ, operateur, valeur, niveau, libelle, destinataires="", active=False, identifiant=None, chemin=BASE_SQLITE):
    if champ not in CHAMPS_REGLES or operateur not in OPERATEURS_REGLES or niveau not in ("critique","important","informatif"):
        raise ValueError("Paramètres de règle invalides.")
    if operateur != "change" and not str(valeur).strip(): raise ValueError("La valeur de comparaison est obligatoire.")
    if operateur in {"contient","commence_par","termine_par"} and len(str(valeur).strip()) < 2:
        raise ValueError("La valeur est trop large : saisissez au moins deux caractères.")
    initialiser_base(chemin); maintenant=datetime.now().isoformat(timespec="seconds")
    with closing(sqlite3.connect(chemin)) as connexion, connexion:
        doublon=connexion.execute("SELECT id FROM regles_personnalisees WHERE champ=? AND operateur=? AND LOWER(valeur)=LOWER(?) AND id<>?",(champ,operateur,str(valeur).strip(),int(identifiant or 0))).fetchone()
        if doublon: raise ValueError("Une règle équivalente existe déjà.")
        if identifiant:
            connexion.execute("UPDATE regles_personnalisees SET nom=?,champ=?,operateur=?,valeur=?,niveau=?,libelle=?,destinataires=?,active=?,version=version+1,date_modification=? WHERE id=?",(nom,champ,operateur,valeur,niveau,libelle,destinataires,int(active),maintenant,int(identifiant)))
            return int(identifiant)
        return connexion.execute("INSERT INTO regles_personnalisees(nom,champ,operateur,valeur,niveau,libelle,destinataires,active,date_modification) VALUES(?,?,?,?,?,?,?,?,?)",(nom,champ,operateur,valeur,niveau,libelle,destinataires,int(active),maintenant)).lastrowid


def lire_regles(chemin=BASE_SQLITE): return _lignes("SELECT * FROM regles_personnalisees ORDER BY id DESC",chemin=chemin)


def evaluer_regle(regle, ancienne, nouvelle):
    avant=str(getattr(ancienne,regle["champ"],"") if ancienne else "").casefold()
    apres=str(getattr(nouvelle,regle["champ"],"") if nouvelle else "").casefold(); valeur=str(regle["valeur"]).casefold()
    return {"contient": valeur in apres, "egal": apres==valeur, "change": avant!=apres, "commence_par": apres.startswith(valeur), "termine_par": apres.endswith(valeur)}[regle["operateur"]]


def simuler_regle(regle, collectes):
    resultats=[]; precedente=None
    for collecte in collectes:
        if evaluer_regle(regle,precedente,collecte): resultats.append(collecte)
        precedente=collecte
    return resultats


def enregistrer_modele_rapport(nom, portefeuille_id, periode, niveaux, sections, format_sortie, cadence, destinataire, actif=False, chemin=BASE_SQLITE):
    if format_sortie not in ("html","pdf","xlsx") or cadence not in ("hebdomadaire","mensuelle"):
        raise ValueError("Format ou cadence invalide.")
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion, connexion:
        return connexion.execute("INSERT INTO modeles_rapports(nom,portefeuille_id,periode,niveaux,sections,format_sortie,cadence,destinataire,actif) VALUES(?,?,?,?,?,?,?,?,?)",(nom.strip(),portefeuille_id or None,str(periode),",".join(niveaux),",".join(sections),format_sortie,cadence,destinataire.strip(),int(actif))).lastrowid


def lire_modeles_rapports(chemin=BASE_SQLITE):
    return _lignes("SELECT m.*,COALESCE(p.nom,'Toutes les sociétés') portefeuille FROM modeles_rapports m LEFT JOIN portefeuilles p ON p.id=m.portefeuille_id ORDER BY m.id DESC",chemin=chemin)


def activer_modele_rapport(identifiant, actif, chemin=BASE_SQLITE):
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion, connexion:
        curseur=connexion.execute("UPDATE modeles_rapports SET actif=? WHERE id=?",(int(actif),int(identifiant)))
        if curseur.rowcount != 1: raise KeyError("Modèle inconnu.")


def enregistrer_generation(modele_id, statut, chemin_fichier="", destinataire="", message="", date_reference=None, chemin=BASE_SQLITE):
    instant=date_reference or datetime.now(); cle=f"{modele_id}|{instant.date().isoformat()}|{destinataire}"; empreinte=hashlib.sha256(cle.encode()).hexdigest()
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion, connexion:
        curseur=connexion.execute("INSERT OR IGNORE INTO generations_rapports(modele_id,statut,chemin,destinataire,message,date_generation,empreinte) VALUES(?,?,?,?,?,?,?)",(int(modele_id),statut,str(chemin_fichier),destinataire,message,instant.isoformat(timespec="seconds"),empreinte))
        return bool(curseur.rowcount)


def generation_deja_enregistree(modele_id, destinataire="", date_reference=None, chemin=BASE_SQLITE):
    instant=date_reference or datetime.now(); cle=f"{modele_id}|{instant.date().isoformat()}|{destinataire}"; empreinte=hashlib.sha256(cle.encode()).hexdigest()
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        return connexion.execute("SELECT 1 FROM generations_rapports WHERE empreinte=?",(empreinte,)).fetchone() is not None
