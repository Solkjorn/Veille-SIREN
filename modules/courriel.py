import smtplib
from datetime import date
from email.message import EmailMessage
from pathlib import Path

from modules.secrets_windows import lire_configuration_smtp


class ErreurCourriel(RuntimeError):
    """Erreur lisible d'envoi de la synthèse."""


def verifier_connexion_smtp(
    configuration: dict | None = None, client=smtplib.SMTP
) -> bool:
    """Teste TLS et l'authentification sans envoyer de message."""
    configuration = configuration or lire_configuration_smtp()
    if not configuration:
        raise ErreurCourriel("Aucune configuration SMTP n'est enregistrée.")
    try:
        with client(
            configuration["hote"], int(configuration["port"]), timeout=30
        ) as smtp:
            smtp.starttls()
            smtp.login(configuration["utilisateur"], configuration["mot_de_passe"])
    except (OSError, smtplib.SMTPException, ValueError, KeyError) as erreur:
        raise ErreurCourriel(f"Échec de la connexion SMTP : {erreur}") from erreur
    return True


def _envoyer_message(message, configuration: dict, client) -> None:
    try:
        with client(configuration["hote"], int(configuration["port"]), timeout=30) as smtp:
            smtp.starttls()
            smtp.login(configuration["utilisateur"], configuration["mot_de_passe"])
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException, ValueError, KeyError) as erreur:
        raise ErreurCourriel(f"Échec de l'envoi SMTP : {erreur}") from erreur


def envoyer_synthese(
    chemin_rapport: Path,
    configuration: dict | None = None,
    client=smtplib.SMTP,
    destinataire: str | None = None,
    objet: str | None = None,
    date_reference: date | None = None,
) -> None:
    """Envoie la synthèse HTML au destinataire SMTP configuré."""
    if configuration is None:
        configuration = lire_configuration_smtp()
    if not configuration:
        raise ErreurCourriel("Aucune configuration SMTP n'est enregistrée.")
    chemin_rapport = Path(chemin_rapport)
    contenu = chemin_rapport.read_text(encoding="utf-8")
    message = EmailMessage()
    message["Subject"] = objet or (
        "Synthèse hebdomadaire Veille-SIREN — "
        f"{(date_reference or date.today()).strftime('%d/%m/%Y')}"
    )
    message["From"] = configuration["expediteur"]
    message["To"] = destinataire or configuration["destinataire"]
    message.set_content(
        "La synthèse hebdomadaire Veille-SIREN est disponible en version HTML."
    )
    message.add_alternative(contenu, subtype="html")
    _envoyer_message(message, configuration, client)


def envoyer_alerte_critique(
    siren: str, raison_sociale: str, changement,
    configuration: dict | None = None, client=smtplib.SMTP,
) -> None:
    """Envoie une alerte immédiate pour un événement critique nouveau."""
    if configuration is None:
        configuration = lire_configuration_smtp()
    if not configuration:
        raise ErreurCourriel("Aucune configuration SMTP n'est enregistrée.")
    societe = raison_sociale or siren
    message = EmailMessage()
    message["Subject"] = f"Alerte critique Veille-SIREN — {societe}"
    message["From"] = configuration["expediteur"]
    message["To"] = configuration["destinataire"]
    message.set_content(
        f"Société : {societe}\nSIREN : {siren}\nÉvénement : {changement.regle}\n"
        f"Avant : {changement.ancienne_valeur or 'Non renseigné'}\n"
        f"Après : {changement.nouvelle_valeur or 'Non renseigné'}"
    )
    _envoyer_message(message, configuration, client)
