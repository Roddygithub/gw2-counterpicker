# 🎨 GW2 CounterPicker - Package UI/UX de Référence

Bienvenue ! Ce dossier contient une version **frontend-only** du projet GW2 CounterPicker, préparée spécialement pour faciliter le redesign de l'interface utilisateur.

## 📋 Contenu du Package

Ce package contient **6 pages HTML standalone** qui représentent toutes les interfaces clés de l'application :

### Pages Principales

1. **`index.html`** - Page d'accueil
   - Hero section avec titre principal et CTA
   - Section des fonctionnalités (features cards)
   - Section "Comment ça marche" (3 étapes)
   - Stats du moteur d'analyse
   - CTA final

2. **`analyze.html`** - Page d'analyse de combats
   - Sélecteur de mode (fichier .evtc vs lien dps.report)
   - Sélecteur de contexte de combat (Auto/Zerg/Guilde/Roam)
   - Zone de drag & drop pour fichiers
   - Formulaire pour lien dps.report
   - Section de résultats (placeholder)
   - Tips et astuces

3. **`meta.html`** - Meta WvW 2025
   - Sélecteur de contexte (Zerg/Guilde/Roam)
   - Tier lists (S, A, B, C) avec builds
   - Cartes de builds avec usage %
   - Section "En Hausse" et "En Baisse"
   - Indicateurs de rôle colorés

4. **`history.html`** - Historique personnel du joueur
   - Cartes de statistiques globales (combats, victoires, K/D)
   - Stats de combat détaillées
   - Builds et rôles favoris
   - Comparaison de performance (percentiles par rôle)
   - Tableau des stats par spécialisation

5. **`guild_analytics.html`** - Analytics de guilde
   - Header avec tag et nom de guilde
   - Stats globales (combats, winrate, membres)
   - Distribution des rôles (barres de progression)
   - Top spécialisations
   - Top participants (tableau)
   - Meilleures compositions de groupe (5 joueurs)

6. **`dashboard.html`** - Dashboard personnel
   - Carte de compte connecté (nom, rang WvW, monde)
   - Liste des guildes avec liens vers analytics
   - Section d'import de stats
   - Actions rapides (liens vers autres pages)

## 🚀 Comment Utiliser

### Ouvrir les Pages

**C'est très simple !** Chaque fichier HTML est **standalone** et peut être ouvert directement dans un navigateur :

1. Double-cliquez sur n'importe quel fichier `.html`
2. OU faites clic-droit → "Ouvrir avec" → votre navigateur préféré (Chrome, Firefox, Edge, Safari)
3. Les pages s'affichent avec tous les styles et animations

**Aucun serveur web n'est nécessaire** - tout fonctionne en local !

### Navigation

- Utilisez le menu de navigation en haut de chaque page pour passer d'une page à l'autre
- Les liens sont fonctionnels entre les pages du package

## 🎨 Technologies Utilisées

### CSS Framework
- **Tailwind CSS** (via CDN) - Framework CSS utility-first
- Configuration custom avec couleurs du thème GW2 CounterPicker
- Classes personnalisées pour les effets de glow, animations, etc.

### JavaScript
- **Alpine.js** (via CDN) - Pour les interactions légères (tabs, dropdowns, etc.)
- Pas de logique backend - juste des interactions UI

### Fonts
- **Orbitron** - Police display pour les titres (style gaming/tech)
- **Inter** - Police body pour le texte (lisibilité)

### Couleurs du Thème

```css
'gw2-purple': '#8B5CF6'    /* Violet principal */
'gw2-dark': '#0F0A1F'      /* Fond sombre */
'gw2-darker': '#080510'    /* Fond très sombre */
'cyber-pink': '#EC4899'    /* Rose cyberpunk */
'cyber-cyan': '#22D3EE'    /* Cyan cyberpunk */
```

## 🎯 Ce Qui Est Attendu de Toi

### Focus sur le Design

Tu peux modifier **librement** :

✅ **Structure HTML** - Réorganiser les sections, ajouter/supprimer des éléments
✅ **Classes Tailwind** - Changer les couleurs, espacements, tailles, layouts
✅ **Typographie** - Polices, tailles de texte, hiérarchie
✅ **Composants** - Cards, boutons, formulaires, tableaux
✅ **Layout** - Grilles, flexbox, responsive design
✅ **Animations** - Transitions, hover effects, etc.
✅ **Couleurs** - Palette de couleurs, contrastes, thème

### Ce Que Tu Peux Ignorer

