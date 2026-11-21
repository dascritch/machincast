# Aide sur l'onglet API

![L'onglet API, ses éléments numérotés comme ci-dessous](../../captures/aide/api.png)

L'onglet API gère les comptes qui peuvent se connecter à l'intranet et à l'API ([#537](https://github.com/dascritch/machincast/issues/537)).
Les numéros renvoient à l'image ; **Aide → Aide contextuelle**, ou <kbd>F1</kbd>, donne chacune de ces aides en infobulle, sur l'élément lui-même.

1. **Comptes** (`users`) : chaque compte, son rôle, son état, `actif` ou `désactivé`, et sa date de création ; les actions qui suivent agissent sur le compte choisi.
2. **➕ Nouveau compte…** (`new_user`) : demande un nom, un mot de passe d'au moins 12 caractères, sa confirmation et un rôle ; le nom ne prend que des lettres sans accent, des chiffres, le point, le tiret et le souligné.
3. **Rôle** (`role`) : `consulter` donne l'intranet et l'API en lecture ; `actions API` de même, et les actions à venir ; le changement vaut aussitôt.
4. **Changer le mot de passe…** (`change_password`) : un nouveau mot de passe, confirmé ; l'ancien n'est pas demandé, et il n'y a pas d'autre récupération. Toutes les sessions du compte prennent fin : c'est le geste à faire quand un mot de passe a fuité.
5. **Désactiver** (`disable`) : le compte ne se connecte plus, et toutes ses sessions prennent fin ; le bouton devient **Réactiver**, qui n'en fait revivre aucune.
6. **❌ Supprimer…** (`delete`) : supprime le compte, après confirmation ; ses sessions prennent fin.
7. **Sessions** (`sessions`) : celles du compte choisi, la plus récente en tête : `à valider` au pupitre, `valide` jusqu'à sa limite, ou `invalide` ; ouverte par la mire de l'`intranet`, ou générée au `pupitre` ; avec l'adresse et le navigateur du poste distant ([#539](https://github.com/dascritch/machincast/issues/539)).
8. **➕ Nouvelle session API…** (`new_session`) : une session valide aussitôt, pour un outil qui lit l'API ; son jeton n'est montré qu'une fois.
9. **Invalider la session** (`invalidate_session`) : la session choisie ne sert plus.

Une connexion à distance à valider s'annonce au-dessus des onglets, dans un bandeau orange : le compte, l'adresse, le navigateur et l'heure limite ; **Accepter** montre le code à 6 chiffres à donner, **Refuser** la ferme.

Pour aller plus loin : [Comptes de l'intranet](../../administration/configuration.md#comptes-de-lintranet).
