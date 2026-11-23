# language: fr
Fonctionnalité: Les gabarits Jinja2 de l'intranet, surchargeables par un plugin
	En tant que développeur d'un plugin,
	je veux que les pages de l'intranet viennent de gabarits Jinja2,
	afin de pouvoir en surcharger ou en remplacer un depuis mon plugin.

	https://github.com/dascritch/machincast/issues/597, ticket enfant de
	https://github.com/dascritch/machincast/issues/596. Les gabarits sont dans machincast/intranet/templates/ ; un
	plugin chargé en fournit un du même nom dans son templates/, le premier plugin l'emporte, et l'original reste
	joignable sous « machincast/<nom> ».

	Contexte:
		Étant donné les comptes de l'intranet :
			| nom   | mot de passe    | rôle        | état  |
			| regie | tisane-au-micro | actions API | actif |
		Et une session valide de « regie », de jeton « jeton-de-regie »
		Et l'API de l'intranet sur la base de test, à « 2026-11-20 10:00:00 »

	Scénario: Sans plugin, l'intranet a ses propres gabarits
		Alors les gabarits de l'intranet sont « banner », « calendar », « documentation », « forbidden », « home », « layout », « live », « login », « page », « validation »
		Quand je demande à l'API « GET /documentation », avec le jeton « jeton-de-regie »
		Alors la page contient « <h1>Documentation</h1> »

	Scénario: Un plugin remplace un gabarit de l'intranet
		Étant donné le plugin « affiche » qui fournit le gabarit « documentation.html.jinja » : « {% extends "layout.html.jinja" %}{% block main %}<p>Notre documentation</p>{% endblock %} »
		Quand je demande à l'API « GET /documentation », avec le jeton « jeton-de-regie »
		Alors la page contient « <p>Notre documentation</p> »
		Et la page ne contient pas « <h1>Documentation</h1> »

	Scénario: Un gabarit surchargé étend l'original, sous « machincast/ »
		Étant donné le plugin « affiche » qui fournit le gabarit « documentation.html.jinja » : « {% extends "machincast/documentation.html.jinja" %}{% block main %}{{ super() }}<p>Et la nôtre</p>{% endblock %} »
		Quand je demande à l'API « GET /documentation », avec le jeton « jeton-de-regie »
		Alors la page contient « <h1>Documentation</h1> »
		Et la page contient « <p>Et la nôtre</p> »

	Scénario: Le premier plugin chargé l'emporte
		Étant donné le plugin « affiche » qui fournit le gabarit « documentation.html.jinja » : « {% extends "layout.html.jinja" %}{% block main %}<p>Affiche</p>{% endblock %} »
		Et le plugin « bandeau » qui fournit le gabarit « documentation.html.jinja » : « {% extends "layout.html.jinja" %}{% block main %}<p>Bandeau</p>{% endblock %} »
		Quand je demande à l'API « GET /documentation », avec le jeton « jeton-de-regie »
		Alors la page contient « <p>Affiche</p> »
		Et la page ne contient pas « <p>Bandeau</p> »

	Scénario: Un gabarit surchargé garde l'échappement automatique
		Étant donné le plugin « affiche » qui fournit le gabarit « documentation.html.jinja » : « {% extends "layout.html.jinja" %}{% block main %}<p>{{ guide }}</p><p>{{ "<b>gras</b>" }}</p>{% endblock %} »
		Quand je demande à l'API « GET /documentation », avec le jeton « jeton-de-regie »
		Alors la page contient « <p>&lt;b&gt;gras&lt;/b&gt;</p> »

	Scénario: Les textes des gabarits sont traduits, et relevés par le catalogue
		Quand je demande à l'API « GET / », avec le jeton « jeton-de-regie »
		Alors la page contient « <h2>Derniers sonores diffusés</h2> »
		Et le catalogue relève « Last sounds on air » dans « machincast/intranet/templates/live.html.jinja »

	Scénario: Un plugin rend ses propres gabarits
		Étant donné le plugin « affiche » qui fournit le gabarit « affiche.html.jinja » : « <p>{{ _("Next event") }} : {{ nom }}</p> »
		Alors un plugin rend « affiche.html.jinja » avec « nom » valant « <Journal> » : « <p>Événement suivant : &lt;Journal&gt;</p> »
