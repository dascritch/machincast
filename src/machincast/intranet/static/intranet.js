// L'accueil de « Machin intranet », en direct (https://github.com/dascritch/machincast/issues/541) : il relit
// /api/v1/live toutes les RELECTURE millisecondes, et tient ses décomptes à la seconde, à l'heure du serveur ; durées
// et décomptes en HH:MM:SS, comme machincast.intranet.home.duration
// (https://github.com/dascritch/machincast/issues/579). Sans JavaScript, la page montre ce qu'en a dit le serveur à
// son chargement.
"use strict";

(() => {
	const RELECTURE = 5000;
	const heure = new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
	const heureCourte = new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit" });
	let ecart = 0;

	const element = (id) => document.getElementById(id);
	const ecrire = (id, texte) => {
		const cible = element(id);
		if (cible !== null) {
			cible.textContent = texte;
		}
	};
	const moment = (valeur) => (valeur ? new Date(valeur) : null);
	const court = (valeur) => {
		const date = moment(valeur);
		return date === null ? "—" : heureCourte.format(date);
	};
	const nommer = (son) => {
		if (!son) {
			return "—";
		}
		const nom = [son.artist, son.title].filter((partie) => partie).join(" – ");
		return nom || son.location || "—";
	};
	const deuxChiffres = (nombre) => String(nombre).padStart(2, "0");
	const duree = (valeur) => {
		if (valeur === null || valeur === undefined) {
			return "—";
		}
		const total = Math.floor(Math.max(0, valeur));
		const heures = Math.floor(total / 3600);
		const minutes = Math.floor((total % 3600) / 60);
		return `${deuxChiffres(heures)}:${deuxChiffres(minutes)}:${deuxChiffres(total % 60)}`;
	};

	const poser = (id, limite) => {
		const cible = element(id);
		if (cible !== null) {
			cible.dataset.limite = limite || "";
		}
	};

	const montrer = (direct) => {
		ecart = new Date(direct.time).getTime() - Date.now();
		ecrire("texte-public", direct.public_text || "—");
		const etat = element("etat");
		if (etat !== null) {
			etat.className = `etat ${direct.state}`;
			// data-dead-air se lit dataset.deadAir.
			const cle = direct.state.replace(/_(.)/g, (_tout, lettre) => lettre.toUpperCase());
			etat.textContent = etat.dataset[cle] || direct.state;
		}
		const evenements = direct.events || {};
		const actuel = evenements.current;
		const suivant = evenements.next;
		ecrire("evenement-nom", actuel ? actuel.name : "—");
		ecrire("evenement-debut", actuel ? court(actuel.start) : "—");
		ecrire("evenement-fin", actuel ? court(actuel.end) : "—");
		poser("evenement-reste", actuel ? actuel.end : null);
		ecrire("suivant-nom", suivant ? suivant.name : "—");
		ecrire("suivant-debut", suivant ? court(suivant.start) : "—");
		ecrire("suivant-fin", suivant ? court(suivant.end) : "—");
		ecrire("sonore-nom", nommer(direct.current));
		ecrire("sonore-duree", duree(direct.current ? direct.current.duration : null));
		poser("sonore-reste", direct.current ? direct.current.estimated_end : null);
		const prochain = (direct.next || [])[0];
		ecrire("prochain-nom", nommer(prochain));
		ecrire("prochain-duree", duree(prochain ? prochain.duration : null));
		poser("prochain-attente", prochain ? prochain.estimated_start : null);
		const liste = element("airplay");
		if (liste !== null) {
			liste.replaceChildren(
				...(direct.previous || []).map((passage) => {
					const ligne = document.createElement("li");
					ligne.textContent = `${court(passage.start)} ${nommer(passage)}`;
					return ligne;
				}),
			);
		}
	};

	const decompter = () => {
		const maintenant = Date.now() + ecart;
		ecrire("heure", heure.format(new Date(maintenant)));
		for (const cible of document.querySelectorAll("[data-limite]")) {
			const limite = moment(cible.dataset.limite);
			cible.textContent = limite === null ? "—" : duree(Math.max(0, (limite.getTime() - maintenant) / 1000));
		}
		window.requestAnimationFrame(decompter);
	};

	const relire = async () => {
		try {
			const reponse = await fetch("/api/v1/live", { credentials: "same-origin", cache: "no-store" });
			if (reponse.status === 401) {
				window.location.assign("/login");
				return;
			}
			if (reponse.ok) {
				montrer(await reponse.json());
			}
		} catch {
			// Le serveur injoignable : la page garde ce qu'elle montre, et réessaie.
		}
	};

	if (element("direct") !== null) {
		relire();
		window.setInterval(relire, RELECTURE);
		window.requestAnimationFrame(decompter);
	}
})();
