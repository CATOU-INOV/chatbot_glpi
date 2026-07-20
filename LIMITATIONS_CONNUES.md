# Limitations connues — bot RAG GLPI

Notes honnêtes sur ce qui ne fonctionne pas encore parfaitement, pour éviter les mauvaises surprises en usage réel.

## Anonymisation des noms propres dans les réponses (qualité, pas sécurité)

**Constat** : le LLM (`qwen2.5:3b`) mentionne parfois, dans sa réponse, un nom de
client ou de technicien présent dans le texte des tickets sources — par
exemple "contactez Mme DUPONT MARIE" alors que ce nom vient du problème
*archivé* d'un ticket précédent, pas d'un contact réel à joindre pour la
question posée aujourd'hui.

**Ce qui est déjà couvert de façon fiable** (`ingest_glpi.py`, par regex,
donc garanti à 100% côté code, indépendant du LLM) :
- Emails (`EMAIL_RE`)
- Mots de passe / identifiants (`PASSWORD_RE`)
- Références de tickets (`TICKET_REF_RE`)
- Signatures de techniciens en fin de solution ("Cordialement, Prénom" →
  `redact_signatures()`)

**Ce qui n'est pas couvert de façon fiable** : les noms de clients mentionnés
dans le texte libre du problème (ex: "La cliente Mme DURAND SOPHIE a...").

**Pistes essayées et écartées** :
- *spaCy + NER français* (`fr_core_news_sm` et `_md`) — testé sur des
  échantillons réels, taux d'erreur trop élevé pour ce type de texte
  (majuscules de formulaire GLPI, mojibake résiduel, jargon métier). Rate des
  cas évidents ("MME DUPONT MARIE" non détecté), et produit des faux positifs
  (un participe passé ou un numéro d'abonnement classés comme "personne").
  Nécessiterait un fine-tuning pour être fiable — hors scope de cette session.
- *Prompt engineering seul* — une instruction system stricte ("ne cite jamais
  de nom") réduit la fréquence du problème mais ne l'élimine pas de façon
  fiable, et peut dégrader la cohérence de la réponse (le modèle invente du
  contenu hors-contexte pour compenser la contrainte, ex: jargon inventé,
  brouillon d'email halluciné).

**Pourquoi ce n'est pas bloquant pour l'instant** : le risque réel (fuite
d'identifiants, de mots de passe, de contacts internes usurpés) est déjà
couvert côté code. Un nom de client déjà visible dans GLPI par les employés
support qui réapparaît mal à propos dans une réponse est une maladresse de
qualité, pas une fuite de donnée nouvelle.

**Pistes pour plus tard, si ça devient prioritaire** :
- Modèle Ollama plus gros (ex: `qwen2.5:7b`) — probablement plus fiable sur
  ce type d'instruction, au prix d'une latence plus élevée sur CPU.
- Anonymisation ciblée des noms de clients à l'ingestion, avec un pattern
  contextuel spécifique (ex: après "Mme"/"M."/"la cliente"/"le client"),
  similaire à `redact_signatures()` — plus fiable qu'un NER générique car
  ancré sur le vocabulaire réel des tickets GLPI, à valider sur un large
  échantillon avant de généraliser.

---

## Latence du reranking

~1min30 par requête sur ce poste (CPU, sans GPU dédié) — retrieval hybride +
reranking cross-encoder + génération Ollama.
