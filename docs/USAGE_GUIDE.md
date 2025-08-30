# Guide d'utilisation SAMURAI

## 1. Installation

Suivez les instructions du `README.md` pour installer les dépendances.

## 2. Lancement du serveur

- **Windows :** Utilisez `start_backend.bat`.
- **Linux/Mac :** Utilisez le script PowerShell dans `scripts/start_flask_server.ps1`.

## 3. Entraînement d'un modèle

Utilisez le script suivant :

```bash
python mlops/scripts/train.py --epochs <N> --batch <N> --data <chemin_yaml> --model <chemin_pt> --device <cpu|cuda>
```

## 4. Comparaison et déploiement

Après l'entraînement, récupérez l'ID du run MLflow et lancez :

```bash
python mlops/scripts/compare_models.py --run_id <MLflow_Run_ID>
```

Le résultat est dans `comparison_result.txt`.

## 5. Gestion des données

Pour synchroniser les données :

```bash
dvc pull -r myremote
```

## 6. Dépannage

- Vérifiez les logs générés (`training_output.log`, etc.).
- Consultez le fichier `Jenkinsfile` pour le pipeline CI/CD.
