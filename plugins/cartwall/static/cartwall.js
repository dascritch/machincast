// Le cartouchier (https://github.com/dascritch/machincast/issues/512) : chaque bouton prend sa couleur, demande son
// action à /api/v1/plugins/cartwall/press et dit la réponse ; la liste des boutons se relit toutes les RELECTURE
// millisecondes, pour griser ceux qui ne peuvent pas servir. L'antenne en direct est tenue par /static/intranet.js.
"use strict";

(() => {
	const RELECTURE = 5000;
	const zone = document.getElementById("cartouchier");
	if (zone === null) {
		return;
	}
	const etat = document.getElementById("cartouchier-etat");
	const actif = zone.dataset.actif === "1";
	const dire = (texte) => {
		if (etat !== null) {
			etat.textContent = texte;
		}
	};

	for (const bouton of zone.querySelectorAll(".carte")) {
		bouton.style.backgroundColor = bouton.dataset.couleur;
		bouton.addEventListener("click", async () => {
			bouton.classList.add("envoi");
			try {
				const reponse = await fetch("/api/v1/plugins/cartwall/press", {
					method: "POST",
					credentials: "same-origin",
					headers: { "content-type": "application/json" },
					body: JSON.stringify({ button: Number(bouton.dataset.bouton) }),
				});
				if (reponse.status === 401) {
					window.location.assign("/login");
					return;
				}
				const valeur = await reponse.json();
				dire(valeur.done ? `✓ ${bouton.textContent}` : `✗ ${bouton.textContent} : ${valeur.reason || valeur.error}`);
			} catch {
				dire(`✗ ${bouton.textContent}`);
			} finally {
				bouton.classList.remove("envoi");
			}
		});
	}

	const relire = async () => {
		try {
			const reponse = await fetch("/api/v1/plugins/cartwall/buttons", { credentials: "same-origin", cache: "no-store" });
			if (!reponse.ok) {
				return;
			}
			for (const donnee of (await reponse.json()).buttons) {
				const bouton = zone.querySelector(`[data-bouton="${donnee.id}"]`);
				if (bouton !== null) {
					bouton.disabled = !actif || !donnee.usable;
					bouton.title = donnee.reason || "";
				}
			}
		} catch {
			// Le serveur injoignable : les boutons restent tels quels, et la liste se relit au tour suivant.
		}
	};
	window.setInterval(relire, RELECTURE);
})();
