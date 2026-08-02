import argparse
import getpass
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from html import escape
from pathlib import Path


NOM_TACHE = "Veille-SIREN - collecte hebdomadaire"
JOURS_XML = (
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
)


def prochaine_limite(
    heure: int = 7,
    maintenant: datetime | None = None,
    jour_semaine: int = 0,
    minute: int = 0,
) -> str:
    """Retourne la prochaine occurrence hebdomadaire demandée."""
    if jour_semaine not in range(7) or heure not in range(24) or minute not in range(60):
        raise ValueError("Le jour ou l'heure de planification est invalide.")
    maintenant = maintenant or datetime.now()
    jours = (jour_semaine - maintenant.weekday()) % 7
    cible = (maintenant + timedelta(days=jours)).replace(
        hour=heure, minute=minute, second=0, microsecond=0
    )
    if cible <= maintenant:
        cible += timedelta(days=7)
    return cible.isoformat(timespec="seconds")


def construire_xml_tache(
    python: Path,
    projet: Path,
    source: str = "pappers",
    utilisateur: str | None = None,
    jour_semaine: int = 0,
    heure: int = 7,
    minute: int = 0,
) -> str:
    """Construit une tâche hebdomadaire avec rattrapage après indisponibilité."""
    python = Path(python).resolve()
    projet = Path(projet).resolve()
    utilisateur = utilisateur or getpass.getuser()
    arguments = (
        f'"{projet / "main.py"}" --execution-hebdomadaire '
        f'--sans-interface --source {source}'
    )
    return f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Veille juridique hebdomadaire des sociétés.</Description></RegistrationInfo>
  <Triggers><CalendarTrigger><StartBoundary>{prochaine_limite(heure, jour_semaine=jour_semaine, minute=minute)}</StartBoundary><Enabled>true</Enabled>
    <ScheduleByWeek><WeeksInterval>1</WeeksInterval><DaysOfWeek><{JOURS_XML[jour_semaine]} /></DaysOfWeek></ScheduleByWeek>
  </CalendarTrigger></Triggers>
  <Principals><Principal id="Auteur"><UserId>{escape(utilisateur)}</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><StartWhenAvailable>true</StartWhenAvailable>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate><ExecutionTimeLimit>PT2H</ExecutionTimeLimit><Enabled>true</Enabled>
    <WakeToRun>true</WakeToRun><RestartOnFailure><Interval>PT5M</Interval><Count>2</Count></RestartOnFailure>
  </Settings>
  <Actions Context="Auteur"><Exec><Command>{escape(str(python))}</Command><Arguments>{escape(arguments)}</Arguments>
    <WorkingDirectory>{escape(str(projet))}</WorkingDirectory></Exec></Actions>
</Task>'''


def installer_tache(
    python: Path = Path(sys.executable),
    projet: Path = Path(__file__).resolve().parents[1],
    source: str = "pappers",
    jour_semaine: int = 0,
    heure: int = 7,
    minute: int = 0,
) -> None:
    """Crée ou remplace la tâche dans le Planificateur Windows."""
    xml = construire_xml_tache(
        python, projet, source, jour_semaine=jour_semaine,
        heure=heure, minute=minute,
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", encoding="utf-16", delete=False
    ) as fichier:
        fichier.write(xml)
        chemin_xml = Path(fichier.name)
    try:
        subprocess.run(
            ["schtasks", "/Create", "/TN", NOM_TACHE, "/XML", str(chemin_xml), "/F"],
            check=True,
        )
    finally:
        chemin_xml.unlink(missing_ok=True)


def lire_etat_tache() -> dict:
    """Lit l'état de la tâche sans dépendre de la langue de Windows."""
    script = (
        f"$t=Get-ScheduledTask -TaskName '{NOM_TACHE}';"
        f"$i=Get-ScheduledTaskInfo -TaskName '{NOM_TACHE}';"
        "[pscustomobject]@{Etat=[string]$t.State;"
        "Derniere=$i.LastRunTime.ToString('o');"
        "Prochaine=$i.NextRunTime.ToString('o');"
        "Resultat=$i.LastTaskResult}|ConvertTo-Json -Compress"
    )
    try:
        resultat = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            check=True, capture_output=True, text=True, encoding="utf-8",
        )
        donnees = json.loads(resultat.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as erreur:
        return {"disponible": False, "erreur": str(erreur)}
    return {
        "disponible": True,
        "etat": donnees.get("Etat", "Inconnu"),
        "derniere": donnees.get("Derniere", ""),
        "prochaine": donnees.get("Prochaine", ""),
        "resultat": donnees.get("Resultat"),
    }


def lancer_tache() -> None:
    """Demande au Planificateur Windows de lancer la chaîne immédiatement."""
    try:
        subprocess.run(["schtasks", "/Run", "/TN", NOM_TACHE], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as erreur:
        raise RuntimeError("La tâche Windows n'a pas pu démarrer.") from erreur


def main() -> int:
    analyseur = argparse.ArgumentParser()
    analyseur.add_argument("--installer", action="store_true")
    analyseur.add_argument("--source", default="pappers")
    analyseur.add_argument("--jour", type=int, choices=range(7), default=0)
    analyseur.add_argument("--heure", type=int, choices=range(24), default=7)
    analyseur.add_argument("--minute", type=int, choices=range(60), default=0)
    arguments = analyseur.parse_args()
    if not arguments.installer:
        analyseur.print_help()
        return 0
    installer_tache(
        source=arguments.source, jour_semaine=arguments.jour,
        heure=arguments.heure, minute=arguments.minute,
    )
    print(
        f"Tâche installée : {NOM_TACHE} "
        f"({JOURS_XML[arguments.jour]} {arguments.heure:02d}:"
        f"{arguments.minute:02d}, rattrapage activé)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
