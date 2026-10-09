# Vérifications effectuées

Date : 9 octobre 2026.

Les tableaux et la section « Configuration simplifiée » ci-dessous décrivent la version historique avec Basic Auth, avant son retrait. La validation de la version actuelle figure dans la section « Accès libre et désinstallation ».

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

## Configuration simplifiée

Le parcours avec adresse SSH, utilisateur root et un seul email a été testé à nouveau sur Debian 13 arm64 avec systemd, dans un environnement isolé. L'adresse d'accès est déduite de la cible ; seuls l'email et un mot de passe applicatif ont été fournis, en plus des informations de connexion du test.

- Déploiement avec valeurs automatiques, ports HTTPS 443/8443 et un seul mot de passe applicatif : réussi.
- Relance : 47 tâches réussies, zéro changement, zéro erreur.
- `verify.yml` : trois contrôles réussis, sans exécuter les tâches d'installation.
- Consultation HTTPS avec certificat explicitement approuvé : 401 sans compte, 200 avec le compte `docs`.
- Accès Git HTTPS avec le même mot de passe et certificat approuvé : branche `main` accessible.
- Déploiement en accès IPv4 direct : réussi ; identité TLS de l’adresse IP vérifiée avec le certificat approuvé, consultation et clone Git réussis.
- `tests/config.yml` : valeurs automatiques, templates pour adresse IPv4 et domaines facultatifs vérifiés sans serveur.

Le test de déploiement utilise une connexion Docker locale pour isoler Debian ; la configuration SSH par mot de passe est inchangée. Aucun VPS utilisateur n'a été contacté.

## Accès libre et désinstallation

La version actuelle a été testée sur Debian 13 arm64 avec systemd dans un environnement local jetable, sans contact avec le VPS utilisateur.

| Vérification | Résultat |
| --- | --- |
| Déploiement sans Basic Auth | Documentation HTTP 200 sans en-tête Authorization ni challenge WWW-Authenticate |
| Migration d'une configuration Basic Auth existante | HTTP 401 avant migration, HTTP 200 après ; ancien fichier de mots de passe supprimé |
| Sauvegarde sans fichier htpasswd | Première archive créée et vérifiée |
| Relance du déploiement | 61 tâches réussies, zéro changement, zéro erreur |
| verify.yml sans mot de passe documentaire | Trois contrôles réussis |
| Désinstallation puis réinstallation | Réussite |
| Purge des paquets suivis sur une installation dédiée | Réussite ; paquets nginx, restic et git-lfs retirés |
| Certificats knowledge-* et comptes de service | Suppression vérifiée |
| Usage partagé de Certbot | Certificat extérieur et dépendances Certbot conservés ; apt-get check réussi |
| Données extérieures et SSH | Conservation vérifiée |
| Seconde désinstallation avec la version finale | 19 tâches réussies, zéro changement, zéro erreur |
| Tests de configuration et syntaxe des quatre playbooks | Réussite |

Les sauvegardes Restic extérieures, le reverse proxy Proxmox et le réseau du VPS ne sont pas modifiés par la désinstallation. La restauration d'un site Nginx préexistant dépend du suivi enregistré avant installation ; le parcours historique sans suivi conserve les paquets préexistants.
