-- ============================================================================
-- UDF Python : fix_mojibake
-- ============================================================================
-- Porte en SQL la logique de app/ingest_glpi.py::fix_mojibake() (ligne 110) :
-- répare le mojibake classique "UTF-8 encodé, relu comme Latin-1" produit par
-- le transfert Sling MariaDB -> Snowflake (charset=utf8mb4 manquant côté
-- connexion source), ex. "Ã©" -> "é".
--
-- Le correctif définitif est côté connexion Sling (params.charset=utf8mb4).
-- Cette UDF est un filet de sécurité déporté dans Snowflake : si le texte est
-- déjà de l'UTF-8 propre, le round-trip lève une exception et la valeur
-- d'origine est renvoyée inchangée (no-op).
--
-- Adapter le nom de schéma cible avant exécution (ici DEVELOPMENT.TCAT).
-- ============================================================================

CREATE OR REPLACE FUNCTION DEVELOPMENT.TCAT.FIX_MOJIBAKE(input_text STRING)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
HANDLER = 'fix_mojibake'
AS
$$
def fix_mojibake(text):
    if not text:
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
$$;

-- ----------------------------------------------------------------------------
-- Vérification rapide
-- ----------------------------------------------------------------------------
-- SELECT DEVELOPMENT.TCAT.FIX_MOJIBAKE('SystÃ¨me de tickets dÃ©fectueux');
-- -> 'Système de tickets défectueux'
--
-- SELECT DEVELOPMENT.TCAT.FIX_MOJIBAKE('Texte déjà propre');
-- -> 'Texte déjà propre'  (no-op, round-trip échoue silencieusement)
