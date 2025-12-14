#!/bin/bash
# Script de déploiement GW2 CounterPicker pour serveur faible en RAM

set -e

echo "=== Déploiement GW2 CounterPicker (Mode Léger) ==="

# Mettre à jour le système
echo "Mise à jour du système..."
sudo apt update && sudo apt upgrade -y

# Installer Python 3.11+ et dépendances
echo "Installation de Python et dépendances..."
sudo apt install -y python3 python3-pip python3-venv nginx git curl

# Créer le répertoire de l'application
APP_DIR="/opt/gw2-counterpicker"
sudo mkdir -p $APP_DIR
sudo chown syff:syff $APP_DIR
cd $APP_DIR

# Cloner le projet
echo "Clonage du projet..."
git clone https://github.com/Roddygithub/gw2-counterpicker.git .

# Créer environnement virtuel
echo "Création de l'environnement virtuel..."
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances Python
echo "Installation des dépendances Python..."
pip install --upgrade pip
pip install -r requirements.txt

# Créer les répertoires nécessaires
mkdir -p data uploads reports

# Désactiver Ollama (pas assez de RAM)
echo "Configuration du mode sans Ollama..."
export OLLAMA_DISABLED=1

# Créer le service systemd
echo "Configuration du service systemd..."
sudo tee /etc/systemd/system/gw2-counterpicker.service > /dev/null <<EOF
[Unit]
Description=GW2 CounterPicker Web Service
After=network.target

[Service]
Type=simple
User=syff
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
Environment=OLLAMA_DISABLED=1
ExecStart=$APP_DIR/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Activer et démarrer le service
sudo systemctl daemon-reload
sudo systemctl enable gw2-counterpicker
sudo systemctl start gw2-counterpicker

echo "=== Configuration Nginx ==="
# Configurer Nginx comme reverse proxy
sudo tee /etc/nginx/sites-available/gw2-counterpicker > /dev/null <<EOF
server {
    listen 80;
    server_name 82.64.171.203;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Pour les uploads de fichiers
    client_max_body_size 50M;
}
EOF

# Activer le site Nginx
sudo ln -sf /etc/nginx/sites-available/gw2-counterpicker /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo "=== Déploiement terminé ! ==="
echo "Site accessible à: http://82.64.171.203"
echo ""
echo "Pour vérifier le statut:"
echo "  sudo systemctl status gw2-counterpicker"
echo "  sudo journalctl -u gw2-counterpicker -f"
