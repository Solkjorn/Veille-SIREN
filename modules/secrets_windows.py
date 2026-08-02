import ctypes
import getpass
import json
import os
from ctypes import wintypes
from pathlib import Path


DOSSIER_SECRETS = Path(
    os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")
) / "Veille-SIREN" / "secrets"
FICHIER_CLE_INSEE = DOSSIER_SECRETS / "insee-api-key.bin"
FICHIER_IDENTIFIANTS_INPI = DOSSIER_SECRETS / "inpi-credentials.bin"
FICHIER_JETON_NOTION = DOSSIER_SECRETS / "notion-token.bin"
FICHIER_SMTP = DOSSIER_SECRETS / "smtp-config.bin"


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob_depuis_octets(donnees: bytes):
    tampon = ctypes.create_string_buffer(donnees)
    blob = _DataBlob(len(donnees), ctypes.cast(tampon, ctypes.POINTER(ctypes.c_byte)))
    return blob, tampon


def _verifier_windows() -> None:
    if os.name != "nt":
        raise OSError("Le stockage DPAPI est disponible uniquement sous Windows.")


def _proteger_texte(texte: str, chemin: Path, description: str) -> Path:
    _verifier_windows()
    entree, tampon = _blob_depuis_octets(texte.encode("utf-8"))
    sortie = _DataBlob()
    succes = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(entree),
        description,
        None,
        None,
        None,
        0,
        ctypes.byref(sortie),
    )
    if not succes:
        raise ctypes.WinError()
    try:
        donnees_chiffrees = ctypes.string_at(sortie.pbData, sortie.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(sortie.pbData)
        del tampon

    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(donnees_chiffrees)
    return chemin


def _lire_texte(chemin: Path) -> str:
    if os.name != "nt" or not chemin.exists():
        return ""

    entree, tampon = _blob_depuis_octets(chemin.read_bytes())
    sortie = _DataBlob()
    succes = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(entree), None, None, None, None, 0, ctypes.byref(sortie)
    )
    if not succes:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(sortie.pbData, sortie.cbData).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(sortie.pbData)
        del tampon


def proteger_cle_insee(cle_api: str) -> Path:
    """Chiffre la clé INSEE avec le compte Windows courant."""
    cle_api = cle_api.strip()
    if not cle_api:
        raise ValueError("La clé API INSEE est vide.")
    return _proteger_texte(
        cle_api, FICHIER_CLE_INSEE, "Veille-SIREN - clé API INSEE"
    )


def lire_cle_insee() -> str:
    """Déchiffre la clé INSEE, si elle existe."""
    return _lire_texte(FICHIER_CLE_INSEE)


def proteger_identifiants_inpi(identifiant: str, mot_de_passe: str) -> Path:
    """Chiffre les identifiants INPI avec le compte Windows courant."""
    identifiant = identifiant.strip()
    if not identifiant or not mot_de_passe:
        raise ValueError("L'identifiant et le mot de passe INPI sont requis.")
    contenu = json.dumps(
        {"identifiant": identifiant, "mot_de_passe": mot_de_passe},
        ensure_ascii=False,
    )
    return _proteger_texte(
        contenu,
        FICHIER_IDENTIFIANTS_INPI,
        "Veille-SIREN - identifiants INPI",
    )


def lire_identifiants_inpi() -> tuple[str, str]:
    """Déchiffre les identifiants INPI, s'ils existent."""
    contenu = _lire_texte(FICHIER_IDENTIFIANTS_INPI)
    if not contenu:
        return "", ""
    try:
        donnees = json.loads(contenu)
    except (json.JSONDecodeError, TypeError) as erreur:
        raise ValueError("Le coffre INPI local est illisible.") from erreur
    return donnees.get("identifiant", ""), donnees.get("mot_de_passe", "")


def proteger_jeton_notion(jeton: str) -> Path:
    """Chiffre le jeton Notion avec le compte Windows courant."""
    jeton = jeton.strip()
    if not jeton:
        raise ValueError("Le jeton Notion est vide.")
    return _proteger_texte(
        jeton, FICHIER_JETON_NOTION, "Veille-SIREN - jeton Notion"
    )


def lire_jeton_notion() -> str:
    """Déchiffre le jeton Notion, si le coffre existe."""
    return _lire_texte(FICHIER_JETON_NOTION)


def configurer_jeton_notion() -> Path:
    """Demande le jeton sans l'afficher puis alimente le coffre Notion."""
    jeton = getpass.getpass("Jeton d'intégration Notion : ")
    return proteger_jeton_notion(jeton)


def proteger_configuration_smtp(configuration: dict) -> Path:
    """Chiffre la configuration SMTP complète avec Windows DPAPI."""
    champs = ("hote", "port", "utilisateur", "mot_de_passe", "expediteur", "destinataire")
    if not all(str(configuration.get(champ, "")).strip() for champ in champs):
        raise ValueError("Tous les paramètres SMTP sont requis.")
    contenu = json.dumps(configuration, ensure_ascii=False)
    return _proteger_texte(contenu, FICHIER_SMTP, "Veille-SIREN - SMTP")


def lire_configuration_smtp() -> dict:
    """Déchiffre la configuration SMTP, si elle existe."""
    contenu = _lire_texte(FICHIER_SMTP)
    if not contenu:
        return {}
    try:
        return json.loads(contenu)
    except json.JSONDecodeError as erreur:
        raise ValueError("Le coffre SMTP local est illisible.") from erreur


def configurer_smtp() -> Path:
    """Demande les paramètres SMTP et protège le mot de passe."""
    configuration = {
        "hote": input("Serveur SMTP : ").strip(),
        "port": input("Port SMTP (souvent 587) : ").strip(),
        "utilisateur": input("Identifiant SMTP : ").strip(),
        "mot_de_passe": getpass.getpass("Mot de passe SMTP ou mot de passe d'application : "),
        "expediteur": input("Adresse d'expédition : ").strip(),
        "destinataire": input("Adresse destinataire : ").strip(),
    }
    return proteger_configuration_smtp(configuration)


def configurer_identifiants_inpi() -> Path:
    """Demande les secrets sans les afficher puis alimente le coffre INPI."""
    identifiant = input("Adresse e-mail INPI : ").strip()
    mot_de_passe = getpass.getpass("Mot de passe INPI : ")
    return proteger_identifiants_inpi(identifiant, mot_de_passe)


if __name__ == "__main__":
    import argparse

    analyseur = argparse.ArgumentParser()
    analyseur.add_argument(
        "service", choices=("inpi", "notion", "smtp"), nargs="?", default="inpi"
    )
    service = analyseur.parse_args().service
    if service == "smtp":
        chemin = configurer_smtp()
        print(f"Configuration SMTP protégée dans : {chemin}")
    elif service == "notion":
        chemin = configurer_jeton_notion()
        print(f"Jeton Notion protégé dans : {chemin}")
    else:
        chemin = configurer_identifiants_inpi()
        print(f"Identifiants INPI protégés dans : {chemin}")
