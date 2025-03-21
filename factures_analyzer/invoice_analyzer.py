# analyseur_factures.py
# Copyright (c) 2025 [Votre Nom]
# Distribué sous la Licence Publique Générale GNU v3 (voir LICENSE)
#
# Ce script utilise invoice2data (https://github.com/invoice-x/invoice2data) comme dépendance,
# sous la licence MIT :
#   Copyright (c) 2016 Invoice-X
#   Permission is hereby granted, free of charge, to any person obtaining a copy
#   of this software and associated documentation files (the "Software"), to deal
#   in the Software without restriction, [...] provided that the above copyright
#   notice and this permission notice shall be included in all copies or substantial
#   portions of the Software.
# Merci à Invoice-X pour leur outil d'extraction que j'ai étendu avec une IA !

import os
import sys  # Ajout de l'importation manquante
import json
import csv
import re
from datetime import datetime
from invoice2data import extract_data
from invoice2data.extract.loader import read_templates
from anthropic import Anthropic

# Configuration de l'API Claude
<<<<<<< HEAD
ANTHROPIC_API_KEY = " Remplacez par votre clé API "
=======
ANTHROPIC_API_KEY = ""  # Remplacez par votre clé API
>>>>>>> 184601b (remove secret)
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Chemins des fichiers CSV de sortie
OUTPUT_CSV = "factures_extraites.csv"
ARTICLES_CSV = "articles_factures.csv"

def traiter_facture_avec_invoice2data(chemin_pdf):
    """Extrait les données de la facture avec invoice2data."""
    # Charge les templates par défaut
    templates = read_templates()
    
    # Charge les templates personnalisés depuis le dossier templates
    templates_dir = "templates"
    print(f"Chargement des templates depuis le dossier : {templates_dir}")
    if os.path.exists(templates_dir):
        for template_file in os.listdir(templates_dir):
            if template_file.endswith(".yml"):
                template_path = os.path.join(templates_dir, template_file)
                print(f"Chargement du template : {template_path}")
                templates.extend(read_templates(template_path))
    
    try:
        print(f"Tentative d'extraction avec invoice2data pour {chemin_pdf}...")
        result = extract_data(chemin_pdf, templates=templates)
        return result
    except Exception as e:
        print(f"Erreur lors de l'extraction avec invoice2data : {e}")
        return {}

def extraire_texte_du_pdf(chemin_pdf):
    """Extrait le texte du PDF pour l'envoyer à Claude."""
    try:
        import pdfplumber
        with pdfplumber.open(chemin_pdf) as pdf:
            texte = ""
            for page in pdf.pages:
                texte += page.extract_text() or ""
        return texte
    except ImportError:
        print("Installez pdfplumber avec : pip install pdfplumber")
        return ""
    except Exception as e:
        print(f"Erreur lors de l'extraction du texte du PDF {chemin_pdf} : {e}")
        return ""

def generer_template_avec_claude(texte_pdf, nom_fichier):
    """Demande à Claude de générer un template YAML pour invoice2data."""
    prompt = f"""
    Voici le texte brut d'une facture :
{texte_pdf[:4000]} # Limité pour ne pas dépasser les limites de l'API
    Génère un template YAML pour invoice2data qui peut extraire les informations suivantes :
    - Numéro de facture
    - Date
    - Montant total
    - Lignes d'articles (description, quantité, unité, prix unitaire, montant)
    Le template doit être au format YAML strictement structuré comme ceci :
    ```yaml
    issuer: Nom du fournisseur
    keywords:
    - Mot clé 1
    - Mot clé 2
    fields:
      date: REGEX_POUR_DATE
      invoice_number: REGEX_POUR_NUMERO
      amount: REGEX_POUR_MONTANT
    lines:
      start: REGEX_POUR_DEBUT_LIGNES
      end: REGEX_POUR_FIN_LIGNES
      line: (?P<desc>.+)\\s+(?P<qty>\\d+)\\s+(?P<unit>\\S+)\\s+(?P<price>\\d+\\.\\d+)\\s+(?P<total>\\d+\\.\\d+)
    options:
      currency: EUR
      decimal_separator: "."
    ```
    Règles importantes :
    Utilise le point (.) comme séparateur décimal dans les regex.
    Assure-toi que les regex correspondent au format exact du texte (ex. "TOTAL 123.45", "FACTURE FCL2024127111").
    Inclue des mots clés uniques pour identifier cette facture.
    Le template doit être complet et prêt à être utilisé par invoice2data.
    """
    try:
        message = anthropic_client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            system="Tu es un assistant spécialisé dans la création de templates pour invoice2data. Ta tâche est de générer un template YAML fonctionnel basé sur le texte d'une facture.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content
    except Exception as e:
        print(f"Erreur lors de la génération du template avec Claude : {e}")
        return None

