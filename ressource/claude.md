# CLAUDE.md — conseil de classe


## Git

- Dépôt : https://github.com/Galgo-dev/EXO-E02.git — branche principale `main`.
- Si main 'inexistant', création first commit + rajout de la structure existante add origin 
- **Chaque nouvelle fonctionnalité se développe sur une nouvelle branche** (`feature/<nom-court>`,
  `docs/<nom>` pour la documentation), jamais directement sur `main`. Intégration par pull request.
- Messages de commit en français.
- Ne push jamais sans ma permission
- Ne supprime aucun commit

### Conventions

- **Composants** : fichiers `.jsx` en `PascalCase`, un composant par fichier ; hooks en `camelCase` préfixés par `use`.
- **Services API** : fichiers `<ressource>.api.js`, une fonction par endpoint ; ils utilisent uniquement `axiosClient`.
- **Pages** : assemblent layouts et composants ; les appels de données passent par les hooks.
- **Contrôle d'accès** : les routes protégées passent par `ProtectedRoute` / `RoleRoute` ; l'API reste la source de vérité pour les droits.
- **Variables d'environnement** : préfixe `VITE_` obligatoire, lues uniquement dans `api/axiosClient.js`.
- **Responsive** : conception mobile d'abord, valeurs communes centralisées dans `styles/variables.css`.


## Règles du projet
- Utilise le clean code
- Simplifie au maximum les fonctionalité
- Ne lis jamais le .env, nis le modifié
- Maximum 10 tests par fonction
- Architecture simplifié