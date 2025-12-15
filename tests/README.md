# Tests GW2 CounterPicker

Suite de tests automatisés pour GW2 CounterPicker.

## Installation des dépendances

```bash
pip install pytest pytest-asyncio httpx
```

## Lancer les tests

### Tous les tests
```bash
pytest
```

### Tests spécifiques
```bash
# Tests de validation de fichiers
pytest tests/test_file_validator.py

# Tests du rate limiter
pytest tests/test_rate_limiter.py

# Tests des endpoints API
pytest tests/test_api_endpoints.py

# Tests du service d'analyse
pytest tests/test_analysis_service.py

# Tests de détection de rôle
pytest tests/test_role_detector.py
```

### Avec verbosité
```bash
pytest -v
```

### Avec couverture de code
```bash
pytest --cov=. --cov-report=html
```

## Structure des tests

```
tests/
├── __init__.py
├── conftest.py                    # Fixtures et configuration
├── test_file_validator.py         # Tests de validation des fichiers
├── test_rate_limiter.py           # Tests du rate limiting
├── test_role_detector.py          # Tests de détection de rôle
├── test_analysis_service.py       # Tests du service d'analyse
└── test_api_endpoints.py          # Tests des endpoints API
```

## Couverture des tests

- ✅ Validation des fichiers (sécurité)
- ✅ Rate limiting
- ✅ Détection de rôle
- ✅ Service d'analyse
- ✅ Endpoints API
- ✅ Gestion des erreurs

## CI/CD

Les tests peuvent être intégrés dans un pipeline CI/CD :

```yaml
# Exemple GitHub Actions
- name: Run tests
  run: |
    pip install pytest pytest-asyncio httpx
    pytest -v
```