def extraire_yaml_de_reponse_claude(reponse):
    """Extrait le YAML de la réponse de Claude."""
    try:
        if isinstance(reponse, list):
            texte_reponse = ""
            for block in reponse:
                if hasattr(block, 'text'):
                    texte_reponse += block.text
            reponse = texte_reponse
        
        if "```yaml" in reponse:
            texte_yaml = reponse.split("```yaml")[1].split("```")[0].strip()
        elif "```" in reponse:
            texte_yaml = reponse.split("```")[1].strip()
        else:
            texte_yaml = reponse.strip()
        
        return texte_yaml
    except Exception as e:
        print(f"Erreur lors de l'extraction du YAML de la réponse de Claude : {e}")
        return None

def sauvegarder_template(nom_fichier, template_yaml):
    """Sauvegarde le template YAML dans le dossier templates."""
    templates_dir = "templates"
    if not os.path.exists(templates_dir):
        print(f"Création du dossier {templates_dir}...")
        os.makedirs(templates_dir)
    
    # Utilise le nom du fichier (sans extension) pour le template
    nom_template = os.path.splitext(os.path.basename(nom_fichier))[0] + ".yml"
    chemin_template = os.path.join(templates_dir, nom_template)
    
    try:
        with open(chemin_template, 'w', encoding='utf-8') as f:
            f.write(template_yaml)
        print(f"Template sauvegardé avec succès : {chemin_template}")
        print(f"Contenu du template généré :\n{template_yaml}\n")
        return chemin_template
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du template : {e}")
        return None

def ameliorer_avec_claude(donnees_facture, texte_pdf):
    """Améliore l'extraction des données en utilisant Claude."""
    prompt = f"""
Voici les données extraites d'une facture : {donnees_facture}

Et voici le texte brut de la facture :
{texte_pdf[:4000]}  # Limité pour ne pas dépasser les limites de l'API

Extrais les informations suivantes et corrige-les si nécessaire :
- Numéro de facture
- Date
- Montant total
- TVA (indique les différents taux de TVA si plusieurs sont présents)
- Fournisseur
- Articles/services avec leur quantité, prix unitaire, montant et taux de TVA

Réponds au format JSON strictement structuré comme ceci :
{{
  "numero_facture": "XXX",
  "date": "JJ/MM/AAAA",
  "montant_total": "XXX.XX",
  "tva": {{ "taux1": "montant1", "taux2": "montant2", ... }},
  "fournisseur": "Nom du fournisseur",
  "articles": [
    {{
      "description": "Description de l'article",
      "quantite": "X",
      "prix_unitaire": "XX.XX",
      "montant": "XX.XX",
      "taux_tva": "X%"
    }},
    ...
  ]
}}

Règles importantes :
- Utilise le point (.) comme séparateur décimal, et non la virgule (ex. "123.45", et non "123,45").
- Pour les taux de TVA dans l'objet "tva", utilise uniquement le nombre comme clé, sans le symbole % (ex. "5.5" au lieu de "5.5%").
- N'inclus pas de symbole de devise (€, $, etc.) dans les valeurs numériques.
- Assure-toi que le JSON soit complet et bien formaté.
- Si la facture a plusieurs pages, extrais uniquement les données de la page fournie.
"""
    
    try:
        message = anthropic_client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=2000,
            system="Tu es un assistant spécialisé dans l'extraction de données des factures. Ta tâche est d'extraire les informations structurées d'une facture et de les renvoyer dans un format JSON clair et cohérent.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content
    except Exception as e:
        print(f"Erreur lors de l'utilisation de l'API Claude : {e}")
        return "Erreur lors de l'appel API"

