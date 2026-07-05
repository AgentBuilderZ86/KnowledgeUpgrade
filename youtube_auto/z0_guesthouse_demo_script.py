"""
Script de démonstration généré pour Z0 Guesthouse.
Ce script montre la structure exacte que le pipeline générerait avec un vrai appel Claude.
"""

import json

demo_script = {
    "titre_video": "Z0 Guesthouse : où le design minimaliste rencontre la sérénité absolue",
    "description_youtube": """Il existe des places qui changent votre rapport au silence, à la lumière, à vous-même.
Z0 Guesthouse est l'une d'elles.

À travers une visite intime et calme, découvrez comment chaque détail architectural, chaque matériau brut, chaque ligne épurée a été pensé pour créer un havre de paix loin du bruit du quotidien.

Ce n'est pas une chambre d'hôtel. C'est une expérience.

🏡 Z0 Guesthouse
→ Design minimaliste & architecture réfléchie
→ Matériaux bruts, lumière naturelle
→ Intimité & connexion au lieu
→ Une invitation à ralentir

Parfait pour :
- Les créatifs en quête d'inspiration
- Ceux qui cherchent une pause loin du monde
- Quiconque apprécie le design et la sérénité

✨ Explorez Z0 Guesthouse, où l'architecture parle plus fort que les mots.""",
    "tags": [
        "z0 guesthouse",
        "luxury guesthouse",
        "minimalist design",
        "architecture",
        "luxury travel",
        "boutique hotel",
        "design accommodation",
        "serenity",
        "minimalism",
        "architectural design"
    ],
    "segments": [
        {
            "timestamp_debut": 0,
            "timestamp_fin": 30,
            "texte_narration": "Il existe des lieux où le temps s'arrête. Où chaque silence parle plus fort que mille mots. Z0 Guesthouse est un de ces havres rares où l'architecture et la sérénité dansent ensemble.",
            "image_query": "minimalist architecture exterior calm serene",
            "texte_ecran": "Z0 GUESTHOUSE"
        },
        {
            "timestamp_debut": 30,
            "timestamp_fin": 75,
            "texte_narration": "Nichée loin des bruits du quotidien, Z0 n'est pas une chambre d'hôtel ordinaire. C'est une invitation à ralentir. À respirer. À redécouvrir le pouvoir du minimalisme et de l'espace.",
            "image_query": "modern minimal architecture outdoor space natural light",
            "texte_ecran": "ÉCHAPPER. RESPIRER. REDÉCOUVRIR."
        },
        {
            "timestamp_debut": 75,
            "timestamp_fin": 120,
            "texte_narration": "Chaque matériau a été choisi avec précision. Béton brut, bois naturel, pierre locale. Les lignes épurées guident l'œil sans le distraire. Ici, moins est infiniment plus.",
            "image_query": "raw concrete wood stone minimalist interior design detail",
            "texte_ecran": "CHAQUE DÉTAIL COMPTE"
        },
        {
            "timestamp_debut": 120,
            "timestamp_fin": 165,
            "texte_narration": "La lumière naturelle traverse les grandes baies vitrées, sculptant les formes, caressant les surfaces. Pas d'ornements inutiles. Pas de bruit visuel. Juste l'essentiel.",
            "image_query": "natural light interior sunlight architectural photography",
            "texte_ecran": "LA LUMIÈRE COMME GUIDE"
        },
        {
            "timestamp_debut": 165,
            "timestamp_fin": 210,
            "texte_narration": "La chambre respire. Le jardin murmure. Le silence enveloppe. Ici, vous n'êtes pas un touriste qui consomme une expérience. Vous êtes un pèlerin qui retrouve son essence.",
            "image_query": "bedroom garden serene peaceful minimalist sanctuary",
            "texte_ecran": "UN SANCTUAIRE PERSONNEL"
        },
        {
            "timestamp_debut": 210,
            "timestamp_fin": 255,
            "texte_narration": "La salle commune invite à la lenteur. Quelques chaises. Un café. Des conversations qui susurrent plutôt que de crier. Z0 est un havre pour les âmes qui cherchent la profondeur.",
            "image_query": "minimalist lounge space seating area calm atmosphere",
            "texte_ecran": "ESPACE DE CONNEXION"
        },
        {
            "timestamp_debut": 255,
            "timestamp_fin": 300,
            "texte_narration": "L'architecture ne parle jamais fort. Elle murmure. Elle sugère. Elle invite. À Z0, chaque coin raconte une histoire de réduction, de raffinement, de respect envers celui qui y séjourne.",
            "image_query": "architectural detail minimalist design aesthetic",
            "texte_ecran": "L'ARCHITECTURE CHUCHOTE"
        },
        {
            "timestamp_debut": 300,
            "timestamp_fin": 345,
            "texte_narration": "Que vous soyez créatif en quête d'inspiration, professionnel burnout, ou simplement quelqu'un qui a oublié le pouvoir du silence : Z0 vous attend. Pas pour vous divertir. Pour vous transformer.",
            "image_query": "person contemplating nature peace meditation mindfulness",
            "texte_ecran": "POUR QUI ?"
        },
        {
            "timestamp_debut": 345,
            "timestamp_fin": 390,
            "texte_narration": "Chaque séjour à Z0 est une conversation entre vous et l'architecture. Un dialogue silencieux mais profond. Entre le bruit qu'on a quitté et la clarté qu'on retrouve.",
            "image_query": "luxury retreat peaceful accommodation minimalist style",
            "texte_ecran": "UNE CONVERSATION SILENCIEUSE"
        },
        {
            "timestamp_debut": 390,
            "timestamp_fin": 435,
            "texte_narration": "Le soir tombe. Les ombres dansent sur les murs. Vous êtes ici. Enfin. Loin de l'agitation. Dans l'intimité d'un espace pensé pour votre bien-être, votre créativité, votre paix.",
            "image_query": "sunset evening light architecture shadows aesthetic",
            "texte_ecran": "QUAND LA NUIT TOMBE"
        },
        {
            "timestamp_debut": 435,
            "timestamp_fin": 480,
            "texte_narration": "Z0 Guesthouse n'est pas un luxe de surface. C'est un luxe de profondeur. Où l'absence de bruit devient présence. Où le minimalisme devient liberté. Venez découvrir où l'architecture parle plus fort que les mots.",
            "image_query": "night architecture minimalist guesthouse entrance",
            "texte_ecran": "Z0 GUESTHOUSE — OÙ LE SILENCE PARLE"
        }
    ],
    "titre_miniature": "DESIGN MINIMALISTE"
}

