from io import BytesIO

from openpyxl import Workbook

from modules.base_donnees import lire_collectes_societe


def exporter_excel(sirens, chemin_base):
    classeur = Workbook()
    feuille = classeur.active
    feuille.title = "Synthese"
    feuille.append(["SIREN", "Raison sociale", "Statut", "Capital", "Adresse", "Dernière collecte"])
    for siren in sirens:
        historique = lire_collectes_societe(siren, chemin_base)
        if historique:
            s = historique[-1]
            feuille.append([s.siren, s.raison_sociale, s.statut, s.capital, s.adresse, s.date_collecte.isoformat(timespec="minutes")])
    flux = BytesIO()
    classeur.save(flux)
    flux.seek(0)
    return flux


def exporter_pdf(sirens, chemin_base):
    lignes = ["Veille-SIREN - Synthese"]
    for siren in sirens:
        historique = lire_collectes_societe(siren, chemin_base)
        if historique:
            s = historique[-1]
            lignes.append(f"{s.siren} | {s.raison_sociale} | {s.statut}")
    texte = "\n".join(lignes).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    commandes = ["BT /F1 11 Tf 50 790 Td"]
    for index, ligne in enumerate(texte.splitlines()):
        if index:
            commandes.append("0 -16 Td")
        commandes.append(f"({ligne.encode('latin-1', 'replace').decode('latin-1')}) Tj")
    commandes.append("ET")
    stream = "\n".join(commandes).encode("latin-1")
    objets = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>", b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>", b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    pdf = bytearray(b"%PDF-1.4\n")
    positions = [0]
    for i, objet in enumerate(objets, 1):
        positions.append(len(pdf)); pdf.extend(f"{i} 0 obj\n".encode() + objet + b"\nendobj\n")
    xref = len(pdf); pdf.extend(f"xref\n0 {len(objets)+1}\n0000000000 65535 f \n".encode())
    for pos in positions[1:]: pdf.extend(f"{pos:010d} 00000 n \n".encode())
    pdf.extend(f"trailer << /Size {len(objets)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return BytesIO(bytes(pdf))
