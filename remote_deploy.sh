#!/bin/bash
cd /home/syff/gw2-counterpicker

# Pull des derniers changements
echo "Pull depuis GitHub..."
git pull origin main

# Mettre à jour les dépendances si nécessaire
if [[ -f "requirements.txt" ]]; then
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Redémarrer le service (si systemd est configuré)
if systemctl is-active --quiet gw2-counterpicker 2>/dev/null; then
    echo "Redémarrage du service systemd..."
    sudo systemctl restart gw2-counterpicker
else
    # Sinon, tuer les processus existants et redémarrer manuellement
    echo "Redémarrage manuel de l'application..."
    pkill -f "python.*main.py" || true
    sleep 2
    source venv/bin/activate
    nohup python -c "import uvicorn; uvicorn.run('main:app', host='0.0.0.0', port=8001)" > app.log 2>&1 &
fi

echo "✅ Déploiement terminé sur le serveur"
