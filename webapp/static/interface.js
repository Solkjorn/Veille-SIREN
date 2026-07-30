document.querySelectorAll(".declencheur-rapport").forEach((bouton) => {
  bouton.addEventListener("click", () => {
    const rapport = document.getElementById(bouton.dataset.cible);
    const ouvert = bouton.getAttribute("aria-expanded") === "true";
    bouton.setAttribute("aria-expanded", String(!ouvert));
    rapport.hidden = ouvert;
  });
});
