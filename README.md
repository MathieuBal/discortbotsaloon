Bot Saloon

Bot Saloon est un bot Discord qui gère les stocks et la comptabilité d'un saloon. Le bot permet aux utilisateurs de vendre des produits et d'en acheter, et maintient une trace de toutes les transactions effectuées.

Prérequis
Pour exécuter le bot, vous aurez besoin des éléments suivants :

Python 3.8 ou version supérieure
Les bibliothèques Python discord.py et asyncio
Un compte Discord et une application Discord enregistrée
Un fichier de configuration JSON avec un jeton Discord valide
Installation
Clonez le dépôt GitHub sur votre ordinateur en utilisant la commande git clone https://github.com/MathieuBal/discortbotsaloon.

Ouvrez le projet dans PyCharm et installez les bibliothèques requises en exécutant la commande pip install -r requirements.txt dans le terminal.

Ajoutez un fichier config.json à la racine du projet. Ce fichier doit contenir les informations de configuration suivantes :

{
  "token": "Votre jeton Discord ici"
}

Exécutez le script en utilisant la commande python botsaloon.py dans le terminal.

Invitez le bot à votre serveur Discord en utilisant le lien d'invitation généré par l'application Discord.

Utilisation
Une fois le bot connecté à votre serveur, vous pouvez effectuer les actions suivantes :

Cliquez sur le bouton "Vente" pour vendre un produit. Sélectionnez une catégorie, choisissez un produit, puis entrez la quantité. Un ticket de caisse sera généré avec le prix total.
Cliquez sur le bouton "Achat" pour acheter un produit. Cette fonctionnalité n'est pas encore implémentée.
Les stocks sont automatiquement mis à jour chaque fois qu'une transaction est effectuée.
Les informations sur les finances sont automatiquement mises à jour chaque fois qu'une transaction est effectuée.
Les informations sur les finances sont affichées dans le canal de comptabilité.
Les informations sur les stocks sont affichées dans le canal de stockage.
N'oubliez pas que vous pouvez personnaliser le bot pour répondre aux besoins de votre serveur en modifiant le code.