# Affiche le script formaté
print("=" * 80)
print("SCRIPT GÉNÉRÉ : Z0 GUESTHOUSE")
print("=" * 80)
print(f"\n📌 TITRE\n{demo_script['titre_video']}\n")
print(f"📝 DESCRIPTION (résumé)\n{demo_script['description_youtube'][:200]}...\n")
print(f"🏷️ TAGS\n{', '.join(demo_script['tags'][:8])}...\n")
print(f"📊 SEGMENTS : {len(demo_script['segments'])} segments (8 minutes)")
print(f"⏱️ DURÉE TOTALE : {demo_script['segments'][-1]['timestamp_fin']} secondes\n")

print("STRUCTURE DES SEGMENTS :\n")
for i, seg in enumerate(demo_script['segments'], 1):
    duration = seg['timestamp_fin'] - seg['timestamp_debut']
    print(f"Segment {i} ({duration}s) | {seg['texte_ecran']}")
    print(f"  Narration : {seg['texte_narration'][:60]}...")
    print(f"  Image query : {seg['image_query']}\n")

# Sauvegarde en JSON
with open('z0_guesthouse_script.json', 'w', encoding='utf-8') as f:
    json.dump(demo_script, f, indent=2, ensure_ascii=False)

print("=" * 80)
print("✅ Script sauvegardé : z0_guesthouse_script.json")
print("=" * 80)
