<!doctype html>
<title>Reranking — avant / après</title>

<style>
  :root {
    --bg: #f6f5f2;
    --surface: #ffffff;
    --ink: #1c1b18;
    --ink-soft: #5c5850;
    --ink-faint: #938f85;
    --line: #e2ddd3;
    --accent: #2f5d50;
    --accent-soft: #e4ece8;
    --bad: #a13a2f;
    --bad-soft: #f7e8e4;
    --good: #2f5d50;
    --good-soft: #e4ece8;
    --mono-bg: #efece4;
    --shadow: 0 1px 2px rgba(28, 27, 24, 0.04), 0 6px 20px rgba(28, 27, 24, 0.06);
  }

  :root[data-theme="dark"] {
    --bg: #161512;
    --surface: #1f1e1a;
    --ink: #ece9e2;
    --ink-soft: #b4afa4;
    --ink-faint: #7a7568;
    --line: #34322b;
    --accent: #6fb39d;
    --accent-soft: #223330;
    --bad: #e0796a;
    --bad-soft: #3a2420;
    --good: #6fb39d;
    --good-soft: #1e332d;
    --mono-bg: #201f1a;
    --shadow: 0 1px 2px rgba(0, 0, 0, 0.3), 0 6px 24px rgba(0, 0, 0, 0.3);
  }

  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg: #161512;
      --surface: #1f1e1a;
      --ink: #ece9e2;
      --ink-soft: #b4afa4;
      --ink-faint: #7a7568;
      --line: #34322b;
      --accent: #6fb39d;
      --accent-soft: #223330;
      --bad: #e0796a;
      --bad-soft: #3a2420;
      --good: #6fb39d;
      --good-soft: #1e332d;
      --mono-bg: #201f1a;
      --shadow: 0 1px 2px rgba(0, 0, 0, 0.3), 0 6px 24px rgba(0, 0, 0, 0.3);
    }
  }

  * { box-sizing: border-box; }

  html, body {
    margin: 0;
    background: var(--bg);
    color: var(--ink);
  }

  body {
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }

  .page {
    max-width: 940px;
    margin: 0 auto;
    padding: 52px 24px 96px;
  }

  header.top {
    margin-bottom: 40px;
  }

  .eyebrow {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--accent);
    margin: 0 0 10px;
  }

  h1 {
    font-size: 2.1rem;
    font-weight: 800;
    line-height: 1.12;
    margin: 0 0 14px;
    text-wrap: balance;
    letter-spacing: -0.015em;
  }

  .lede {
    font-size: 1.02rem;
    color: var(--ink-soft);
    max-width: 62ch;
    margin: 0;
  }

  .lede code {
    font-family: "SF Mono", "Cascadia Code", Consolas, monospace;
    font-size: 0.92em;
    background: var(--mono-bg);
    padding: 0.1em 0.4em;
    border-radius: 4px;
  }

  /* --- Query card --- */
  .query-card {
    margin-top: 28px;
    padding: 18px 22px;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 12px;
    box-shadow: var(--shadow);
    display: flex;
    align-items: baseline;
    gap: 12px;
    flex-wrap: wrap;
  }

  .query-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--ink-faint);
    flex: none;
  }

  .query-text {
    font-size: 1.08rem;
    font-weight: 600;
    color: var(--ink);
  }

  /* --- Pipeline strip --- */
  .pipeline {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    margin: 28px 0 40px;
    font-size: 0.86rem;
  }

  .pnode {
    padding: 9px 14px;
    border-radius: 8px;
    font-weight: 600;
    white-space: nowrap;
    border: 1px solid var(--line);
    background: var(--surface);
  }

  .pnode strong { color: var(--accent); }

  .parrow {
    color: var(--ink-faint);
    font-size: 1rem;
  }

  /* --- Compare grid --- */
  .compare {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 22px;
    margin-bottom: 44px;
  }

  @media (max-width: 720px) {
    .compare { grid-template-columns: 1fr; }
  }

  .col {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 14px;
    overflow: hidden;
    box-shadow: var(--shadow);
  }

  .col-head {
    padding: 16px 20px;
    border-bottom: 1px solid var(--line);
  }

  .col-head .k {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--ink-faint);
    margin: 0 0 4px;
  }

  .col-head .v {
    font-size: 1rem;
    font-weight: 700;
    margin: 0;
  }

  .col.before .v { color: var(--ink-soft); }
  .col.after .v { color: var(--accent); }

  .rank-list {
    display: flex;
    flex-direction: column;
  }

  .rank-row {
    display: grid;
    grid-template-columns: 28px 1fr auto;
    align-items: center;
    gap: 12px;
    padding: 13px 20px;
    border-bottom: 1px solid var(--line);
    font-size: 0.9rem;
  }

  .rank-row:last-child { border-bottom: none; }

  .rank-pos {
    font-weight: 700;
    color: var(--ink-faint);
    font-variant-numeric: tabular-nums;
  }

  .rank-title {
    color: var(--ink);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .rank-score {
    font-family: "SF Mono", "Cascadia Code", Consolas, monospace;
    font-size: 0.82rem;
    color: var(--ink-faint);
    font-variant-numeric: tabular-nums;
    flex: none;
  }

  .rank-row.dropped {
    background: var(--bad-soft);
  }

  .rank-row.dropped .rank-title {
    color: var(--bad);
    text-decoration: line-through;
    text-decoration-color: color-mix(in srgb, var(--bad) 50%, transparent);
  }

  .rank-row.dropped .rank-pos::after {
    content: "✕";
    margin-left: 6px;
    font-size: 0.75rem;
  }

  .rank-row.kept {
    background: var(--good-soft);
  }

  .rank-row.kept .rank-title {
    color: var(--good);
    font-weight: 600;
  }

  /* --- Verdict banner --- */
  .verdict {
    background: var(--accent-soft);
    border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent);
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 44px;
  }

  .verdict-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent);
    margin: 0 0 8px;
  }

  .verdict p {
    margin: 0;
    font-size: 0.98rem;
    color: var(--ink);
  }

  .verdict strong { color: var(--accent); }

  /* --- Section --- */
  section { margin-bottom: 44px; }

  h2.section-title {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--ink-faint);
    margin: 0 0 18px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--line);
  }

  /* --- Discarded ticket detail cards --- */
  .discard-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-left: 4px solid var(--bad);
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 14px;
    box-shadow: var(--shadow);
  }

  .discard-title {
    font-size: 1rem;
    font-weight: 700;
    margin: 0 0 6px;
    color: var(--ink);
  }

  .discard-meta {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    font-size: 0.8rem;
    color: var(--ink-faint);
    margin: 0 0 10px;
    font-variant-numeric: tabular-nums;
  }

  .discard-meta b { color: var(--ink-soft); font-weight: 600; }

  .discard-excerpt {
    font-size: 0.88rem;
    color: var(--ink-soft);
    background: var(--mono-bg);
    border-radius: 8px;
    padding: 10px 14px;
    font-style: italic;
  }

  .discard-why {
    margin-top: 10px;
    font-size: 0.88rem;
    color: var(--ink);
  }

  .discard-why b { color: var(--bad); }

  /* --- Explanation --- */
  .explain {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 22px;
  }

  @media (max-width: 720px) {
    .explain { grid-template-columns: 1fr; }
  }

  .explain-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 20px 22px;
    box-shadow: var(--shadow);
  }

  .explain-card h3 {
    font-size: 0.95rem;
    margin: 0 0 8px;
    font-weight: 700;
  }

  .explain-card p {
    font-size: 0.9rem;
    color: var(--ink-soft);
    margin: 0;
  }

  .explain-card code {
    font-family: "SF Mono", "Cascadia Code", Consolas, monospace;
    font-size: 0.85em;
    background: var(--mono-bg);
    padding: 0.1em 0.4em;
    border-radius: 4px;
    color: var(--ink);
  }

  footer.foot {
    margin-top: 56px;
    padding-top: 20px;
    border-top: 1px solid var(--line);
    font-size: 0.78rem;
    color: var(--ink-faint);
  }

  @media (max-width: 560px) {
    h1 { font-size: 1.6rem; }
    .page { padding: 36px 18px 72px; }
  }
