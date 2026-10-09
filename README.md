# Plateforme documentaire autonome

Forgejo + MkDocs Material + Nginx, installés sur un VPS Debian par Ansible. Les sources sont clonables, la documentation est publiée en HTML et les mises à jour sont autonomes. Aucun runner CI, abonnement, Docker ou clé SSH nécessaire sur le VPS.

## Quickstart

Un VPS **Debian 12 ou 13**, son adresse SSH et un email suffisent. Ansible crée les comptes, le dépôt documentaire, HTTPS, la publication automatique et les sauvegardes locales. Prévoir un VPS dédié et ouvrir les ports **443 et 8443** auprès de l'hébergeur.

### 1. Préparer l'inventory

Ansible Core 2.19+ doit être installé sur votre poste. Depuis le dépôt :

```sh
cd ~/Documents/ansible-knowledge-platform
cp -n inventory/hosts.example.yml inventory/hosts.yml
```

Modifier uniquement `inventory/hosts.yml` :

```yaml
all:
  children:
    knowledge:
      hosts:
        knowledge_01:
          ansible_host: 203.0.113.10       # Adresse réelle du VPS
          ansible_user: root             # Ou votre utilisateur sudo
          platform_email: vous@entreprise.fr
```

Le port SSH est 22 par défaut. Ajouter `ansible_port` seulement si l'hébergeur utilise un autre port. Le mot de passe SSH sera demandé au lancement ; l'inventory réel est ignoré par Git.

### 2. Se connecter une première fois

Remplacer l'adresse par celle du VPS et adapter l'utilisateur si nécessaire :

```sh
ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password,keyboard-interactive root@203.0.113.10
```

Vérifier l'empreinte du serveur auprès de l'hébergeur avant de l'accepter. Saisir le mot de passe SSH, puis `exit` pour revenir sur votre poste. Aucune clé d'authentification SSH n'est nécessaire.

### 3. Déployer

Avec `root` :

```sh
ansible-playbook deploy.yml -k
```

Avec un utilisateur sudo :

```sh
ansible-playbook deploy.yml -k -K
```

Deux secrets sont demandés : le **mot de passe SSH**, puis un **mot de passe plateforme d'au moins 16 caractères** à choisir pour Forgejo et la consultation des docs. Avec sudo, `-K` demande également son mot de passe ; l'omettre si sudo ne demande pas de mot de passe. Aucun Vault nécessaire.

### 4. Utiliser

Les adresses exactes sont affichées à la fin du déploiement :

| Service | Adresse automatique | Identifiant |
| --- | --- | --- |
| Documentation | `https://ADRESSE_DU_VPS/` | `docs` |
| Forgejo | `https://ADRESSE_DU_VPS:8443/` | `docsadmin` |
| Dépôt privé | `https://ADRESSE_DU_VPS:8443/docsadmin/base-connaissance.git` | `docsadmin` |

Les deux comptes utilisent le mot de passe plateforme choisi. HTTPS utilise par défaut un **certificat auto-signé valable dix ans** : le navigateur affiche un avertissement. Pour Git, importer ce certificat dans les autorités de confiance de votre poste ; éviter de désactiver globalement la vérification TLS. Le certificat public est disponible sur le VPS à l'emplacement affiché à la fin du déploiement. Aucun domaine ni service DNS extérieur n'est nécessaire.

Vérifier les services avec root :

```sh
ansible-playbook verify.yml -k
```

Avec sudo, ajouter `-K` si un mot de passe sudo est nécessaire. Relancer la commande de déploiement pour réappliquer la configuration en saisissant le mot de passe plateforme actuel : les documents existants sont conservés.

## Modifier les documents

Dans Forgejo, ouvrir `docsadmin/base-connaissance`, puis éditer les fichiers Markdown dans `docs/` directement dans le navigateur. Le site est reconstruit automatiquement dans la minute suivant le commit, plus la durée du build.

Pour travailler avec Git, après avoir fait confiance au certificat du serveur :

```sh
git clone https://ADRESSE_DU_VPS:8443/docsadmin/base-connaissance.git
cd base-connaissance
# Modifier les fichiers Markdown dans docs/
git add docs/
git commit -m "Documenter la procédure de livraison"
git pull --rebase
git push origin main
```

Git demande le compte Forgejo et son mot de passe. Les inscriptions publiques sont désactivées ; l'administrateur peut créer des comptes individuels et les ajouter comme collaborateurs du dépôt. Avec la 2FA, utiliser un jeton Forgejo pour Git HTTPS.

