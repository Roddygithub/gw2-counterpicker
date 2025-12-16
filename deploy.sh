#!/bin/bash
# Script de déploiement automatique GW2 CounterPicker
# Synchronise GitHub et le serveur de votre ami

set -e

echo "=== Déploiement automatique GW2 CounterPicker ==="

# Configuration
SERVER_IP="82.64.171.203"
SERVER_PORT="2222"
SERVER_USER="syff"
SERVER_PATH="/home/syff/gw2-counterpicker"

# 1. Vérifier s'il y a des changements à committer
echo "Vérification des changements locaux..."
if [[ -n $(git status --porcelain) ]]; then
    echo "Changements détectés, commit en cours..."
    
    # Ajouter tous les fichiers modifiés
    git add .
    
    # Demander le message de commit
    echo "Entrez le message de commit (ou laissez vide pour le défaut):"
    read -r commit_message
    
    if [[ -z "$commit_message" ]]; then
        commit_message="Auto-deploy $(date '+%Y-%m-%d %H:%M:%S')"
    fi
    
    # Commit
    git commit -m "$commit_message"
    
    # Push vers GitHub
    echo "Envoi vers GitHub..."
    git push origin main
    
    echo "✅ Changements poussés sur GitHub"
else
    echo "Aucun changement local à pousser"
fi

# 2. Déployer sur le serveur distant
echo "Déploiement sur le serveur distant..."

# Créer un script de déploiement distant
cat > remote_deploy.sh << 'EOF'
#!/bin/bash
cd /home/syff/gw2-counterpicker

# Pull des derniers changements
echo "Pull depuis GitHub..."
git pull origin main

# Mettre à jour les dépendances si nécessaire
if [[ -f "requirements.txt" ]]; then
    source venv/bin/activate
    pip install -r requirements.txt -q
fi

# Démarrer Ollama si pas déjà en cours
echo "Vérification d'Ollama..."
if ! pgrep -x "ollama" > /dev/null; then
    echo "Démarrage d'Ollama..."
    nohup ollama serve > /dev/null 2>&1 &
    sleep 3
fi

# Vérifier que le modèle llama3.2 est disponible
if ! ollama list | grep -q "llama3.2"; then
    echo "Téléchargement du modèle llama3.2..."
    ollama pull llama3.2
fi

echo "✅ Ollama prêt"

# Redémarrer l'application
echo "Redémarrage de l'application..."
lsof -i :8001 -t | xargs -r kill -9 2>/dev/null || true
sleep 2
source venv/bin/activate
nohup python main.py > app.log 2>&1 &
sleep 4

# Vérifier que l'application est démarrée
if curl -s http://localhost:8001/health | grep -q "operational"; then
    echo "✅ Application démarrée avec succès"
else
    echo "⚠️ L'application n'a pas démarré correctement, vérifiez app.log"
fi

echo "✅ Déploiement terminé sur le serveur"
EOF

# Envoyer et exécuter le script distant
scp -P $SERVER_PORT remote_deploy.sh $SERVER_USER@$SERVER_IP:/tmp/
ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP "chmod +x /tmp/remote_deploy.sh && /tmp/remote_deploy.sh"

# Nettoyer
rm remote_deploy.sh

echo ""
echo "=== Déploiement terminé ! ==="
echo "✅ GitHub mis à jour"
echo "✅ Serveur distant mis à jour"
echo ""
echo "Le site sera disponible à: http://$SERVER_IP:8001"
echo "Ou via tunnel SSH: http://localhost:8001"
