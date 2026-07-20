<?php

/**
 * -------------------------------------------------------------------------
 * GLPI RAG plugin
 * -------------------------------------------------------------------------
 * Injecte un widget d'assistant RAG (recherche de tickets similaires déjà
 * résolus) sur le formulaire de création de ticket. Appelle l'API locale
 * FastAPI (Qdrant + Ollama + Langfuse) via fetch() JS.
 * -------------------------------------------------------------------------
 */

use Glpi\Plugin\Hooks;
use GlpiPlugin\Glpirag\ItemForm;

define('PLUGIN_GLPIRAG_VERSION', '0.1.0');

// Version GLPI minimale (incluse)
define('PLUGIN_GLPIRAG_MIN_GLPI', '10.0.0');
// Version GLPI maximale (exclue)
define('PLUGIN_GLPIRAG_MAX_GLPI', '10.0.99');

/**
 * Initialise les hooks du plugin.
 * REQUIS
 *
 * @return void
 */
function plugin_init_glpirag()
{
    global $PLUGIN_HOOKS;

    $PLUGIN_HOOKS[Hooks::CSRF_COMPLIANT]['glpirag'] = true;

    // Charge le JS/CSS du widget sur toutes les pages GLPI. ItemForm::postItemForm
    // se charge de ne rendre le widget que sur le formulaire de ticket ; le CSS/JS
    // chargés globalement ici sont légers et sans effet sur les autres pages.
    // GLPI 10.x sert les assets des plugins depuis le sous-dossier public/ —
    // chemin confirmé via test direct (plugins/glpirag/public/js/... répond
    // 200, plugins/glpirag/js/... répond 404).
    $PLUGIN_HOOKS[Hooks::ADD_JAVASCRIPT]['glpirag'] = 'public/js/glpirag.js';
    $PLUGIN_HOOKS[Hooks::ADD_CSS]['glpirag']        = 'public/css/glpirag.css';

    // Affiche le widget après les champs standards du formulaire (titre,
    // description...), avant la validation — c'est là que l'employé a déjà
    // formulé son problème et peut voir des solutions similaires.
    $PLUGIN_HOOKS[Hooks::POST_ITEM_FORM]['glpirag'] = [ItemForm::class, 'postItemForm'];
}

/**
 * Nom et version du plugin.
 * REQUIS
 *
 * @return array
 */
function plugin_version_glpirag()
{
    return [
        'name'         => 'GLPI RAG Assistant',
        'version'      => PLUGIN_GLPIRAG_VERSION,
        'author'       => 'Interne',
        'license'      => 'Interne',
        'homepage'     => '',
        'requirements' => [
            'glpi' => [
                'min' => PLUGIN_GLPIRAG_MIN_GLPI,
                'max' => PLUGIN_GLPIRAG_MAX_GLPI,
            ],
        ],
    ];
}

/**
 * Vérifie les prérequis avant installation.
 * OPTIONNEL mais recommandé.
 *
 * @return boolean
 */
function plugin_glpirag_check_prerequisites()
{
    return true;
}

/**
 * Vérifie la configuration du plugin.
 *
 * @param boolean $verbose Afficher un message en cas d'échec.
 *
 * @return boolean
 */
function plugin_glpirag_check_config($verbose = false)
{
    return true;
}
