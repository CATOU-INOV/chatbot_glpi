<?php

/**
 * -------------------------------------------------------------------------
 * GLPI RAG plugin — install/uninstall hooks
 * -------------------------------------------------------------------------
 * Ce plugin n'a pas de table ni de droit dédié : il ne fait qu'injecter un
 * widget JS/HTML sur le formulaire de ticket. install()/uninstall() sont
 * requis par GLPI mais n'ont donc rien à faire ici.
 * -------------------------------------------------------------------------
 */

function plugin_glpirag_install()
{
    return true;
}

function plugin_glpirag_uninstall()
{
    return true;
}
