document.querySelectorAll(".buyable").forEach(element => {
    element.addEventListener("click", () => cardBought(element));
});

function cardBought(card) {
    window.location.href =`/${window.location.toString().split('/')[3]}/cardbought/${card.id}`;
}