# Vérifications effectuées

Date : 9 octobre 2026.

Les tests ont été réalisés localement dans des environnements Debian avec systemd. Docker a servi uniquement à isoler ces tests ; la plateforme déployée par Ansible utilise des services natifs. Aucun VPS utilisateur n'a été contacté.

| Vérification | Résultat |
|---|---|
| Syntaxe des playbooks deploy, maintenance et verify | Réussite |
| Inventory d'exemple | Groupe knowledge correctement chargé |
| Connexion Ansible SSH et sudo par mot de passe, clés désactivées | Réussite sur Debian 13 |
| Installation de Forgejo, SQLite, MkDocs et Nginx | Réussite sur Debian 12 et 13, arm64 |
| Certificat TLS auto-signé dans l'environnement de test | Site accessible en HTTPS |
| Documentation sans authentification | HTTP 401 |
| Documentation avec authentification | HTTP 200 |
| Relance Ansible sur Debian 12 et 13 | Zéro changement, aucune erreur |
| Clone du dépôt via HTTPS et mot de passe | Réussite |
| Push d'un document | Publication par le timer sans commande de build |
| Push contenant un lien interne cassé | Échec du build et conservation de la dernière version correcte |
| Push correctif après échec | Publication automatique rétablie |
| Commit inchangé | Aucun rebuild |
| Hooks/configuration Python ajoutés au dépôt documentaire | Non exécutés par le constructeur |
| Lien symbolique dans les documents | Rejeté, site précédent conservé |
| Unités systemd | Vérification avec systemd-analyze réussie |
| Échec volontaire de sauvegarde | Forgejo redémarre malgré l’erreur |
| Sauvegarde locale | Archive créée après arrêt cohérent de Forgejo et service redémarré |
| Extraction de l'archive | SQLite integrity_check=ok, commit Git et site récupérés |

Quatre tests automatisés exécutent de vrais builds MkDocs (`tests/test_publish.py`) ; ils vérifient publication/no-op, échec puis reprise, non-exécution de hooks et rejet des liens symboliques.

La validation couvre le parcours local complet. Elle ne couvre pas encore un certificat Let's Encrypt sur de vrais domaines, le réseau de votre VPS, un envoi Restic extérieur ou une restauration complète sur un autre VPS. Les SHA256 amd64 et arm64 correspondent aux releases Forgejo officielles ; les tests d'exécution ont utilisé arm64.
