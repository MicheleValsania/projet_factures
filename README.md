# Analyseur de Factures PDF pour Restaurants

Cet outil permet d'extraire automatiquement des données structurées (numéro de facture, date, montant total, articles, TVA) à partir de factures au format PDF et de les sauvegarder dans des fichiers CSV. Il s'agit d'une première brique pour un futur logiciel de gestion dédié à la cuisine des restaurants.

## Fonctionnalités
- Extraction initiale des données avec `invoice2data`
- Amélioration et structuration grâce à l'intelligence artificielle (Claude d'Anthropic)
- Sauvegarde dans deux fichiers CSV : un pour les factures, un pour les articles

## Objectif
Aider les restaurateurs français à mieux gérer leurs coûts en transformant leurs factures papier ou PDF en données exploitables, tout en posant les bases d'un outil de gestion culinaire plus large.

## Prérequis
- Python 3.8 ou supérieur
- Une clé API Anthropic (pour l'IA)

## Installation
1. Clonez ce dépôt :
   ```bash
   git clone https://github.com/[votre-username]/analyseur-factures.git
   cd analyseur-factures
## Crédits et Remerciements
Ce projet utilise [invoice2data](https://github.com/invoice-x/invoice2data), une bibliothèque open-source sous licence MIT. Voici leur notice de copyright, conformément à leur licence :

> Copyright (c) 2016 Invoice-X  
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, [...] provided that the above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

J’ai intégré `invoice2data` comme dépendance pour extraire les données initiales des factures PDF, avant de les enrichir avec une intelligence artificielle (Claude d’Anthropic) pour une structuration adaptée aux besoins des restaurateurs. Un grand merci à l’équipe d’Invoice-X pour leur travail formidable !