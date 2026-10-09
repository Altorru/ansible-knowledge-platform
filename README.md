# Plateforme documentaire autonome

Forgejo + MkDocs Material + Nginx, installés sur un VPS Debian par Ansible. Les sources sont clonables, la documentation est publiée en HTML et les mises à jour sont autonomes. Aucun runner CI, abonnement, Docker ou clé SSH nécessaire sur le VPS.

## Démarrage

Prérequis : Debian 12 ou 13, architecture amd64 ou arm64, accès SSH par mot de passe et droits sudo, deux domaines pointant sur le VPS. Les ports TCP 80 et 443 doivent être accessibles pour Let's Encrypt. Prévoir un serveur dédié à cette plateforme pour éviter les conflits avec d'autres services web.

Sur le Mac, Ansible Core 2.19+ est nécessaire ; la version 2.21.5 installée convient. Ouvrir un terminal dans ce dépôt, copier l'inventory et renseigner les fichiers :

```sh
cp inventory/hosts.example.yml inventory/hosts.yml
```

- `inventory/hosts.yml` : adresse, utilisateur et port SSH.
- `inventory/group_vars/knowledge/main.yml` : domaines Git et documentation, emails et nom du dépôt.

Les valeurs `.invalid` sont volontairement refusées avant installation. Vérifier l'empreinte SSH de la cible auprès de l'hébergeur puis effectuer une première connexion avec mot de passe pour l'enregistrer :

```sh
ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password,keyboard-interactive -p 22 deploy@ADRESSE_DU_VPS
```

Ensuite, une seule commande déploie toute la plateforme :

```sh
ansible-playbook -i inventory/hosts.yml deploy.yml -k -K
```

Ansible demande le mot de passe SSH, le mot de passe sudo, le mot de passe initial Forgejo et le mot de passe partagé du site documentaire. Les mots de passe applicatifs doivent comporter au moins 16 caractères. Omettre `-K` pour root ou sudo sans mot de passe. Les connexions Ansible n'utilisent aucune clé SSH.

Le déploiement met aussi à jour les paquets Debian sans suppression de paquets, migration majeure ou redémarrage automatique. Mettre `platform_upgrade_packages: false` dans l’inventory pour réserver les mises à jour au playbook de maintenance.

## Résultat

- `https://git.VOTRE-DOMAINE/` : Forgejo, connecté avec `forgejo_admin_user` (par défaut `docsadmin`).
- `https://docs.VOTRE-DOMAINE/` : documentation, utilisateur `docs` et mot de passe partagé.
- Dépôt initial privé : `https://git.VOTRE-DOMAINE/docsadmin/base-connaissance.git`.
- Services natifs : Forgejo, Nginx, publication toutes les 60 secondes, première sauvegarde vérifiée puis sauvegarde quotidienne.

Les domaines réels proviennent de l'inventory. Les inscriptions publiques sont désactivées. Pour démarrer simplement, l'équipe peut utiliser le compte du dépôt ; des comptes individuels et collaborateurs peuvent ensuite être ajoutés dans Forgejo sans changer le déploiement.

Git passe par HTTPS : le mot de passe du compte fonctionne tant que son authentification ne nécessite pas de jeton (par exemple après activation de 2FA). Cela ne nécessite aucune clé SSH.

## Modifier les documents

```sh
git clone https://git.VOTRE-DOMAINE/docsadmin/base-connaissance.git
cd base-connaissance
```

Modifier les fichiers dans `docs/`, puis :

```sh
git add docs/
git commit -m "Documenter la procédure de livraison"
git push origin main
```

Le site s'actualise normalement dans la minute suivant le push, plus la durée du build. Il faut récupérer les changements des collègues avant de pousser (`git pull --rebase`) et résoudre les conflits éventuels. Tous les collaborateurs du dépôt peuvent modifier la documentation.

Prévisualisation locale facultative :

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/mkdocs serve
```

Les fichiers Markdown sont la source de vérité. Le navigateur permet la consultation et Forgejo permet aussi l'édition des fichiers. Le premier déploiement initialise seulement un dépôt vide ; les suivants ne remplacent jamais les documents existants.

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
ansible-vault create inventory/group_vars/knowledge/vault.yml
```

Contenu à saisir dans l'éditeur :

```yaml
vault_forgejo_admin_password: 'votre-mot-de-passe-forgejo'
vault_docs_password: 'votre-mot-de-passe-documentation'
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

## TLS

`tls_mode: letsencrypt` est le mode par défaut : certificat public pour les deux domaines, renouvellement par `certbot.timer` et rechargement Nginx après renouvellement. Renseigner un email valide et vérifier les enregistrements DNS A/AAAA. L'accord aux conditions Let's Encrypt est fourni par le playbook lors de son exécution.

`tls_mode: selfsigned` est réservé aux tests ou réseaux internes avec une autorité de confiance administrée séparément. Le certificat généré n'est pas reconnu par les navigateurs et n'est pas renouvelé automatiquement. Aucun contenu documentaire n'est accessible en HTTP sans TLS.

Le playbook n'altère pas les règles du pare-feu ni la configuration SSH. Ouvrir 80/443 auprès de l'hébergeur si nécessaire. Forgejo écoute uniquement sur `127.0.0.1:3000`. Aucun port Git SSH supplémentaire n'est ouvert.

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

1. Installer la même version de cette plateforme avec Ansible et des domaines de test.
2. Arrêter les timers, `knowledge-publish.service` et Forgejo.
3. Vérifier l'archive (`tar -tzf`) puis extraire dans un répertoire temporaire protégé.
4. Remplacer `/var/lib/forgejo`, `/etc/forgejo` et `/srv/knowledge` avec les fichiers sauvegardés. Si les identifiants numériques des comptes ont changé, réattribuer `/var/lib/forgejo` à `forgejo:forgejo` et `/srv/knowledge` à `knowledge:knowledge`, puis réappliquer les permissions de configuration avec Ansible.
5. Restaurer les paramètres métier et secrets nécessaires ; adapter les domaines et obtenir de nouveaux certificats avec Ansible. Les certificats Let's Encrypt ne sont pas inclus dans l'archive.
6. Redémarrer Forgejo, relancer Ansible, vérifier le clone, les documents, l'authentification et les timers.

Ne pas extraire aveuglément une archive sur un serveur existant. Restic permet d'abord de récupérer l'archive sur une machine isolée. Le protocole de restauration complet doit être validé dans votre environnement.

## Maintenance et contrôles

```sh
ansible-playbook verify.yml -k -K --ask-vault-pass
ansible-playbook maintenance.yml -k -K
```

`verify.yml` utilise `vault_docs_password` ou demande le mot de passe de consultation, et vérifie les services et le site depuis le VPS. Pour vérifier aussi l'accès externe et la validité du certificat, ouvrir les deux domaines depuis un poste utilisateur.

`maintenance.yml` réalise une sauvegarde puis une mise à jour Debian sans suppression automatique de paquets ni migration majeure. Il signale le besoin de redémarrage. MkDocs et Forgejo restent fixés : une mise à jour applicative consiste à mettre à jour les versions/checksums ou le fichier de dépendances, à vérifier en test puis à relancer Ansible. La sauvegarde est déclenchée avant un changement du binaire Forgejo. Une migration de base peut empêcher un simple retour à l'ancien binaire : restaurer les données correspondantes.

Le mode `--check` ne remplace pas un déploiement de test et ne convient pas à une cible vierge sans Python ni fichiers de configuration. Les contrôles syntaxiques fonctionnent sans serveur :

```sh
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
