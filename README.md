# 🌐 Net-Map • Scanner Réseau & Cartographie Topologique

**Net-Map** est une application moderne et ultra-rapide qui découvre l'intégralité des appareils connectés à votre réseau local (LAN / Wi-Fi), extrait leurs informations clés (**Adresses IP, Adresses MAC, Noms d'hôtes, Constructeurs, Ports ouverts**) et génère une **carte topologique interactive** en temps réel.

---

## ✨ Fonctionnalités Complètes (v1.2)

### 1. 🔍 Découverte & Empreinte Avancée (Fingerprinting)
- ⚡ **Scan Réseau Ultra-Rapide** : Balayage multithreadé sans processus externe par sockets légers et table ARP physique de l'hôte (1 à 3 secondes pour 254 adresses).
- 🏷️ **Identification Fabricants (OUI)** : Base de données locale intégrée + cache persistant avec enrichissement en ligne + détection d'adresses MAC aléatoires (iOS / Android).
- 💻 **Noms d'Hôtes & NetBIOS** : Requêtes NetBIOS (UDP 137) pour Windows / Samba / NAS et DNS inverse standard.
- 🌐 **Bannering Web & Titres HTTP** : Extraction automatique du `<title>` des pages d'accueil et des en-têtes `Server:` pour identifier instantanément les interfaces web (*"Freebox OS"*, *"Synology DSM"*, *"Pi-hole"*, etc.).
- 📶 **Détection SSDP / UPnP** : Interroge les annonces SSDP pour les équipements multimédias et domotiques.
- 🖥️ **Détection d'OS par TTL** : Analyse du Time-to-Live réseau pour déduire l'OS (*Linux/Android/macOS* vs *Windows* vs *Routeurs*).

### 2. ⚡ Boîte à Outils de Diagnostic Direct
- ⚡ **Wake-on-LAN (WOL)** : Bouton dédié pour envoyer un « Magic Packet » UDP de réveil à distance vers l'adresse MAC ciblée.
- 📶 **Mesure de Latence en Temps Réel (Live Ping)** : Teste la connectivité et la latence en direct pour n'importe quel équipement sélectionné.
- 🔍 **Scan de Ports Étendu à la Demande** : Audit approfondi des ports 1 à 1024 pour un équipement spécifique d'un seul clic.

### 3. 🗺️ Cartographie Topologique Interactive Avancée (Vis.js)
- 🔀 **Choix des Dispositions (Layouts)** :
  - **Physique Dynamique** (simulation de ressorts et gravité).
  - **Arborescence Hiérarchique** (arbre structuré partant d'Internet et du Routeur vers les périphériques).
  - **Étoile / Radiale** (roue centrée sur la passerelle).
- ✏️ **Personnalisation & Persistance** :
  - Renommez n'importe quel appareil avec un alias (*"PC Gaming Maxime"*, *"Imprimante Étage"*).
  - Ajoutez des notes internes sauvegardées dans `backend/data/devices_store.json`.
- 🔎 **Inspection Latérale** : Tiroir glissant avec détails complets et raccourcis HTTP / HTTPS directs.

### 4. 🛡️ Mode Surveillance Continue & Détection d'Intrus (Rogue Devices)
- 🕒 **Scan Périodique en Tâche de Fond** : Surveille en continu l'arrivée de nouveaux équipements sur le réseau local.
- 🚨 **Alerte d'Intrus en Temps Réel** : Notification visuelle immédiate, carillon sonore et badge d'alerte lors de la détection d'une nouvelle adresse MAC inconnue.
- 📋 **Journal des Alertes** : Historique consultable et effaçable des équipements ayant rejoint le réseau.

---

## 🚀 Démarrage Rapide

### Prérequis
- **Linux / WSL** (Ubuntu, Debian, etc.) ou **Windows 10 / 11**
- Python 3.10 ou supérieur

---

### Option 1 : Lancement sous Linux / WSL (Ubuntu)
Ouvrez votre terminal Linux ou WSL et lancez :
```bash
./run.sh
```
Ou manuellement :
```bash
# 1. Aller dans le dossier du projet
cd /mnt/c/Users/Maxime/Documents/dev/Net-Map

# 2. Lancer avec le venv Linux
./.venv-linux/bin/python main.py
```
> [!TIP]
> **Compatibilité WSL2** : L'application détecte automatiquement l'environnement WSL et interroge le sous-réseau physique de l'hôte (Wi-Fi/Ethernet) pour découvrir tous les vrais appareils du réseau local ainsi que leurs adresses MAC réelles.

---

### Option 2 : Lancement sous Windows (Natif)
Double-cliquez sur :
```cmd
run.bat
```
Ou dans PowerShell / CMD :
```powershell
.\.venv\Scripts\python main.py
```

Dans les deux cas, le serveur démarre et l'interface s'ouvre sur [**http://localhost:8000**](http://localhost:8000).

---

## 📁 Structure du Projet

```
Net-Map/
├── backend/
│   ├── app.py                      # Application FastAPI (REST & WebSockets)
│   ├── data/
│   │   └── oui_cache.json          # Cache persistant des résolutions MAC constructeurs
│   └── scanner/
│       ├── __init__.py             # Moteur principal de scan et d'orchestration
│       ├── network_detector.py      # Détection réseau, interfaces et passerelle
│       ├── arp_scanner.py          # Scan ARP multithreadé natif Windows (SendARP)
│       ├── oui_lookup.py           # Résolution et base de données constructeurs (OUI)
│       ├── host_resolver.py        # Résolution noms d'hôtes (DNS inverse & NetBIOS)
│       ├── port_scanner.py         # Détection des ports TCP courants
│       ├── device_classifier.py    # Algorithme de classification des appareils
│       └── topology_builder.py     # Construction des nœuds et arêtes du graphe Vis.js
├── frontend/
│   ├── index.html                  # Interface utilisateur moderne (Tailwind CSS, Vis.js)
│   ├── style.css                   # Styles personnalisés et animations
│   └── app.js                      # Contrôleur JS, gestion WebSocket et graphe interactif
├── main.py                         # Point d'entrée principal avec ouverture automatique du navigateur
├── run.bat                         # Lanceur rapide Windows
├── requirements.txt                # Dépendances Python
└── README.md                       # Documentation
```

---

## 🔒 Confidentialité & Sécurité
- Ce scanner effectue des requêtes ARP et des connexions légères uniquement au sein de votre réseau local privé.
- Aucun pilote agressif de capture de paquets (Npcap / WinPcap) n'est requis grâce à l'utilisation directe des API standard Windows.
