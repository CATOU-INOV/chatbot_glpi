<!doctype html>
<title>Bot RAG GLPI — État des lieux</title>

<style>
  @font-face {
    font-family: "Fraunces-local";
    src: local("Georgia");
  }

  :root {
    --bg: #faf9f7;
    --bg-raised: #ffffff;
    --ink: #232019;
    --ink-soft: #5a5548;
    --ink-faint: #948e7d;
    --line: #e4e0d6;
    --accent: #a8562f;
    --accent-soft: #f2e4da;
    --ok: #4f7a4a;
    --ok-bg: #e9f0e6;
    --blocked: #b3402e;
    --blocked-bg: #fbe9e4;
    --pending: #9c7a1f;
    --pending-bg: #f6efdd;
    --code-bg: #f0ede4;
    --shadow: 0 1px 2px rgba(35, 32, 25, 0.06), 0 4px 16px rgba(35, 32, 25, 0.05);
  }

  :root[data-theme="dark"] {
    --bg: #1b1914;
    --bg-raised: #242019;
    --ink: #ede8dd;
    --ink-soft: #b8b1a0;
    --ink-faint: #7d7666;
    --line: #383327;
    --accent: #d98a5f;
    --accent-soft: #3a2a20;
    --ok: #8bb583;
    --ok-bg: #263124;
    --blocked: #e0796a;
    --blocked-bg: #3a2420;
    --pending: #d4b256;
    --pending-bg: #362e19;
    --code-bg: #211e17;
    --shadow: 0 1px 2px rgba(0, 0, 0, 0.3), 0 4px 20px rgba(0, 0, 0, 0.25);
  }

  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg: #1b1914;
      --bg-raised: #242019;
      --ink: #ede8dd;
      --ink-soft: #b8b1a0;
      --ink-faint: #7d7666;
      --line: #383327;
      --accent: #d98a5f;
      --accent-soft: #3a2a20;
      --ok: #8bb583;
      --ok-bg: #263124;
      --blocked: #e0796a;
      --blocked-bg: #3a2420;
      --pending: #d4b256;
      --pending-bg: #362e19;
      --code-bg: #211e17;
      --shadow: 0 1px 2px rgba(0, 0, 0, 0.3), 0 4px 20px rgba(0, 0, 0, 0.25);
    }
  }

  * { box-sizing: border-box; }

  html, body {
    margin: 0;
    padding: 0;
    background: var(--bg);
    color: var(--ink);
  }

  body {
    font-family: Georgia, "Times New Roman", serif;
    line-height: 1.55;
    -webkit-font-smoothing: antialiased;
  }

  .page {
    max-width: 780px;
    margin: 0 auto;
    padding: 56px 24px 96px;
  }

  header.top {
    margin-bottom: 40px;
  }

  .eyebrow {
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.11em;
    text-transform: uppercase;
    color: var(--accent);
    margin: 0 0 10px;
  }

  h1 {
    font-family: Georgia, "Times New Roman", serif;
    font-size: 2.15rem;
    font-weight: 700;
    line-height: 1.15;
    margin: 0 0 12px;
    text-wrap: balance;
    letter-spacing: -0.01em;
  }

  .subhead {
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
    color: var(--ink-soft);
    font-size: 0.98rem;
    margin: 0;
    max-width: 60ch;
  }

  .meta-row {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid var(--line);
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 0.82rem;
    color: var(--ink-faint);
  }

  .meta-row strong {
    color: var(--ink-soft);
    font-weight: 600;
  }

  /* --- Blocking banner --- */
  .blocker {
    background: var(--blocked-bg);
    border: 1px solid color-mix(in srgb, var(--blocked) 35%, transparent);
    border-radius: 10px;
    padding: 20px 22px;
    margin: 0 0 40px;
    box-shadow: var(--shadow);
  }

  .blocker-label {
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--blocked);
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0 0 10px;
  }

  .blocker-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--blocked);
    flex: none;
  }

  .blocker h2 {
    font-size: 1.05rem;
    margin: 0 0 8px;
    font-weight: 700;
  }

  .blocker p {
    margin: 0 0 8px;
    color: var(--ink);
    font-size: 0.96rem;
  }

  .blocker p:last-child { margin-bottom: 0; }

  /* --- Section structure --- */
  section {
    margin-bottom: 44px;
  }

  h2.section-title {
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--ink-faint);
    margin: 0 0 18px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--line);
  }

  /* --- Timeline / steps --- */
  .steps {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .step {
    display: grid;
    grid-template-columns: 28px 1fr;
    gap: 14px;
    padding: 14px 0;
    border-bottom: 1px solid var(--line);
  }

  .step:last-child { border-bottom: none; }

  .step-icon {
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding-top: 2px;
  }

  .step-icon svg { width: 18px; height: 18px; }

  .step.done .step-icon { color: var(--ok); }
  .step.blocked .step-icon { color: var(--blocked); }
  .step.pending .step-icon { color: var(--pending); }

  .step-title {
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
    font-weight: 600;
    font-size: 0.96rem;
    color: var(--ink);
    margin: 0 0 4px;
  }

  .step-body {
    font-size: 0.93rem;
    color: var(--ink-soft);
    margin: 0;
  }

  .step-body code {
    font-family: "SF Mono", "Cascadia Code", Consolas, monospace;
    font-size: 0.85em;
    background: var(--code-bg);
    padding: 0.1em 0.4em;
    border-radius: 4px;
    color: var(--ink);
  }

  .tag {
    display: inline-block;
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    padding: 2px 8px;
    border-radius: 20px;
    margin-left: 8px;
    vertical-align: 1px;
  }

  .tag.ok { background: var(--ok-bg); color: var(--ok); }
  .tag.blocked { background: var(--blocked-bg); color: var(--blocked); }
  .tag.pending { background: var(--pending-bg); color: var(--pending); }

  /* --- Config table --- */
  .config-table {
    width: 100%;
    border-collapse: collapse;
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 0.88rem;
  }

  .config-table th {
    text-align: left;
    font-weight: 600;
    color: var(--ink-faint);
    font-size: 0.72rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 0 12px 8px 0;
    border-bottom: 1px solid var(--line);
  }

  .config-table td {
    padding: 9px 12px 9px 0;
    border-bottom: 1px solid var(--line);
    vertical-align: top;
    color: var(--ink);
  }

  .config-table tr:last-child td { border-bottom: none; }

  .config-table code {
    font-family: "SF Mono", "Cascadia Code", Consolas, monospace;
    font-size: 0.85em;
    background: var(--code-bg);
    padding: 0.15em 0.45em;
    border-radius: 4px;
  }

  .table-wrap {
    overflow-x: auto;
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 4px 16px;
    background: var(--bg-raised);
  }

  /* --- Next actions --- */
  .actions {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .action {
    display: grid;
    grid-template-columns: 26px 1fr;
    gap: 12px;
    padding: 14px 16px;
    background: var(--bg-raised);
    border: 1px solid var(--line);
    border-radius: 10px;
    box-shadow: var(--shadow);
  }

  .action-num {
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
    font-weight: 700;
    font-size: 0.85rem;
    color: var(--accent);
  }

  .action-title {
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
    font-weight: 600;
    font-size: 0.94rem;
    margin: 0 0 4px;
  }

  .action-body {
    font-size: 0.9rem;
    color: var(--ink-soft);
    margin: 0;
  }

  .action-body code {
    font-family: "SF Mono", "Cascadia Code", Consolas, monospace;
    font-size: 0.85em;
    background: var(--code-bg);
    padding: 0.15em 0.4em;
    border-radius: 4px;
    color: var(--ink);
  }

  /* --- Pipeline diagram --- */
  .pipeline {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 0.82rem;
    padding: 18px;
    background: var(--bg-raised);
    border: 1px solid var(--line);
    border-radius: 10px;
    margin-top: 16px;
  }

  .pnode {
    padding: 8px 12px;
    border-radius: 7px;
    font-weight: 600;
    white-space: nowrap;
  }

  .pnode.ok { background: var(--ok-bg); color: var(--ok); }
  .pnode.blocked { background: var(--blocked-bg); color: var(--blocked); }
  .pnode.neutral { background: var(--code-bg); color: var(--ink-soft); }

  .parrow {
    color: var(--ink-faint);
    font-size: 0.95rem;
  }

  footer.foot {
    margin-top: 56px;
    padding-top: 20px;
    border-top: 1px solid var(--line);
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 0.78rem;
    color: var(--ink-faint);
  }

  @media (max-width: 560px) {
    h1 { font-size: 1.7rem; }
    .page { padding: 36px 18px 72px; }
  }
</style>

<div class="page">

  <header class="top">
    <p class="eyebrow">Projet interne</p>
    <h1>Bot RAG GLPI — État des lieux</h1>
    <p class="subhead">
      Assistant pour aider les employés à résoudre leurs tickets GLPI, à partir de tickets
      similaires déjà résolus. Stack 100&nbsp;% locale : Snowflake → Qdrant → Ollama.
    </p>
    <div class="meta-row">
      <span><strong>Dernière session :</strong> 3 juillet 2026</span>
      <span><strong>Repo :</strong> chatbot_GLPI</span>
      <span><strong>Statut global :</strong> bloqué côté données</span>
    </div>
  </header>

  <div class="blocker">
    <p class="blocker-label"><span class="blocker-dot"></span>Point de blocage actuel</p>
    <h2>Encodage des accents corrompu dans le pipeline Sling (MariaDB → Snowflake)</h2>
    <p>
      Les caractères accentués (é, è, à…) sont mal transférés entre la base GLPI (MariaDB) et
      Snowflake — un <code>é</code> devient <code>Ã©</code> une fois arrivé dans Snowflake.
    </p>
    <p>
      <strong>Diagnostic confirmé :</strong> les octets stockés dans MariaDB sont corrects
      (UTF-8 valide, vérifié via <code>HEX()</code>). Le problème vient du transfert Sling — la
      connexion source <code>GLPI</code> dans la config Sling ne déclare aucun charset explicite.
    </p>
    <p>
      <strong>Correctif identifié, pas encore appliqué :</strong> ajouter
      <code>params: { charset: utf8mb4 }</code> à la connexion <code>GLPI</code> dans Sling, puis
      relancer le job de réplication (<code>mode: full-refresh</code>) pour recharger les données
      proprement.
    </p>
  </div>

  <section>
    <h2 class="section-title">Ce qui a été fait — dans l'ordre</h2>
    <div class="steps">

      <div class="step done">
        <div class="step-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
        </div>
        <div>
          <p class="step-title">Structure du projet créée<span class="tag ok">Fait</span></p>
          <p class="step-body">
            <code>ingest_glpi.py</code>, <code>test_query.py</code>, <code>requirements.txt</code>,
            <code>.env</code>, <code>.gitignore</code>.
          </p>
        </div>
      </div>

      <div class="step done">
        <div class="step-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
        </div>
        <div>
          <p class="step-title">Décision : tout en local, pas d'API Claude<span class="tag ok">Fait</span></p>
          <p class="step-body">
            Le projet cible un modèle Ollama auto-hébergé (aucune donnée ne doit sortir).
            <code>test_query.py</code> appelle Ollama en HTTP local, plus de dépendance Anthropic.
          </p>
        </div>
      </div>

      <div class="step done">
        <div class="step-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
        </div>
        <div>
          <p class="step-title">Ollama installé + modèle téléchargé<span class="tag ok">Fait</span></p>
          <p class="step-body">
            <code>qwen2.5:3b</code> (1.9&nbsp;Go) — choisi pour tourner correctement sur CPU
            (poste sans GPU dédié, Intel Core Ultra 7 265U / 31&nbsp;Go RAM). Testé, répond
            en quelques secondes.
          </p>
        </div>
      </div>

      <div class="step done">
        <div class="step-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
        </div>
        <div>
          <p class="step-title">Qdrant lancé via Docker<span class="tag ok">Fait</span></p>
          <p class="step-body">Collection <code>glpi_tickets</code>, vecteurs 384 dim (cosine).</p>
        </div>
      </div>

      <div class="step done">
        <div class="step-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
        </div>
        <div>
          <p class="step-title">Authentification Snowflake résolue<span class="tag ok">Fait</span></p>
          <p class="step-body">
            Compte perso bloqué par MFA (Duo) → bascule sur un compte de service
            (<code>BI_USER_SVC</code>, rôle <code>BI_USER_ANALYSTS</code>) en key-pair auth
            (clé <code>.p8</code>). <code>ingest_glpi.py</code> gère les deux modes
            (password ou clé privée).
          </p>
        </div>
      </div>

      <div class="step done">
        <div class="step-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
        </div>
        <div>
          <p class="step-title">Droits cross-schema résolus par clonage<span class="tag ok">Fait</span></p>
          <p class="step-body">
            La vue <code>V_RAG_TICKETS</code> dépendait de tables dans un autre
            schéma source alimenté par Sling, inaccessibles au compte de service. Solution :
            <code>CREATE TABLE ... CLONE</code> des deux tables sources
            (<code>F_GLPI_TICKETS</code>, <code>F_GLPI_ITILSOLUTIONS</code>) dans
            <code>DEVELOPMENT.TCAT</code>, vue recréée dessus. 137&nbsp;911 lignes confirmées,
            <code>GRANT SELECT</code> donné au rôle <code>BI_USER_ANALYSTS</code>.
          </p>
        </div>
      </div>

      <div class="step done">
        <div class="step-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
        </div>
        <div>
          <p class="step-title">Bug ID Qdrant corrigé<span class="tag ok">Fait</span></p>
          <p class="step-body">
            Qdrant refuse les ID de type <code>"640988_1"</code> (chaîne libre) — il faut un
            entier ou un UUID. Corrigé : ID = <code>uuid5("{ticket_id}_{solution_rank}")</code>,
            la clé lisible reste dans le payload (<code>composite_key</code>).
          </p>
        </div>
      </div>

      <div class="step done">
        <div class="step-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
        </div>
        <div>
          <p class="step-title">Test d'ingestion sur 50 lignes<span class="tag ok">Fait</span></p>
          <p class="step-body">
            46 tickets ingérés, 4 filtrés (solution &lt; 30 caractères) — comportement attendu.
            Ajout d'une variable <code>INGEST_LIMIT</code> pour tester sur un échantillon sans
            toucher au script.
          </p>
        </div>
      </div>

      <div class="step blocked">
        <div class="step-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h.01"/></svg>
        </div>
        <div>
          <p class="step-title">Bug nettoyage HTML — corrigé côté script<span class="tag ok">Fait</span></p>
          <p class="step-body">
            Le HTML est doublement encodé (entités <code>&amp;#60;</code> qui, une fois décodées,
            révèlent de vraies balises). <code>BeautifulSoup</code> ne les nettoyait qu'en un
            seul passage. Correctif appliqué dans <code>clean_html()</code> : décodage puis
            deuxième passage de parsing.
          </p>
        </div>
      </div>

      <div class="step blocked">
        <div class="step-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/></svg>
        </div>
        <div>
          <p class="step-title">Encodage des accents — cause identifiée, correctif en attente<span class="tag blocked">Bloquant</span></p>
          <p class="step-body">
            Voir le bandeau de blocage en haut de page. Diagnostic terminé, reste à appliquer le
            changement de config Sling et relancer le chargement.
          </p>
        </div>
      </div>

    </div>
  </section>

  <section>
    <h2 class="section-title">Où on en est dans le pipeline</h2>
    <div class="pipeline">
      <span class="pnode ok">MariaDB (GLPI)</span>
      <span class="parrow">→</span>
      <span class="pnode blocked">Sling (charset à corriger)</span>
      <span class="parrow">→</span>
      <span class="pnode ok">Snowflake (clones TCAT)</span>
      <span class="parrow">→</span>
      <span class="pnode neutral">ingest_glpi.py</span>
      <span class="parrow">→</span>
      <span class="pnode neutral">Qdrant</span>
      <span class="parrow">→</span>
      <span class="pnode neutral">Ollama / qwen2.5:3b</span>
    </div>
  </section>

  <section>
    <h2 class="section-title">Configuration actuelle (.env)</h2>
    <div class="table-wrap">
      <table class="config-table">
        <thead>
          <tr><th>Variable</th><th>Valeur / statut</th></tr>
        </thead>
        <tbody>
          <tr><td><code>SNOWFLAKE_USER</code></td><td><code>BI_USER_SVC</code></td></tr>
          <tr><td><code>SNOWFLAKE_ACCOUNT</code></td><td><code>&lt;masqué&gt;</code></td></tr>
          <tr><td><code>SNOWFLAKE_DATABASE</code> / <code>SCHEMA</code></td><td><code>DEVELOPMENT</code> / <code>TCAT</code></td></tr>
          <tr><td><code>SNOWFLAKE_PRIVATE_KEY_PATH</code></td><td>clé <code>.p8</code> non chiffrée, dans <code>keys/</code> (gitignored)</td></tr>
          <tr><td><code>QDRANT_HOST</code> / <code>PORT</code></td><td><code>localhost</code> / <code>6333</code> (Docker)</td></tr>
          <tr><td><code>QDRANT_COLLECTION</code></td><td><code>glpi_tickets</code></td></tr>
          <tr><td><code>OLLAMA_HOST</code></td><td><code>http://localhost:11434</code></td></tr>
          <tr><td><code>OLLAMA_MODEL</code></td><td><code>qwen2.5:3b</code></td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section>
    <h2 class="section-title">Pour reprendre la semaine prochaine</h2>
    <div class="actions">

      <div class="action">
        <span class="action-num">1</span>
        <div>
          <p class="action-title">Corriger la config Sling</p>
          <p class="action-body">
            Dans la connexion <code>GLPI</code> (fichier de connexions Sling), ajouter :
            <code>params: { charset: utf8mb4 }</code>. Vérifier avec l'admin si un paramètre
            <code>useUnicode: true</code> est aussi nécessaire selon le driver.
          </p>
        </div>
      </div>

      <div class="action">
        <span class="action-num">2</span>
        <div>
          <p class="action-title">Relancer la réplication Sling</p>
          <p class="action-body">
            <code>mode: full-refresh</code> déjà configuré — un simple relancement du job recharge
            tout depuis MariaDB avec le bon charset.
          </p>
        </div>
      </div>

      <div class="action">
        <span class="action-num">3</span>
        <div>
          <p class="action-title">Re-cloner les tables dans TCAT</p>
          <p class="action-body">
            Refaire <code>CREATE OR REPLACE TABLE ... CLONE</code> pour
            <code>F_GLPI_TICKETS</code> et <code>F_GLPI_ITILSOLUTIONS</code> depuis les tables
            source fraîchement corrigées, ou pointer directement <code>V_RAG_TICKETS</code> vers
            les tables source si le problème de droits est réglé entretemps.
          </p>
        </div>
      </div>

      <div class="action">
        <span class="action-num">4</span>
        <div>
          <p class="action-title">Vérifier un échantillon avant l'ingestion complète</p>
          <p class="action-body">
            <code>INGEST_LIMIT=50 python ingest_glpi.py</code>, puis inspecter un point Qdrant
            (via l'API scroll) pour confirmer que les accents sont propres et le HTML bien
            nettoyé.
          </p>
        </div>
      </div>

      <div class="action">
        <span class="action-num">5</span>
        <div>
          <p class="action-title">Lancer l'ingestion complète</p>
          <p class="action-body">
            <code>python ingest_glpi.py</code> sans <code>INGEST_LIMIT</code> — les 137&nbsp;911
            lignes. Prévoir un peu de temps (embedding CPU).
          </p>
        </div>
      </div>

      <div class="action">
        <span class="action-num">6</span>
        <div>
          <p class="action-title">Tester les questions réelles</p>
          <p class="action-body">
            <code>python test_query.py</code> — évaluer la pertinence des réponses de
            <code>qwen2.5:3b</code> sur des cas concrets, ajuster le prompt système si besoin.
          </p>
        </div>
      </div>

    </div>
  </section>

  <footer class="foot">
    Ce fichier est un point de sauvegarde de contexte, pas une doc finale — à mettre à jour au
    fil de l'eau ou à supprimer une fois le projet stabilisé.
  </footer>

</div>
