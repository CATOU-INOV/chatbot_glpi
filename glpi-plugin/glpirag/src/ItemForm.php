<?php

namespace GlpiPlugin\Glpirag;

use Ticket;

/**
 * Injecte le widget d'assistant RAG sur le formulaire de création de ticket.
 *
 * @see http://glpi-developer-documentation.rtfd.io/en/master/plugins/hooks.html#items-display-related
 */
class ItemForm
{
    /**
     * Affiche le widget après les champs standards du formulaire d'un item.
     * Ne s'affiche que sur le formulaire Ticket — les autres types d'objets
     * (Computer, Profile, etc.) déclenchent aussi ce hook mais ne nous
     * intéressent pas ici.
     *
     * @param array $params Tableau avec les clés "item" et "options".
     *
     * @return void
     */
    public static function postItemForm($params)
    {
        $item = $params['item'];

        if ($item::getType() !== Ticket::class) {
            return;
        }

        // Sur un ticket déjà existant (édition), pas de sens à proposer des
        // "tickets similaires" — le widget ne s'affiche qu'à la création.
        if (!$item->isNewItem()) {
            return;
        }

        echo '<div id="glpirag-widget-root" class="glpirag-widget"></div>';
    }
}
