import ctypes
import os
from ctypes import wintypes
from pathlib import Path


DOSSIER_SECRETS = Path(
    os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")
) / "Veille-SIREN" / "secrets"
FICHIER_CLE_INSEE = DOSSIER_SECRETS / "insee-api-key.bin"


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob_depuis_octets(donnees: bytes):
    tampon = ctypes.create_string_buffer(donnees)
    blob = _DataBlob(len(donnees), ctypes.cast(tampon, ctypes.POINTER(ctypes.c_byte)))
    return blob, tampon


def _verifier_windows() -> None:
    if os.name != "nt":
        raise OSError("Le stockage DPAPI est disponible uniquement sous Windows.")


def proteger_cle_insee(cle_api: str) -> Path:
    """Chiffre la clé avec le compte Windows courant et l'enregistre hors du dépôt."""
    _verifier_windows()
    cle_api = cle_api.strip()
    if not cle_api:
        raise ValueError("La clé API INSEE est vide.")

    entree, tampon = _blob_depuis_octets(cle_api.encode("utf-8"))
    sortie = _DataBlob()
    succes = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(entree),
        "Veille-SIREN - clé API INSEE",
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

    FICHIER_CLE_INSEE.parent.mkdir(parents=True, exist_ok=True)
    FICHIER_CLE_INSEE.write_bytes(donnees_chiffrees)
    return FICHIER_CLE_INSEE


def lire_cle_insee() -> str:
    """Déchiffre la clé liée au compte Windows courant, si elle existe."""
    if os.name != "nt" or not FICHIER_CLE_INSEE.exists():
        return ""

    entree, tampon = _blob_depuis_octets(FICHIER_CLE_INSEE.read_bytes())
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
