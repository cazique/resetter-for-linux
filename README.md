# Resetter for Linux

![Logo](https://raw.githubusercontent.com/cazique/resetter-for-linux/main/assets/logo.png)

**Una herramienta de restauración del sistema robusta y segura para distribuciones Linux, escrita en Bash puro para máxima compatibilidad.**

---

### 🌐 Idiomas
- [Español](#-español)
- [English](#-english)
- [Français](#-français)
- [Deutsch](#-deutsch)
- [中文](#-中文)
- [हिन्दी](#-हनद)

---

## 🇪🇸 Español

### 🎯 Visión General
Resetter for Linux es una utilidad de línea de comandos diseñada para ayudar a los administradores de sistemas y usuarios a restaurar su sistema a un estado limpio y predeterminado. Ofrece múltiples niveles de reseteo, desde una simple limpieza de las configuraciones de usuario hasta una purga completa de paquetes no esenciales, devolviendo el sistema a un estado similar al de una instalación nueva.

### ✨ Características Principales
- **Dos Niveles de Reseteo:**
  - **Reseteo Suave:** Limpia los archivos de configuración (`dotfiles`) de todos los usuarios, solucionando problemas de escritorio sin afectar a los programas instalados.
  - **Reseteo Completo:** Elimina todos los paquetes instalados por el usuario y resetea los perfiles, ideal para una restauración completa.
- **Sistema de Backup Avanzado:** Crea copias de seguridad de los datos del usuario, configuraciones del sistema, listas de paquetes e incluso volúmenes e imágenes de Docker antes de cualquier operación.
- **Cifrado de Backups:** Protege tus copias de seguridad con cifrado GPG simétrico basado en contraseña.
- **Simulación (Dry Run):** Permite previsualizar todos los cambios que se realizarían (paquetes a eliminar, ficheros a modificar) sin afectar realmente al sistema.
- **Soporte Multi-distribución:** Diseñado para ser compatible con una amplia gama de distribuciones basadas en Debian, Ubuntu, Fedora y Arch Linux.
- **Gestión de GRUB:** Capaz de respaldar, reinstalar y actualizar la configuración del gestor de arranque GRUB.
- **Interfaz Interactiva:** Un menú fácil de usar que guía al usuario a través de todas las opciones.
- **Soporte Multilingüe:** Disponible en 6 idiomas.

### ⚙️ Instalación
Para instalar Resetter, ejecuta el siguiente comando en tu terminal. El script de instalación detectará tu distribución e instalará las dependencias necesarias.

```bash
curl -fsSL https://raw.githubusercontent.com/cazique/resetter-for-linux/main/scripts/install.sh | sudo bash
```

### 🚀 Uso
Una vez instalado, puedes ejecutar la herramienta con el siguiente comando:
```bash
sudo resetter
```
Esto lanzará el menú interactivo donde podrás seleccionar la operación que deseas realizar:
1.  **Copia de Seguridad:** Crea un backup de tus datos.
2.  **Restablecer Sistema:** Elige entre un reseteo suave o completo.
3.  **Simulación Dry Run:** Previsualiza los cambios antes de aplicarlos.
4.  **Generar Reporte:** Crea un informe del estado actual de tu sistema.
5.  **Restaurar Backup:** (Funcionalidad futura) Restaura desde un backup existente.
6.  **Configuración:** Cambia el idioma de la aplicación.

---

## 🇬🇧 English

### 🎯 Overview
Resetter for Linux is a command-line utility designed to help system administrators and users restore their system to a clean, default state. It offers multiple reset levels, from a simple cleanup of user configurations to a complete purge of non-essential packages, returning the system to a state similar to a fresh installation.

### ✨ Key Features
- **Two Reset Levels:**
  - **Soft Reset:** Cleans all user configuration files (`dotfiles`), fixing desktop issues without affecting installed programs.
  - **Full Reset:** Removes all user-installed packages and resets profiles, ideal for a complete restoration.
- **Advanced Backup System:** Creates backups of user data, system configurations, package lists, and even Docker volumes and images before any operation.
- **Backup Encryption:** Protects your backups with password-based symmetric GPG encryption.
- **Simulation (Dry Run):** Allows you to preview all changes that would be made (packages to be removed, files to be modified) without actually affecting the system.
- **Multi-distribution Support:** Designed to be compatible with a wide range of distributions based on Debian, Ubuntu, Fedora, and Arch Linux.
- **GRUB Management:** Capable of backing up, reinstalling, and updating the GRUB bootloader configuration.
- **Interactive Interface:** An easy-to-use menu that guides the user through all options.
- **Multilingual Support:** Available in 6 languages.

### ⚙️ Installation
To install Resetter, run the following command in your terminal. The installation script will detect your distribution and install the necessary dependencies.
```bash
curl -fsSL https://raw.githubusercontent.com/cazique/resetter-for-linux/main/scripts/install.sh | sudo bash
```

### 🚀 Usage
Once installed, you can run the tool with the following command:
```bash
sudo resetter
```
This will launch the interactive menu where you can select the desired operation:
1.  **Backup:** Create a backup of your data.
2.  **Reset System:** Choose between a soft or full reset.
3.  **Dry Run Simulation:** Preview changes before applying them.
4.  **Generate Report:** Create a report of your system's current state.
5.  **Restore Backup:** (Future functionality) Restore from an existing backup.
6.  **Settings:** Change the application's language.

---

## 🇫🇷 Français

### 🎯 Aperçu
Resetter for Linux est un utilitaire en ligne de commande conçu pour aider les administrateurs système et les utilisateurs à restaurer leur système à un état propre et par défaut. Il propose plusieurs niveaux de réinitialisation, d'un simple nettoyage des configurations utilisateur à une purge complète des paquets non essentiels, ramenant le système à un état similaire à une nouvelle installation.

### ✨ Fonctionnalités Clés
- **Deux Niveaux de Réinitialisation :**
  - **Réinitialisation Douce :** Nettoie tous les fichiers de configuration utilisateur (`dotfiles`), résolvant les problèmes de bureau sans affecter les programmes installés.
  - **Réinitialisation Complète :** Supprime tous les paquets installés par l'utilisateur et réinitialise les profils, idéal pour une restauration complète.
- **Système de Sauvegarde Avancé :** Crée des sauvegardes des données utilisateur, des configurations système, des listes de paquets et même des volumes et images Docker avant toute opération.
- **Chiffrement des Sauvegardes :** Protège vos sauvegardes avec un chiffrement GPG symétrique basé sur un mot de passe.
- **Simulation (Dry Run) :** Permet de prévisualiser toutes les modifications qui seraient apportées (paquets à supprimer, fichiers à modifier) sans affecter réellement le système.
- **Support Multi-distribution :** Conçu pour être compatible avec un large éventail de distributions basées sur Debian, Ubuntu, Fedora et Arch Linux.
- **Gestion de GRUB :** Capable de sauvegarder, réinstaller et mettre à jour la configuration du chargeur de démarrage GRUB.
- **Interface Interactive :** Un menu facile à utiliser qui guide l'utilisateur à travers toutes les options.
- **Support Multilingue :** Disponible en 6 langues.

### ⚙️ Installation
Pour installer Resetter, exécutez la commande suivante dans votre terminal. Le script d'installation détectera votre distribution et installera les dépendances nécessaires.
```bash
curl -fsSL https://raw.githubusercontent.com/cazique/resetter-for-linux/main/scripts/install.sh | sudo bash
```

### 🚀 Utilisation
Une fois installé, vous pouvez lancer l'outil avec la commande suivante :
```bash
sudo resetter
```
Cela lancera le menu interactif où vous pourrez sélectionner l'opération souhaitée :
1.  **Sauvegarde :** Créez une sauvegarde de vos données.
2.  **Réinitialiser le Système :** Choisissez entre une réinitialisation douce ou complète.
3.  **Simulation Dry Run :** Prévisualisez les changements avant de les appliquer.
4.  **Générer un Rapport :** Créez un rapport sur l'état actuel de votre système.
5.  **Restaurer la Sauvegarde :** (Fonctionnalité future) Restaurez à partir d'une sauvegarde existante.
6.  **Paramètres :** Changez la langue de l'application.

---

## 🇩🇪 Deutsch

### 🎯 Überblick
Resetter for Linux ist ein Befehlszeilen-Tool, das Systemadministratoren und Benutzern hilft, ihr System in einen sauberen Standardzustand zurückzusetzen. Es bietet mehrere Rücksetzstufen, von einer einfachen Bereinigung der Benutzerkonfigurationen bis hin zu einer vollständigen Löschung nicht wesentlicher Pakete, wodurch das System in einen Zustand ähnlich einer Neuinstallation versetzt wird.

### ✨ Hauptmerkmale
- **Zwei Rücksetzstufen:**
  - **Sanfter Reset:** Bereinigt alle Benutzerkonfigurationsdateien (`dotfiles`) und behebt Desktop-Probleme, ohne installierte Programme zu beeinträchtigen.
  - **Vollständiger Reset:** Entfernt alle vom Benutzer installierten Pakete und setzt Profile zurück, ideal für eine vollständige Wiederherstellung.
- **Erweitertes Backup-System:** Erstellt vor jedem Vorgang Sicherungen von Benutzerdaten, Systemkonfigurationen, Paketlisten und sogar Docker-Volumes und -Images.
- **Backup-Verschlüsselung:** Schützt Ihre Backups mit passwortbasierter symmetrischer GPG-Verschlüsselung.
- **Simulation (Dry Run):** Ermöglicht eine Vorschau aller Änderungen (zu entfernende Pakete, zu ändernde Dateien), ohne das System tatsächlich zu beeinflussen.
- **Multi-Distributions-Unterstützung:** Entwickelt für die Kompatibilität mit einer Vielzahl von Distributionen, die auf Debian, Ubuntu, Fedora und Arch Linux basieren.
- **GRUB-Verwaltung:** Kann die Konfiguration des GRUB-Bootloaders sichern, neu installieren und aktualisieren.
- **Interaktive Oberfläche:** Ein einfach zu bedienendes Menü, das den Benutzer durch alle Optionen führt.
- **Mehrsprachige Unterstützung:** Verfügbar in 6 Sprachen.

### ⚙️ Installation
Um Resetter zu installieren, führen Sie den folgenden Befehl in Ihrem Terminal aus. Das Installationsskript erkennt Ihre Distribution und installiert die erforderlichen Abhängigkeiten.
```bash
curl -fsSL https://raw.githubusercontent.com/cazique/resetter-for-linux/main/scripts/install.sh | sudo bash
```

### 🚀 Verwendung
Nach der Installation können Sie das Tool mit dem folgenden Befehl ausführen:
```bash
sudo resetter
```
Dies startet das interaktive Menü, in dem Sie den gewünschten Vorgang auswählen können:
1.  **Sicherung:** Erstellen Sie eine Sicherung Ihrer Daten.
2.  **System zurücksetzen:** Wählen Sie zwischen einem sanften oder vollständigen Reset.
3.  **Dry Run-Simulation:** Vorschau der Änderungen vor der Anwendung.
4.  **Bericht erstellen:** Erstellen Sie einen Bericht über den aktuellen Zustand Ihres Systems.
5.  **Sicherung wiederherstellen:** (Zukünftige Funktion) Wiederherstellung aus einer vorhandenen Sicherung.
6.  **Einstellungen:** Ändern Sie die Sprache der Anwendung.

---

## 🌏 中文

### 🎯 概述
Resetter for Linux 是一个命令行实用程序，旨在帮助系统管理员和用户将其系统恢复到干净的默认状态。它提供多个重置级别，从简单的用户配置清理到完全清除非必要软件包，使系统恢复到类似于全新安装的状态。

### ✨ 主要功能
- **两种重置级别：**
  - **软重置：** 清理所有用户配置文件（`dotfiles`），解决桌面问题而不影响已安装的程序。
  - **完全重置：** 删除所有用户安装的软件包并重置配置文件，非常适合完全恢复。
- **高级备份系统：** 在执行任何操作之前，创建用户数据、系统配置、软件包列表甚至 Docker 卷和镜像的备份。
- **备份加密：** 使用基于密码的对称 GPG 加密保护您的备份。
- **模拟（Dry Run）：** 允许您预览将要进行的所有更改（要删除的软件包、要修改的文件），而不会实际影响系统。
- **多发行版支持：** 设计用于与基于 Debian、Ubuntu、Fedora 和 Arch Linux 的各种发行版兼容。
- **GRUB 管理：** 能够备份、重新安装和更新 GRUB 引导加载程序配置。
- **交互式界面：** 一个易于使用的菜单，引导用户完成所有选项。
- **多语言支持：** 提供 6 种语言版本。

### ⚙️ 安装
要安装 Resetter，请在终端中运行以下命令。安装脚本将检测您的发行版并安装必要的依赖项。
```bash
curl -fsSL https://raw.githubusercontent.com/cazique/resetter-for-linux/main/scripts/install.sh | sudo bash
```

### 🚀 使用
安装后，您可以使用以下命令运行该工具：
```bash
sudo resetter
```
这将启动交互式菜单，您可以在其中选择所需的操作：
1.  **备份：** 创建数据备份。
2.  **重置系统：** 在软重置或完全重置之间进行选择。
3.  **模拟运行：** 在应用更改之前预览更改。
4.  **生成报告：** 创建系统当前状态的报告。
5.  **恢复备份：** （未来功能）从现有备份中恢复。
6.  **设置：** 更改应用程序的语言。

---

## 🇮🇳 हिन्दी

### 🎯 अवलोकन
Resetter for Linux एक कमांड-लाइन उपयोगिता है जिसे सिस्टम प्रशासकों और उपयोगकर्ताओं को अपने सिस्टम को एक स्वच्छ, डिफ़ॉल्ट स्थिति में पुनर्स्थापित करने में मदद करने के लिए डिज़ाइन किया गया है। यह कई रीसेट स्तर प्रदान करता है, उपयोगकर्ता कॉन्फ़िगरेशन की एक साधारण सफाई से लेकर गैर-आवश्यक पैकेजों की पूरी तरह से सफाई तक, सिस्टम को एक नई स्थापना के समान स्थिति में लौटाता है।

### ✨ मुख्य विशेषताएँ
- **दो रीसेट स्तर:**
  - **सॉफ्ट रीसेट:** सभी उपयोगकर्ता कॉन्फ़िगरेशन फ़ाइलों (`dotfiles`) को साफ करता है, स्थापित प्रोग्राम को प्रभावित किए बिना डेस्कटॉप समस्याओं को ठीक करता है।
  - **पूर्ण रीसेट:** सभी उपयोगकर्ता-स्थापित पैकेजों को हटाता है और प्रोफाइल को रीसेट करता है, जो पूर्ण पुनर्स्थापना के लिए आदर्श है।
- **उन्नत बैकअप सिस्टम:** किसी भी ऑपरेशन से पहले उपयोगकर्ता डेटा, सिस्टम कॉन्फ़िगरेशन, पैकेज सूचियों और यहां तक कि डॉकर वॉल्यूम और छवियों का बैकअप बनाता है।
- **बैकअप एन्क्रिप्शन:** आपके बैकअप को पासवर्ड-आधारित सममित GPG एन्क्रिप्शन से सुरक्षित रखता है।
- **सिमुलेशन (ड्राई रन):** आपको वास्तव में सिस्टम को प्रभावित किए बिना किए जाने वाले सभी परिवर्तनों (हटाए जाने वाले पैकेज, संशोधित की जाने वाली फाइलें) का पूर्वावलोकन करने की अनुमति देता है।
- **बहु-वितरण समर्थन:** डेबियन, उबंटू, फेडोरा और आर्च लिनक्स पर आधारित वितरणों की एक विस्तृत श्रृंखला के साथ संगत होने के लिए डिज़ाइन किया गया है।
- **GRUB प्रबंधन:** GRUB बूटलोडर कॉन्फ़िगरेशन का बैकअप, पुनर्स्थापना और अद्यतन करने में सक्षम।
- **इंटरैक्टिव इंटरफ़ेस:** एक उपयोग में आसान मेनू जो उपयोगकर्ता को सभी विकल्पों के माध्यम से मार्गदर्शन करता है।
- **बहुभाषी समर्थन:** 6 भाषाओं में उपलब्ध है।

### ⚙️ स्थापना
Resetter स्थापित करने के लिए, अपने टर्मिनल में निम्नलिखित कमांड चलाएँ। स्थापना स्क्रिप्ट आपके वितरण का पता लगाएगी और आवश्यक निर्भरताएँ स्थापित करेगी।
```bash
curl -fsSL https://raw.githubusercontent.com/cazique/resetter-for-linux/main/scripts/install.sh | sudo bash
```

### 🚀 उपयोग
एक बार स्थापित हो जाने पर, आप निम्न कमांड के साथ टूल चला सकते हैं:
```bash
sudo resetter
```
यह इंटरैक्टिव मेनू लॉन्च करेगा जहां आप वांछित ऑपरेशन का चयन कर सकते हैं:
1.  **बैकअप:** अपने डेटा का बैकअप बनाएं।
2.  **सिस्टम रीसेट करें:** सॉफ्ट या पूर्ण रीसेट के बीच चयन करें।
3.  **ड्राई रन सिमुलेशन:** उन्हें लागू करने से पहले परिवर्तनों का पूर्वावलोकन करें।
4.  **रिपोर्ट बनाएं:** अपने सिस्टम की वर्तमान स्थिति की एक रिपोर्ट बनाएं।
5.  **बैकअप पुनर्स्थापित करें:** (भविष्य की कार्यक्षमता) मौजूदा बैकअप से पुनर्स्थापित करें।
6.  **सेटिंग्स:** एप्लिकेशन की भाषा बदलें।