def extraire_json_de_reponse_claude(reponse):
    """Extrait le JSON de la réponse de Claude."""
    try:
        # Vérifie si la réponse est une liste de TextBlock
        if isinstance(reponse, list):
            texte_reponse = ""
            for block in reponse:
                if hasattr(block, 'text'):
                    texte_reponse += block.text
            reponse = texte_reponse
        
        # Recherche le bloc JSON dans la réponse
        if "```json" in reponse:
            texte_json = reponse.split("```json")[1].split("```")[0].strip()
        elif "```" in reponse:
            texte_json = reponse.split("```")[1].strip()
        else:
            texte_json = reponse.strip()
        
        # Remplace les virgules par des points dans les taux de TVA
        texte_json = re.sub(r'"(\d+),(\d+)"', r'"\1.\2"', texte_json)
        
        # Charge le JSON
        donnees_extraites = json.loads(texte_json)
        print(f"JSON extrait avec succès : {texte_json[:100]}...")
        return donnees_extraites
    except Exception as e:
        print(f"Erreur lors de l'extraction du JSON de la réponse de Claude : {e}")
        print(f"Risposta complète : {reponse}")
        return {}

def nettoyer_valeur_monetaire(valeur):
    """Nettoie une valeur monétaire en enlevant les symboles de devise et en normalisant la notation décimale."""
    if not valeur:
        return ""
    # Convertit en chaîne si ce n'est pas déjà le cas
    valeur_str = str(valeur)
    # Supprime tous les symboles de devise et caractères non numériques sauf la virgule et le point
    valeur_propre = re.sub(r'[^\d,.\-]', '', valeur_str)
    # Remplace la virgule par un point pour la notation décimale standard
    valeur_propre = valeur_propre.replace(',', '.')
    return valeur_propre

def sauvegarder_factures_en_csv(liste_donnees):
    """Sauvegarde les données des factures dans un fichier CSV."""
    if not liste_donnees:
        print("Aucune donnée de facture à sauvegarder.")
        return False
    
    try:
        # Détermine les en-têtes basés sur toutes les clés dans tous les enregistrements
        entetes = set()
        for donnees in liste_donnees:
            entetes.update(donnees.keys())
        
        entetes = sorted(list(entetes))
        
        # Écrit dans le fichier CSV
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=entetes)
            writer.writeheader()
            for donnees in liste_donnees:
                writer.writerow(donnees)
        
        print(f"Données des factures sauvegardées avec succès dans {OUTPUT_CSV}")
        return True
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du CSV des factures : {e}")
        return False

def sauvegarder_articles_en_csv(liste_articles):
    """Sauvegarde les données des articles dans un fichier CSV."""
    if not liste_articles:
        print("Aucun article à sauvegarder.")
        return False
    
    try:
        # Détermine les en-têtes basés sur toutes les clés dans tous les enregistrements
        entetes = set()
        for article in liste_articles:
            entetes.update(article.keys())
        
        entetes = sorted(list(entetes))
        
        # Écrit dans le fichier CSV
        with open(ARTICLES_CSV, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=entetes)
            writer.writeheader()
            for article in liste_articles:
                writer.writerow(article)
        
        print(f"Données des articles sauvegardées avec succès dans {ARTICLES_CSV}")
        return True
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du CSV des articles : {e}")
        return False

