# La normalisation du niveau

Les sonores n'ont pas tous le même niveau : un morceau masterisé fort côtoie un jingle discret ou une archive faible.
Le plugin « Normalisation du niveau » porte chaque sonore à la même sonie, mesurée selon l'EBU R128, sans que sa crête dépasse jamais un plafond ([#43](https://github.com/dascritch/machincast/issues/43)) : l'antenne reste homogène, sans dépendre seulement du compresseur matériel.

## La mesure

L'audit complet de Machin indexer (`Machin indexer --full-audit`, ou l'analyse d'un sonore au dernier moment) mesure chaque fichier : sa **sonie** intégrée, en LUFS, et sa **crête**, le plus fort échantillon, en dBFS.
Un sonore jamais audité n'est pas mesuré : il joue avec son seul ajustement manuel.

## Le régler

Menu **Plugins**, **Normalisation du niveau** :

- **Sonie visée**, un curseur en LUFS : −23 par défaut, la valeur de l'EBU R128 ; une station plus forte vise souvent −16 ;
- **Plafond de crête**, un curseur en dBFS : −1 par défaut ; la crête d'un sonore, gain compris, ne le dépasse jamais ;
- **Enregistrer** les écrit dans `machincast.toml` ; relancer la diffusion et l'indexation pour qu'elles les prennent.

## Les réglages d'une banque

Dans la fiche d'une banque, l'encart **Niveau** permet de lui donner sa propre **Sonie visée** et son propre **Plafond de crête** : cocher la case, puis régler le curseur.
Ils remplacent ceux du plugin pour les sonores que la banque fournit, par exemple une banque de publicités plus forte, ou de musique de nuit plus douce.
Décochée, la banque suit le réglage du plugin, que son curseur grisé montre.

## Le gain d'un sonore

Machin player joue chaque fichier avec un gain : la sonie visée moins sa sonie mesurée, plus son ajustement manuel, ramené si sa crête dépasserait le plafond.
Un stream n'en a pas.

Dans la fiche d'un sonore, l'encart **Niveau**, sous l'encart **Fichier**, se déplie d'un clic sur son titre ; il montre sa mesure, son **Ajustement manuel**, en dB, et le gain appliqué, puis celui de chaque banque qui a ses propres réglages.
L'ajustement ne peut pas dépasser la valeur qui garde la crête sous le plafond, le plus bas de celui du plugin et de ceux des banques qui contiennent le sonore.
Si une mise à jour du fichier, mesurée par l'audit complet suivant, le faisait dépasser, il est ramené à la plus forte valeur permise, et le log le dit, en incident « niveau ajusté ».
