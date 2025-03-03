# 🚀 Utilisation de la carte OpenRB-150 avec Dynamixel

## 🔄 Upload

    Pour téléverser le programme sur la carte **OpenRB-150**, assurez-vous que la source d'alimentation utilisée est le **port USB**.  
    ⚠️ Sans cela, le port ne sera pas détecté et **VS Code ne pourra pas uploader** le code.

## ▶️ Exécution (Run)

    Pour exécuter le programme avec les moteurs, utilisez une alimentation **12V**.  
    ⚠️ Sans cette alimentation, **les moteurs peuvent ne pas fonctionner correctement**.  

    ✅ Pour des tests légers (exemple : `Get_position` ou `Scan`), le code peut fonctionner avec l’USB.  
    ⚠️ **Attention**, il est recommandé d’utiliser l’alimentation 12V pour éviter toute instabilité.

## 🔍 Identification des moteurs (ID)

    Si l'**ID d'un moteur est inconnu ou perdu**, utilisez le programme **Scan** situé dans le dossier `test`.  
    🔌 **Veuillez brancher un seul moteur à la fois** pour éviter toute confusion.

## 🧪 Tests & Backups

    📁 Le dossier `test` contient des **sauvegardes de programmes `.cpp`** afin de ne pas interférer avec `main.cpp`.  
    📌 Cela permet de remplacer rapidement `main.cpp` par un autre programme temporaire (exemple : une démo)  
    et de **restaurer facilement l’original** en cas de besoin.

---