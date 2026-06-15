# 📋 Déploiement du Sondage PSY

## 🚀 Déployer sur Vercel (Gratuit)

### Étape 1: Préparer Gmail

1. **Activer l'authentification 2FA** sur votre compte Gmail
2. **Générer un mot de passe d'application:**
   - Aller sur: https://myaccount.google.com/apppasswords
   - Sélectionner "Mail" et "Windows/Mac/Linux"
   - Google génère un mot de passe de 16 caractères
   - Copier ce mot de passe (sans espaces)

### Étape 2: Configurer Vercel

1. **Installer Vercel CLI:**
```bash
npm install -g vercel
```

2. **Connecter à Vercel:**
```bash
vercel login
```

3. **Ajouter les variables d'environnement:**
```bash
vercel env add GMAIL_USER
# Entrez: germain.ia17@gmail.com

vercel env add GMAIL_PASSWORD
# Entrez: votre-mot-de-passe-application-16-caractères
```

4. **Déployer le projet:**
```bash
vercel --prod
```

### Étape 3: Récupérer le lien public

Après le déploiement, Vercel vous donnera une URL comme:
```
https://psy-survey.vercel.app
```

Ce lien est **public et partageable!**

---

## 🔧 Configuration manuelle (Alternative)

### Via Dashboard Vercel

1. Allez sur [vercel.com](https://vercel.com)
2. Cliquez "New Project"
3. Connectez votre repo GitHub
4. Allez dans "Settings" → "Environment Variables"
5. Ajoutez:
   - `GMAIL_USER`: germain.ia17@gmail.com
   - `GMAIL_PASSWORD`: votre-mot-de-passe-app
6. Cliquez "Deploy"

---

## 📧 Vérifier que ça marche

1. Allez sur votre URL Vercel
2. Remplissez le sondage
3. Entrez votre email (par exemple: test@gmail.com)
4. Cliquez "Soumettre le sondage"
5. Vérifiez germain.ia17@gmail.com pour les réponses

---

## 🛡️ Sécurité

- ✅ Les mots de passe **ne sont jamais** en git
- ✅ Les variables sont **chiffrées** sur Vercel
- ✅ Les données sont envoyées en **HTTPS**
- ✅ Les emails sont **supprimés après 30 jours** sur Gmail

---

## 🆘 Dépannage

### "Erreur: Erreur lors de l'envoi"
- Vérifiez que le mot de passe d'application est correct (16 caractères)
- Vérifiez que 2FA est activé sur Gmail
- Attendez quelques minutes et réessayez

### "Email non reçu"
- Vérifiez le dossier Spam
- Vérifiez que `GMAIL_USER` = germain.ia17@gmail.com

### "Fonction API non trouvée"
- Vérifiez que le fichier `api/send-survey.js` existe
- Attendez que Vercel termine le déploiement (5-10 min)

---

## 📊 Voir les réponses

Les réponses arrivent dans germain.ia17@gmail.com avec un format:
```
Nouvelle réponse de sondage PSY - utilisateur@email.com
```

Chaque email contient un tableau avec toutes les réponses.

---

## 🎉 Partager le lien

Vous pouvez maintenant partager le lien public:
```
https://votre-domaine.vercel.app
```

Ou le personnaliser avec un domaine:
1. Allez dans Vercel → Project Settings
2. Onglet "Domains"
3. Connectez votre domaine

Exemple: `https://psy-survey.com`