❌ **Logique backend** - Les formulaires, les actions, les API calls
❌ **Data bindings** - Les variables Jinja2 ont été remplacées par du contenu statique
❌ **JavaScript complexe** - Pas besoin de coder de la logique métier
❌ **Intégration backend** - On s'occupera de ré-intégrer ton travail dans les vrais templates

### Données Factices

Toutes les données affichées sont **des exemples** :
- Noms de joueurs : "Player.1234", "Commander.5678"
- Stats : nombres fictifs mais réalistes
- Builds : vrais noms de spécialisations GW2
- Guildes : "[TAG] Nom de Guilde"

**C'est normal !** L'objectif est de voir le design, pas les vraies données.

## 📐 Principes de Design Actuels

### Style Général
- **Thème sombre** (dark mode) avec effets néon/cyberpunk
- **Gradients** sur les titres et boutons importants
- **Glassmorphism** (backdrop-blur) sur les cartes
- **Animations subtiles** (hover, transitions)

### Composants Clés

1. **Glow Cards** - Cartes avec bordure lumineuse au hover
2. **Gradient Buttons** - Boutons avec dégradés de couleur
3. **Role Badges** - Badges colorés par rôle (DPS, Heal, Stab, etc.)
4. **Progress Bars** - Barres de progression pour les stats
5. **Tier Cards** - Cartes de builds avec tier (S, A, B, C)

### Responsive Design
- Mobile-first avec Tailwind
- Breakpoints : `sm:`, `md:`, `lg:`
- Grids qui s'adaptent (1 col mobile → 2-3 cols desktop)

## 🔧 Conseils Techniques

### Modifier les Couleurs

Dans chaque fichier HTML, tu trouveras la config Tailwind dans le `<head>` :

```javascript
tailwind.config = {
    theme: {
        extend: {
            colors: {
                'gw2-purple': '#8B5CF6',  // ← Change ici
                // ...
            }
        }
    }
}
```

### Ajouter des Composants

Tu peux utiliser **toutes les classes Tailwind** :
- Documentation : https://tailwindcss.com/docs

Exemples :
```html
<!-- Bouton gradient -->
<button class="px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg">
    Click me
</button>

<!-- Card avec glassmorphism -->
<div class="bg-white/10 backdrop-blur-lg border border-white/20 rounded-xl p-6">
    Contenu
</div>
```

### Alpine.js pour Interactions

Quelques exemples d'Alpine.js déjà utilisés :

```html
<!-- Tabs -->
<div x-data="{ tab: 'files' }">
    <button @click="tab = 'files'">Fichiers</button>
    <button @click="tab = 'url'">URL</button>
    
    <div x-show="tab === 'files'">Contenu fichiers</div>
    <div x-show="tab === 'url'">Contenu URL</div>
</div>
```

## 📝 Workflow Recommandé

1. **Ouvre toutes les pages** dans ton navigateur pour avoir une vue d'ensemble
2. **Identifie les patterns** qui se répètent (navigation, footer, cards, etc.)
3. **Commence par une page** (ex: index.html) pour définir le style général
4. **Applique le style** aux autres pages en gardant la cohérence
5. **Teste le responsive** en redimensionnant la fenêtre du navigateur
6. **Partage ton travail** - envoie-moi les fichiers HTML modifiés

## 🎨 Inspiration & Références

Le design actuel s'inspire de :
- **Cyberpunk/Gaming aesthetics** - Néons, gradients, effets glow
- **Dark mode moderne** - Contrastes élevés, lisibilité
- **Guild Wars 2** - Couleurs violettes/dorées, thème fantasy-tech

N'hésite pas à proposer une **nouvelle direction artistique** si tu as des idées !

## 💡 Questions Fréquentes

**Q: Puis-je changer complètement le design ?**
A: Oui ! Tu as carte blanche. Si tu veux partir sur un thème clair, minimaliste, ou autre, vas-y.

**Q: Dois-je garder toutes les sections ?**
A: Tu peux réorganiser, mais essaie de garder les informations principales (stats, builds, etc.).

**Q: Comment tester mes modifications ?**
A: Sauvegarde le fichier HTML et rafraîchis la page dans ton navigateur (F5 ou Cmd+R).

**Q: Les liens fonctionnent-ils ?**
A: Oui, entre les pages du package. Les liens externes (dps.report, etc.) fonctionnent aussi.

**Q: Puis-je ajouter des images/icônes ?**
A: Oui ! Tu peux utiliser des émojis (déjà présents) ou ajouter des icônes SVG inline.

## 📞 Contact

Si tu as des questions ou besoin de clarifications, n'hésite pas à me contacter !

**Bon redesign ! 🚀**

---

*Package créé le 19 Décembre 2024 pour GW2 CounterPicker v4.0*
