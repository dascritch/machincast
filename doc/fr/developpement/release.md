# Publier une version

Chaque version publiée de MachinCast a son tag git, `v<version>`, sa release GitHub, avec son archive `.tar.gz`, et ses informations à jour pour l'équipe de l'antenne et l'administrateur du poste ([#208](https://github.com/dascritch/machincast/issues/208), [#41](https://github.com/dascritch/machincast/issues/41)). Les versions d'avant 1.0 se publient en pré-version (`prerelease`).

## Ce que voit l'équipe de l'antenne

- **Aide → Version** dit la version installée, et sa date de publication (`MachinCast 0.9.0, publiée le 2026-10-28, commit 1a2b3c4.`). Installée depuis le dépôt git, après le commit de la release, elle compte aussi les modifications qui ont suivi (`…, plus 3 modifications, la dernière le 2026-10-30 à 15:00, commit 5d6e7f8.`). Sous ce texte, les nouveautés de la version.
- **Aide → Documentation** ouvre le guide de l'antenne du tag de la release, quand le code installé est celui de la release ; celui de `main` sinon.
- **Les nouveautés** de la version installée s'ouvrent une fois, au premier lancement de l'interface qui la découvre, pour chaque compte (la version vue est retenue dans `~/.config/machincast/vues.ini`).

Tout vient du tag `v<version>` et des fichiers des nouveautés, un par langue ([#369](https://github.com/dascritch/machincast/issues/369)) : `src/machincast/interface/news.fr.md` en français, `src/machincast/interface/news.md` en anglais (`machincast.interface.version`). L'interface montre celui de la langue de la session, `news.<langue>.md`, et `news.md` pour une langue qui n'a pas le sien.

## Préparer la version

Sur une branche `release/<version>`, en un seul commit, « Version <version> », lié aux tickets de la release :

1. **Le numéro**, dans `pyproject.toml`. Avant 1.0 : `0.<mineure>.<correctif>`.
2. **Les tickets résolus** depuis la release précédente (ou depuis le début du dépôt, pour la première) :

   ```bash
   gh api --paginate "repos/dascritch/machincast/issues?state=closed&since=<date de la release précédente>T00:00:00Z" \
   	--jq '.[] | select(.pull_request == null) | "\(.number)\t\(.closed_at)\t\(.user.login)\t\(.title)"'
   ```

   Garder ceux fermés depuis la release précédente comme résolus, pas ceux fermés comme doublons ou abandonnés (`state_reason` : `not_planned`). Les personnes qui ont ouvert un ticket ou l'ont commenté se lisent par `.user.login` et par les commentaires de chaque ticket.
3. **`RELEASE.fr.md`**, à la racine, puis sa traduction anglaise, `RELEASE.md` : une nouvelle section en tête, avant celle de la version précédente, titrée `## <version> — <AAAA-MM-JJ>`. Les tickets résolus y sont classés par sujet (antenne, programmation, sonores et indexation, interface, installation et administration…), chacun avec son lien. Elle se termine par les remerciements à tous ceux qui ont signalé un problème, demandé une amélioration ou fait un retour. **Pour la première release, avant 1.0**, ne parler que des fonctionnalités créées : ni le design, ni les améliorations du code ou de la documentation.
4. **Les nouveautés de l'interface**, `src/machincast/interface/news.fr.md`, puis sa traduction anglaise, `src/machincast/interface/news.md`, comme `RELEASE.fr.md` et `RELEASE.md` : la même section, `## <version> — <AAAA-MM-JJ>`, en tête, en quelques lignes pour l'équipe de l'antenne : ce qui change pour elle, sans numéro de ticket ni vocabulaire technique. Une langue qui a son catalogue de traduction peut avoir ses nouveautés, `news.<langue>.md` ; sans elles, sa session montre celles en anglais.
5. **`README.fr.md`** : la ligne `**Version <version>**, publiée le <AAAA-MM-JJ>`, avec le lien vers `RELEASE.fr.md` ; et `README.md`, la ligne `**Version <version>**, released on <AAAA-MM-JJ>`, avec le lien vers `RELEASE.md`.
6. **Le guide de l'antenne**, `doc/fr/utilisateur`, relu d'un bout à l'autre ([#128](https://github.com/dascritch/machincast/issues/128)) : chaque fonctionnalité de la version y est, sans rien de technique.
7. **Ses captures d'écran**, refaites par `Machin dev-screenshots` ([Captures d'écran du guide de l'antenne](poste.md#captures-décran-du-guide-de-lantenne)), puis relues. Elles ne se refont qu'à la préparation d'une release, sauf si le responsable du projet le demande expressément.
8. **La traduction anglaise** ([#352](https://github.com/dascritch/machincast/issues/352)) : les documents de premier niveau (`README.md`, `INSTALL.md`, `TROUBLESHOOTING.md`, `CONTRIBUTING.md`, `RELEASE.md`) reprennent ce qui a changé dans leur source française, `*.fr.md`, depuis la release précédente, et `doc/en/` est retraduit de `doc/fr/`. C'est le seul moment où la documentation se retraduit.
9. **Les vérifications**, dans le ticket « Tests, revue de code et performances » ouvert pour cette demande de release ([Quels tests lancer](../regles/tests.md#quels-tests-lancer)) : `Machin dev-test` complet, puis les scénarios `@release`, qui ne tournent pas avec `pytest` : `.venv/bin/pytest -m release` ([Scénarios à lancer avant une version](../../../TROUBLESHOOTING.fr.md#scénarios-à-lancer-avant-une-version)). Les relancer aussi après toute mise à jour de GStreamer ou de libsoup.

Le scénario « Les informations des versions publiées concordent », dans `tests/features/documentation.feature`, vérifie que les nouveautés, en anglais et en français, `RELEASE.md`, `README.md` et `pyproject.toml` donnent la même version, à la même date.

## Publier

Une fois le commit « Version <version> » mergé dans `main` :

```bash
git checkout main && git pull
git tag -a v<version> -m "MachinCast <version>"
git push origin v<version>
git archive --format=tar.gz --prefix=machincast-<version>/ --output=machincast-<version>.tar.gz v<version>
```

Puis créer la release GitHub du tag, intitulée `MachinCast <version>`, en pré-version avant 1.0, avec la section de `RELEASE.md` pour notes et l'archive en pièce jointe.