Prévisualisation locale facultative :

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/mkdocs serve
```

Les fichiers Markdown sont la source de vérité. Le premier déploiement initialise uniquement un dépôt vide ; les suivants ne remplacent jamais les documents existants.

## Publication fiable

Le timer systemd appelle un programme court sous le compte `knowledge`. Celui-ci lit un instantané du commit `main`, construit dans un dossier temporaire puis remplace atomiquement le lien `current` si le build réussit. Un verrou empêche les publications concurrentes et protège les sauvegardes. Les cinq dernières versions HTML sont conservées. Un commit inchangé n'est pas reconstruit.

En cas de lien interne cassé, de build invalide ou de document manquant, la dernière version fonctionnelle reste servie. La publication suivante retente le build. Les erreurs sont consultables avec :

```sh
sudo journalctl -u knowledge-publish.service -n 100 --no-pager
sudo systemctl list-timers 'knowledge-*'
```

La configuration `mkdocs.yml` et les dépendances du serveur sont administrées par Ansible depuis ce dépôt. Les copies contenues dans le dépôt documentaire servent à la prévisualisation ; modifier ces copies ne change pas la configuration du serveur. Cela empêche un push de documents d'installer ou d'exécuter des plugins ou hooks Python. Pour changer la navigation ou le thème, modifier `seed/mkdocs.yml` ici puis relancer Ansible. Les changements du moteur et de sa configuration déclenchent également un rebuild.

## Secrets avec Ansible Vault

Pour ne pas ressaisir les mots de passe applicatifs :

```sh
mkdir -p inventory/group_vars/knowledge
ansible-vault create inventory/group_vars/knowledge/vault.yml
```

Contenu à saisir dans l'éditeur :

```yaml
vault_forgejo_admin_password: 'votre-mot-de-passe-plateforme'
# Facultatif : séparer le mot de passe de consultation
# vault_docs_password: 'autre-mot-de-passe-documentation'
# Optionnel, pour éviter -k / -K :
ansible_password: 'votre-mot-de-passe-ssh'
ansible_become_password: 'votre-mot-de-passe-sudo'
```

Puis :

```sh
ansible-playbook deploy.yml -k -K --ask-vault-pass
```

Si SSH et sudo sont définis dans Vault, omettre `-k -K`. Le fichier Vault est ignoré par Git par défaut, tout comme l'inventory réel. Les secrets internes Forgejo sont générés une fois sur le serveur. Aucun mot de passe ne figure dans les fichiers livrés.

Le mot de passe Forgejo est créé une fois, puis n'est pas réinitialisé automatiquement. Si l'administrateur le change dans Forgejo, mettre à jour Vault ou saisir ce nouveau mot de passe lors des déploiements suivants. Le mot de passe partagé de documentation peut être modifié en relançant Ansible.

## Paramètres avancés (facultatifs)

Les paramètres techniques sont définis dans `roles/platform/defaults/main.yml` : comptes applicatifs, dépôt `base-connaissance`, branche `main`, ports, versions et sauvegardes. Aucun de ces paramètres n'est à renseigner pour démarrer. Ansible met à jour les paquets Debian sans migration majeure ni redémarrage automatique.

Pour utiliser des domaines et un certificat public plus tard, ajouter dans l'inventory `git_domain`, `docs_domain` (deux domaines distincts pointant vers le VPS) et `tls_mode: letsencrypt`. L'email déjà renseigné sert aussi pour Let's Encrypt. Les deux services utilisent alors le port 443 ; ouvrir également le port 80 pour les challenges et le renouvellement automatique. Les conditions Let's Encrypt sont acceptées lors du déploiement.

Le playbook n'altère ni le pare-feu ni la configuration SSH. Forgejo écoute en interne sur `127.0.0.1:3000`, derrière Nginx. La consultation reste protégée par mot de passe. Pour éviter les mises à jour système au déploiement, ajouter `platform_upgrade_packages: false` dans l'inventory.

## Sauvegardes

Chaque jour vers 03:30, heure de Paris (avec un décalage aléatoire jusqu'à 15 minutes), le serveur :

1. Prend le verrou de publication.
2. Arrête brièvement Forgejo pour une copie cohérente de SQLite et des dépôts.
3. Archive données, configuration, secrets et site publié dans `/var/backups/knowledge/`.
4. Redémarre Forgejo, y compris lorsqu'une erreur survient pendant l'archivage.
5. Conserve les archives locales pendant environ sept jours.

Les archives sont protégées et contiennent des secrets. Une sauvegarde locale ne protège pas contre la perte du VPS.

Pour une copie extérieure, renseigner `backup_restic_repository` (S3 ou serveur REST par exemple) et `vault_restic_password` dans Vault. Pour S3, ajouter `vault_aws_access_key_id` et `vault_aws_secret_access_key`. Initialiser volontairement le dépôt distant avec `restic init` avant de l'activer. Le script envoie ensuite l'archive avec Restic et applique une rétention quotidienne, hebdomadaire et mensuelle. Cette option ne nécessite pas de worker.

Sauvegarde manuelle :

```sh
sudo /usr/local/sbin/knowledge-backup
```

## Restaurer

Tester la restauration sur un VPS isolé avant un incident réel :

1. Installer la même version de cette plateforme avec Ansible sur un VPS de test.
2. Arrêter les timers, `knowledge-publish.service` et Forgejo.
3. Vérifier l'archive (`tar -tzf`) puis extraire dans un répertoire temporaire protégé.
4. Remplacer `/var/lib/forgejo`, `/etc/forgejo` et `/srv/knowledge` avec les fichiers sauvegardés. Si les identifiants numériques des comptes ont changé, réattribuer `/var/lib/forgejo` à `forgejo:forgejo` et `/srv/knowledge` à `knowledge:knowledge`, puis réappliquer les permissions de configuration avec Ansible.
5. Restaurer les paramètres métier et secrets nécessaires ; adapter la cible SSH et recréer les certificats avec Ansible. Les certificats Let's Encrypt ne sont pas inclus dans l'archive.
6. Redémarrer Forgejo, relancer Ansible, vérifier le clone, les documents, l'authentification et les timers.

Ne pas extraire aveuglément une archive sur un serveur existant. Restic permet d'abord de récupérer l'archive sur une machine isolée. Le protocole de restauration complet doit être validé dans votre environnement.

## Maintenance et contrôles

```sh
ansible-playbook verify.yml -k -K
ansible-playbook maintenance.yml -k -K
```

Si vous avez créé un fichier Vault, ajouter `--ask-vault-pass` à ces commandes. Avec root, omettre `-K` ; Ansible utilise automatiquement les droits du compte connecté.

`verify.yml` utilise `vault_docs_password` ou demande le mot de passe de consultation, et vérifie les services et le site depuis le VPS. Pour vérifier aussi l'accès externe et la validité du certificat, ouvrir les deux adresses affichées depuis un poste utilisateur.

`maintenance.yml` réalise une sauvegarde puis une mise à jour Debian sans suppression automatique de paquets ni migration majeure. Il signale le besoin de redémarrage. MkDocs et Forgejo restent fixés : une mise à jour applicative consiste à mettre à jour les versions/checksums ou le fichier de dépendances, à vérifier en test puis à relancer Ansible. La sauvegarde est déclenchée avant un changement du binaire Forgejo. Une migration de base peut empêcher un simple retour à l'ancien binaire : restaurer les données correspondantes.

Le mode `--check` ne remplace pas un déploiement de test et ne convient pas à une cible vierge sans Python ni fichiers de configuration. Les contrôles de configuration et de syntaxe fonctionnent sans serveur :

```sh
ansible-playbook -i localhost, tests/config.yml
ansible-playbook -i inventory/hosts.example.yml deploy.yml --syntax-check
ansible-playbook -i inventory/hosts.example.yml maintenance.yml --syntax-check
ansible-playbook -i inventory/hosts.example.yml verify.yml --syntax-check
```

Tests de publication avec de vrais builds MkDocs :

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
MKDOCS_BIN="$PWD/.venv/bin/mkdocs" .venv/bin/python -m unittest discover -s tests -v
```

Voir `VALIDATION.md` pour les vérifications réellement effectuées. Aucun déploiement sur votre VPS n'est annoncé tant que votre inventory n'a pas été exécuté.

## Sources et licences

Forgejo est un logiciel libre ; MkDocs 1.6.1 et Material 9.7.7 sont fixés pour éviter une migration majeure implicite. Les dépendances Python sont également fixées dans `requirements.txt`. Les binaires Forgejo 15.0.9 proviennent des releases officielles et leurs SHA256 sont enregistrés dans le rôle. Les paquets Debian utilisent les dépôts signés du système.

- https://forgejo.org/docs/latest/admin/installation/binary/
- https://forgejo.org/docs/latest/admin/config-cheat-sheet/
- https://www.mkdocs.org/user-guide/deploying-your-docs/
- https://squidfunk.github.io/mkdocs-material/
