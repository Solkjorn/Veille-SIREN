def siren_valide(siren: str) -> bool:
    """
    Vérifie qu'un SIREN est valide à l'aide de l'algorithme de Luhn.
    """

    siren = str(siren).strip()

    # Vérifie que le SIREN contient exactement 9 chiffres
    if len(siren) != 9 or not siren.isdigit():
        return False

    total = 0

    # Parcours des chiffres de droite à gauche
    for i, chiffre in enumerate(reversed(siren)):
        n = int(chiffre)

        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9

        total += n

    return total % 10 == 0