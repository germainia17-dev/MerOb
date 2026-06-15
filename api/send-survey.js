import nodemailer from 'nodemailer';

const transporter = nodemailer.createTransport({
  service: 'gmail',
  auth: {
    user: process.env.GMAIL_USER,
    pass: process.env.GMAIL_PASSWORD
  }
});

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { userEmail, answers } = req.body;

    // Formater les réponses
    const questions_text = {
      'q1': 'Situation professionnelle',
      'q2': 'Principaux défis',
      'q3': 'Préférence de communication',
      'q4': 'Type de contenu',
      'q5': 'Plus grande force',
      'q6': "Domaine d'amélioration",
      'q7': 'Objectif principal',
      'q8': 'Gestion des échecs',
      'q9': 'Temps disponible',
      'q10': 'Type de soutien',
      'q11': 'Besoin de parler',
      'q12': 'Accepterait IA pour préoccupations',
      'q13': 'Soutien professionnel',
      'q14': 'Niveau de stress',
      'q15': 'PSY pourrait-il aider'
    };

    let emailContent = '<h2>Réponses du sondage PSY</h2>';
    emailContent += `<p><strong>Email de l'utilisateur:</strong> ${userEmail}</p>`;
    emailContent += `<p><strong>Date:</strong> ${new Date().toLocaleString('fr-FR')}</p>`;
    emailContent += '<hr>';
    emailContent += '<table border="1" cellpadding="10" style="border-collapse: collapse; width: 100%;">';
    emailContent += '<tr style="background-color: #f0f0f0;"><th>Question</th><th>Réponse</th></tr>';

    for (let i = 1; i <= 15; i++) {
      const answer = answers[`q${i}`] || 'Non répondu';
      emailContent += `<tr><td>${i}. ${questions_text[`q${i}`]}</td><td>${answer}</td></tr>`;
    }

    emailContent += '</table>';
    emailContent += '<hr>';
    emailContent += '<p><em>Email envoyé automatiquement par PSY Survey</em></p>';

    // Envoyer à l'administrateur
    await transporter.sendMail({
      from: process.env.GMAIL_USER,
      to: 'germain.ia17@gmail.com',
      subject: `Nouvelle réponse de sondage PSY - ${userEmail}`,
      html: emailContent
    });

    // Envoyer une confirmation à l'utilisateur
    const confirmationEmail = `
      <h2>Merci pour votre participation!</h2>
      <p>Bonjour,</p>
      <p>Nous avons reçu vos réponses au sondage PSY avec succès.</p>
      <p>Voici un résumé de vos réponses:</p>
      <hr>
      ${emailContent}
      <hr>
      <p>Nous utiliserons ces informations pour personnaliser votre expérience PSY.</p>
      <p>À bientôt!</p>
      <p><strong>PSY - Votre Assistant Personnel</strong></p>
    `;

    await transporter.sendMail({
      from: process.env.GMAIL_USER,
      to: userEmail,
      subject: 'Confirmation - Votre sondage PSY',
      html: confirmationEmail
    });

    return res.status(200).json({
      success: true,
      message: 'Emails envoyés avec succès'
    });

  } catch (error) {
    console.error('Erreur:', error);
    return res.status(500).json({
      error: 'Erreur lors de l\'envoi du mail',
      details: error.message
    });
  }
}