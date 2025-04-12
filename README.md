# Projet Animatronique : Marcus

Ce dépôt contient le code et la structure d’architecture pour un système d’animatronique capable de détecter des visages, reconnaître des émotions, parler et bouger la tête via des servomoteurs. L’objectif est de permettre à *Marcus* de réagir en temps réel aux personnes qui l’entourent (détection du regard, conversation audio, expressions faciales, etc.).

---

<!-- HTML image Marcus (resized) -->
<img src="docs/Marcus.jpg" alt="Marcus illustration" width="300"/>

<!-- HTML image Setup (resized) -->
<img src="docs/Setup_Marcus.jpg" alt="Marcus illustration" width="300"/>


## Aperçu de l’Architecture

Le diagramme ci-dessous illustre le flux de communication entre les différents composants :

- **Raspberry Pi**  
  *Caméra + Reconnaissance faciale*  
  Envoi de la position `(x,y)` et des émotions détectées via MQTT

- **Microphone**  
  *Capture audio et envoi vers le PC*

- **PC central**  
  - Fait office de **Broker MQTT**  
  - Utilise **Whisper** (STT) pour la reconnaissance vocale  
  - Fait des requêtes au **LLM externe** (OpenAI) via une API REST (avec le contexte : texte + émotion)  
  - Renvoie une réponse texte  
  - Gère la **synthèse vocale (TTS)** pour parler via un haut-parleur

- **Arduino** (contrôle des servos)  
  - Reçoit les commandes MQTT (*PARLE, REGARDE, HOCHE_TETE, etc.*)  
  - Envoie son statut (*busy/ready*) via MQTT  
  - Contrôle effectif des mouvements du cou/de la tête

---

## Structure du Dépôt

```bash
marcus/
├── docs/
│   └── ... (Documentation, schémas, etc.)
├── lib/
│   └── ... (Bibliothèques ou modules partagés)
├── src/
│   ├── common/
│   │   └── communication.py       (Fonctions communes de communication MQTT/Python)
│   ├── llm/
│   │   └── com_llm.py            (Intégration des requêtes LLM, ex. OpenAI)
│   ├── servo/
│   │   ├── com_servos.cpp        (Implémentation MQTT côté Arduino)
│   │   ├── servos.cpp            (Logique de contrôle des servos)
│   │   └── servos.h              (Header file pour servos)
│   ├── vision/
│   │   ├── com_vision.py         (Communication MQTT liée à la vision)
│   │   ├── FaceRecognition.py    (Détection visage/émotion via OpenCV)
│   │   └── ... (Fichiers .xml pour les modèles de détection Haarcascade)
│   └── voice/
│       └── voice_assistant.py    (Gestion microphone + envoi audio au PC)
└── README.md                     (Vous êtes ici)
