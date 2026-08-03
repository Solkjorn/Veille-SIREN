document.querySelectorAll(".declencheur-rapport").forEach((bouton) => {
  bouton.addEventListener("click", () => {
    const rapport = document.getElementById(bouton.dataset.cible);
    const ouvert = bouton.getAttribute("aria-expanded") === "true";
    bouton.setAttribute("aria-expanded", String(!ouvert));
    rapport.hidden = ouvert;
  });
});

document.querySelectorAll("form[data-confirmation]").forEach((formulaire) => {
  formulaire.addEventListener("submit", (evenement) => {
    if (!window.confirm(formulaire.dataset.confirmation)) {
      evenement.preventDefault();
    }
  });
});

const lienEvitement = document.querySelector('.lien-evitement');
const contenuPrincipal = document.getElementById('contenu-principal');
if (lienEvitement && contenuPrincipal) {
  lienEvitement.addEventListener('click', () => {
    contenuPrincipal.focus();
  });
}