</style>

<div class="page">

  <header class="top">
    <p class="eyebrow">Bot RAG GLPI — démo technique</p>
    <h1>Ce que le reranking change concrètement</h1>
    <p class="lede">
      Même question, même base de 46 tickets indexés. Comparaison du classement obtenu
      par simple similarité vectorielle (<code>bi-encoder</code>) contre le classement
      final après relecture par un <code>cross-encoder</code>.
    </p>
  </header>

  <div class="query-card">
    <span class="query-label">Question posée</span>
    <span class="query-text">« Comment résoudre un problème d'abonnement qui ne fonctionne pas ? »</span>
  </div>

  <div class="pipeline">
    <span class="pnode">Qdrant — scan large <strong>(25 candidats)</strong></span>
    <span class="parrow">→</span>
    <span class="pnode">Cross-encoder — relit chaque paire</span>
    <span class="parrow">→</span>
    <span class="pnode">Top 3 retenu <strong>→ Ollama</strong></span>
  </div>

  <div class="compare">
    <div class="col before">
      <div class="col-head">
        <p class="k">Étage 1 — retrieval seul</p>
        <p class="v">Top 5 par similarité cosinus</p>
      </div>
      <div class="rank-list">
        <div class="rank-row kept">
          <span class="rank-pos">1</span>
          <span class="rank-title">Abonnement qui ne fonctionne pas</span>
          <span class="rank-score">0.566</span>
        </div>
        <div class="rank-row dropped">
          <span class="rank-pos">2</span>
          <span class="rank-title">besoin d'un téléphone pour le bureau</span>
          <span class="rank-score">0.520</span>
        </div>
        <div class="rank-row kept">
          <span class="rank-pos">3</span>
          <span class="rank-title">Probleme paiement abo X2212579</span>
          <span class="rank-score">0.497</span>
        </div>
        <div class="rank-row kept">
          <span class="rank-pos">4</span>
          <span class="rank-title">Probleme paiement abo X2212579</span>
          <span class="rank-score">0.497</span>
        </div>
        <div class="rank-row dropped">
          <span class="rank-pos">5</span>
          <span class="rank-title">ABO 30€</span>
          <span class="rank-score">0.489</span>
        </div>
      </div>
    </div>

    <div class="col after">
      <div class="col-head">
        <p class="k">Étage 2 — après reranking</p>
        <p class="v">Top 3 par score cross-encoder</p>
      </div>
      <div class="rank-list">
        <div class="rank-row kept">
          <span class="rank-pos">1</span>
          <span class="rank-title">Abonnement qui ne fonctionne pas</span>
          <span class="rank-score">4.199</span>
        </div>
        <div class="rank-row kept">
          <span class="rank-pos">2</span>
          <span class="rank-title">Probleme paiement abo X2212579</span>
          <span class="rank-score">2.188</span>
        </div>
        <div class="rank-row kept">
          <span class="rank-pos">3</span>
          <span class="rank-title">Probleme paiement abo X2212579</span>
          <span class="rank-score">2.006</span>
        </div>
      </div>
    </div>
  </div>

  <div class="verdict">
    <p class="verdict-label">Ce qu'il faut retenir</p>
    <p>
      Le retrieval seul plaçait un ticket <strong>hors-sujet</strong> en 2ᵉ position
      (score 0.520, quasiment identique aux tickets pertinents) — le bi-encoder avait
      été trompé par une proximité de surface. Le cross-encoder l'a immédiatement
      écarté du classement final : les 3 tickets retenus parlent tous réellement
      d'abonnement.
    </p>
  </div>

  <section>
    <h2 class="section-title">Les tickets écartés par le reranking</h2>

    <div class="discard-card">
      <p class="discard-title">« besoin d'un téléphone pour le bureau »</p>
      <div class="discard-meta">
        <span><b>Rang retrieval :</b> 2ᵉ / 25</span>
        <span><b>Score cosinus :</b> 0.520</span>
        <span><b>Rang après reranking :</b> hors top 3</span>
      </div>
      <div class="discard-excerpt">
        « Le technicien va brancher le deuxième boîtier Gigaset sur le port 0/1 du routeur »
      </div>
      <p class="discard-why">
        <b>Pourquoi le retrieval l'a mal classé :</b> proximité lexicale/thématique
        vague avec du vocabulaire télécom/matériel, sans rapport avec un problème
        d'abonnement client.
      </p>
    </div>

    <div class="discard-card">
      <p class="discard-title">« ABO 30€ »</p>
      <div class="discard-meta">
        <span><b>Rang retrieval :</b> 5ᵉ / 25</span>
        <span><b>Score cosinus :</b> 0.489</span>
        <span><b>Rang après reranking :</b> hors top 3</span>
      </div>
      <div class="discard-excerpt">
        Titre court et générique (« ABO » = abréviation fréquente dans les tickets),
        sans description assez proche du problème réellement posé.
      </div>
      <p class="discard-why">
        <b>Pourquoi le retrieval l'a mal classé :</b> le mot « ABO » suffisait à
        rapprocher ce ticket vectoriellement, sans que le contenu réel du problème
        corresponde à la question posée.
      </p>
    </div>
  </section>

  <section>
    <h2 class="section-title">Pourquoi ça se produit</h2>
    <div class="explain">
      <div class="explain-card">
        <h3>Bi-encoder (retrieval)</h3>
        <p>
          Encode la question et chaque ticket <strong>séparément</strong>, puis compare
          les deux vecteurs par similarité cosinus. Rapide — c'est ce qui permet de
          scanner toute la base Qdrant en quelques millisecondes — mais approximatif :
          il ne voit jamais la question et le ticket <em>ensemble</em>.
        </p>
      </div>
      <div class="explain-card">
        <h3>Cross-encoder (reranking)</h3>
        <p>
          Relit la paire <code>(question, ticket)</code> <strong>ensemble</strong>, en une
          seule passe, et produit un score de pertinence réelle. Bien plus précis,
          mais trop coûteux pour scanner 137 000 tickets — d'où le filtrage en deux
          temps : large puis précis.
        </p>
      </div>
    </div>
  </section>

  <footer class="foot">
    Modèles : <code>all-MiniLM-L6-v2</code> (retrieval) ·
    <code>cross-encoder/ms-marco-MiniLM-L-6-v2</code> (reranking) — les deux tournent
    en local sur CPU, aucune donnée ne sort. Base de test : 46 tickets ingérés sur
    137 911 au total.
  </footer>

</div>
