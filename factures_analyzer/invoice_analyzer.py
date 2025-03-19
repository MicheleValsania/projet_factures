import os
import sys
import json
import csv
import re
from datetime import datetime
from invoice2data import extract_data
from invoice2data.extract.loader import read_templates
from anthropic import Anthropic

# Configuration de l'API Claude
ANTHROPIC_API_KEY = "votre clé API"  # Remplacez par votre clé API
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Chemins des fichiers CSV de sortie
OUTPUT_CSV = "factures_extraites.csv"
ARTICLES_CSV = "articles_factures.csv"

def traiter_facture_avec_invoice2data(chemin_pdf):
    """Extrait les données de la facture avec invoice2data"""
    templates = read_templates()
    try:
        result = extract_data(chemin_pdf, templates=templates)
        return result
    except Exception as e:
        print(f"Erreur lors de l'extraction avec invoice2data : {e}")
        return {}

def extraire_texte_du_pdf(chemin_pdf):
    """Extrait le texte du PDF pour l'envoyer à Claude"""
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

def ameliorer_avec_claude(donnees_facture, texte_pdf):
    """Améliore l'extraction des données en utilisant Claude"""
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
      "montant_total": "XXX,XX",
      "tva": {{ "taux1": "montant1", "taux2": "montant2", ... }},
      "fournisseur": "Nom du fournisseur",
      "articles": [
        {{
          "description": "Description de l'article",
          "quantite": "X",
          "prix_unitaire": "XX,XX",
          "montant": "XX,XX",
          "taux_tva": "X%"
        }},
        ...
      ]
    }}
    
    N'inclus pas de symbole de devise (€, $, etc.) dans les valeurs numériques.
    """
    
    try:
        message = anthropic_client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
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
    """Extrait le JSON de la réponse de Claude"""
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
        
        # Charge le JSON
        donnees_extraites = json.loads(texte_json)
        print(f"JSON extrait avec succès : {texte_json[:100]}...")
        return donnees_extraites
    except Exception as e:
        print(f"Erreur lors de l'extraction du JSON de la réponse de Claude : {e}")
        print(f"Type de réponse : {type(reponse)}")
        
        # Pour le débogage
        if isinstance(reponse, str):
            print(f"Début de la réponse : {reponse[:200]}...")
        elif isinstance(reponse, list) and len(reponse) > 0:
            if hasattr(reponse[0], 'text'):
                print(f"Début du TextBlock : {reponse[0].text[:200]}...")
        
        # Dernier recours : essayer d'extraire manuellement
        try:
            if isinstance(reponse, list) and len(reponse) > 0:
                block = reponse[0]
                if hasattr(block, 'text'):
                    texte = block.text
                    if "```json" in texte:
                        texte_json = texte.split("```json")[1].split("```")[0].strip()
                        json_data = json.loads(texte_json)
                        print("Extraction manuelle réussie!")
                        return json_data
        except Exception as nested_e:
            print(f"Échec de l'extraction manuelle : {nested_e}")
        
        return {}

def nettoyer_valeur_monetaire(valeur):
    """Nettoie une valeur monétaire en enlevant les symboles de devise et en normalisant la notation décimale"""
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
    """Sauvegarde les données des factures dans un fichier CSV"""
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
    """Sauvegarde les données des articles dans un fichier CSV"""
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
    """Aplatit les données de la facture pour le CSV principal"""
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
    """Extrait les articles de la facture pour le CSV des articles"""
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
    """Traite un seul fichier PDF et ajoute les données aux listes"""
    print(f"\nTraitement de la facture : {chemin_pdf}")
    
    # Extraction initiale avec invoice2data
    donnees_facture = traiter_facture_avec_invoice2data(chemin_pdf)
    print("\nDonnées extraites avec invoice2data :")
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
    # Correction de l'affichage pour gérer à la fois les chaînes et les listes
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
    """Fonction principale qui démarre le processus"""
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