def aplatir_donnees_facture(donnees_facture, nom_fichier):
    """Aplatit les données de la facture pour le CSV principal."""
    donnees_plates = {
        "nom_fichier": os.path.basename(nom_fichier),
        "date_extraction": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Mappings des noms de champs possibles
    mappings_champs = {
        "numero_facture": ["numero_fattura", "numero_facture", "numero"],
        "date": ["data", "date"],
        "montant_total": ["importo_totale", "montant_total", "total"],
        "fournisseur": ["fornitore", "fournisseur"]
    }
    
    # Ajoute les champs principaux en vérifiant tous les noms possibles
    for cle_cible, cles_possibles in mappings_champs.items():
        for cle in cles_possibles:
            if cle in donnees_facture:
                if cle_cible.startswith("montant"):
                    donnees_plates[cle_cible] = nettoyer_valeur_monetaire(donnees_facture[cle])
                else:
                    donnees_plates[cle_cible] = donnees_facture[cle]
                break
    
    # Traitement de la TVA (peut être un objet ou une chaîne)
    if "tva" in donnees_facture:
        if isinstance(donnees_facture["tva"], dict):
            # Plusieurs taux de TVA
            for taux, montant in donnees_facture["tva"].items():
                donnees_plates[f"tva_{taux}"] = nettoyer_valeur_monetaire(montant)
            
            # TVA totale si disponible
            if "total" in donnees_facture["tva"]:
                donnees_plates["tva_totale"] = nettoyer_valeur_monetaire(donnees_facture["tva"]["total"])
        else:
            # TVA unique
            donnees_plates["tva"] = nettoyer_valeur_monetaire(donnees_facture["tva"])
    elif "iva" in donnees_facture:
        if isinstance(donnees_facture["iva"], dict):
            for taux, montant in donnees_facture["iva"].items():
                donnees_plates[f"tva_{taux}"] = nettoyer_valeur_monetaire(montant)
            
            if "total" in donnees_facture["iva"]:
                donnees_plates["tva_totale"] = nettoyer_valeur_monetaire(donnees_facture["iva"]["total"])
        else:
            donnees_plates["tva"] = nettoyer_valeur_monetaire(donnees_facture["iva"])
    
    print(f"Données de facture formatées : {donnees_plates}")
    return donnees_plates

def extraire_articles(donnees_facture, nom_fichier, numero_facture):
    """Extrait les articles de la facture pour le CSV des articles."""
    articles = []
    
    # Clés possibles pour les articles
    cles_articles = ["articles", "articoli", "items", "lignes"]
    
    # Recherche de la liste des articles
    liste_articles = None
    for cle in cles_articles:
        if cle in donnees_facture and isinstance(donnees_facture[cle], list):
            liste_articles = donnees_facture[cle]
            break
    
    if not liste_articles:
        print("Aucun article trouvé dans les données extraites.")
        return articles
    
    print(f"Nombre d'articles trouvés : {len(liste_articles)}")
    
    # Mappings des noms de champs pour les articles
    mappings_champs_articles = {
        "description": ["description", "descrizione", "libelle", "designation"],
        "quantite": ["quantite", "quantité", "quantita", "quantità", "qty"],
        "prix_unitaire": ["prix_unitaire", "prezzo_unitario", "unit_price", "pu"],
        "montant": ["montant", "importo", "amount", "total"],
        "taux_tva": ["taux_tva", "aliquota_iva", "tva", "vat_rate"]
    }
    
    # Traitement de chaque article
    for index, article in enumerate(liste_articles):
        article_traite = {
            "nom_fichier": os.path.basename(nom_fichier),
            "numero_facture": numero_facture,
            "ligne": index + 1
        }
        
        # Extraction des champs de l'article
        for cle_cible, cles_possibles in mappings_champs_articles.items():
            for cle in cles_possibles:
                if cle in article:
                    if cle_cible in ["montant", "prix_unitaire"]:
                        article_traite[cle_cible] = nettoyer_valeur_monetaire(article[cle])
                    else:
                        article_traite[cle_cible] = article[cle]
                    break
        
        articles.append(article_traite)
    
    print(f"Articles formatés : {len(articles)}")
    return articles

def traiter_fichier_unique(chemin_pdf, toutes_donnees, tous_articles):
    """Traite un seul fichier PDF et ajoute les données aux listes."""
    print(f"\nTraitement de la facture : {chemin_pdf}")
    
    # Extraction initiale avec invoice2data
    donnees_facture = traiter_facture_avec_invoice2data(chemin_pdf)
    print("\nDonnées extraites avec invoice2data :")
    print(donnees_facture)
    
    # Si invoice2data échoue, génère un template avec Claude
    if not donnees_facture:
        print("invoice2data n'a pas trouvé de template. Génération d'un template avec Claude...")
        texte_pdf = extraire_texte_du_pdf(chemin_pdf)
        if not texte_pdf:
            print("Impossible d'extraire le texte du PDF.")
            return
        
        reponse_template = generer_template_avec_claude(texte_pdf, chemin_pdf)
        if reponse_template:
            template_yaml = extraire_yaml_de_reponse_claude(reponse_template)
            if template_yaml:
                chemin_template = sauvegarder_template(chemin_pdf, template_yaml)
                if chemin_template:
                    # Réessaie l'extraction avec le nouveau template
                    donnees_facture = traiter_facture_avec_invoice2data(chemin_pdf)
                    print("\nDonnées extraites avec invoice2data après ajout du template :")
                    print(donnees_facture)
    
    # Extraction du texte pour Claude
    texte_pdf = extraire_texte_du_pdf(chemin_pdf)
    if not texte_pdf:
        print("Impossible d'extraire le texte du PDF.")
        return
    
    # Amélioration avec Claude
    print("\nConsultation de Claude pour améliorer l'extraction...")
    reponse_claude = ameliorer_avec_claude(donnees_facture, texte_pdf)
    
    print("\nDonnées améliorées par Claude :")
    if isinstance(reponse_claude, list):
        print("[Liste d'objets TextBlock]")
    else:
        reponse_str = str(reponse_claude)
        print(reponse_str[:500] + "..." if len(reponse_str) > 500 else reponse_str)
    
    # Extrait le JSON de la réponse de Claude
    donnees_extraites = extraire_json_de_reponse_claude(reponse_claude)
    
    if donnees_extraites:
        print("Données JSON extraites avec succès !")
        
        # Récupération du numéro de facture pour lier les articles
        numero_facture = None
        for cle in ["numero_facture", "numero_fattura", "numero"]:
            if cle in donnees_extraites:
                numero_facture = donnees_extraites[cle]
                break
        
        if not numero_facture:
            numero_facture = os.path.basename(chemin_pdf)  # Utilise le nom du fichier comme fallback
        
        # Aplatit les données pour le CSV principal
        donnees_plates = aplatir_donnees_facture(donnees_extraites, chemin_pdf)
        if donnees_plates:
            toutes_donnees.append(donnees_plates)
            print(f"Données de facture ajoutées. Nombre total de factures : {len(toutes_donnees)}")
        
        # Extrait les articles pour le CSV des articles
        articles = extraire_articles(donnees_extraites, chemin_pdf, numero_facture)
        if articles:
            tous_articles.extend(articles)
            print(f"Articles ajoutés. Nombre total d'articles : {len(tous_articles)}")
    else:
        print("Échec de l'extraction des données JSON. Aucune donnée à ajouter.")

def main():
    """Fonction principale qui démarre le processus."""
    if len(sys.argv) < 2:
        print("Usage : python analyseur_factures.py chemin_vers_fichier.pdf OU chemin_vers_repertoire")
        return
    
    chemin = sys.argv[1]
    
    if not os.path.exists(chemin):
        print(f"Le chemin {chemin} n'existe pas.")
        return
    
    toutes_donnees_extraites = []
    tous_articles_extraits = []
    
    if os.path.isdir(chemin):
        print(f"Traitement de tous les PDF dans le répertoire : {chemin}")
        for nom_fichier in os.listdir(chemin):
            if nom_fichier.lower().endswith('.pdf'):
                chemin_pdf = os.path.join(chemin, nom_fichier)
                traiter_fichier_unique(chemin_pdf, toutes_donnees_extraites, tous_articles_extraits)
    else:
        if not chemin.lower().endswith('.pdf'):
            print(f"Le fichier {chemin} ne semble pas être un PDF.")
            return
        traiter_fichier_unique(chemin, toutes_donnees_extraites, tous_articles_extraits)
    
    # Sauvegarde toutes les données extraites dans des CSV
    print(f"\nTentative de sauvegarde des données. Nombre de factures : {len(toutes_donnees_extraites)}")
    if toutes_donnees_extraites:
        sauvegarder_factures_en_csv(toutes_donnees_extraites)
    else:
        print("Aucune donnée de facture à sauvegarder.")
    
    print(f"Tentative de sauvegarde des articles. Nombre d'articles : {len(tous_articles_extraits)}")
    if tous_articles_extraits:
        sauvegarder_articles_en_csv(tous_articles_extraits)
    else:
        print("Aucun article à sauvegarder.")
    
    print("\nTraitement terminé !")

if __name__ == "__main__":
    main()
