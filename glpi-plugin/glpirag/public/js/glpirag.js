/**
 * Widget d'assistant RAG affiché sur le formulaire de création de ticket GLPI.
 *
 * Cherche le conteneur injecté par ItemForm::postItemForm() côté PHP
 * (#glpirag-widget-root) et y construit un petit formulaire : l'employé tape
 * sa question, on appelle l'API locale FastAPI (/api/chat), on affiche la
 * réponse + les tickets sources, avec un feedback 👍/👎 qui appelle
 * /api/feedback.
 */
(function () {
  "use strict";

  // URL de l'API RAG — à ajuster si l'API tourne ailleurs qu'en local.
  const GLPIRAG_API_BASE = "http://localhost:8000";

  function initWidget(root) {
    root.innerHTML = `
      <div class="glpirag-box">
        <div class="glpirag-header">
          <i class="ti ti-message-chatbot"></i>
          <span>Assistant GLPI — tickets similaires déjà résolus</span>
        </div>
        <div class="glpirag-input-row">
          <input type="text" class="glpirag-question" placeholder="Décrivez votre problème pour voir si une solution existe déjà..." />
          <button type="button" class="glpirag-ask-btn">Rechercher</button>
        </div>
        <div class="glpirag-status" hidden></div>
        <div class="glpirag-answer" hidden>
          <div class="glpirag-answer-text"></div>
          <div class="glpirag-feedback">
            <span>Cette réponse est-elle utile ?</span>
            <button type="button" class="glpirag-fb-btn" data-score="1">👍</button>
            <button type="button" class="glpirag-fb-btn" data-score="0">👎</button>
            <span class="glpirag-fb-thanks" hidden>Merci pour votre retour !</span>
          </div>
          <div class="glpirag-sources"></div>
        </div>
      </div>
    `;

    const questionInput = root.querySelector(".glpirag-question");
    const askBtn = root.querySelector(".glpirag-ask-btn");
    const statusEl = root.querySelector(".glpirag-status");
    const answerBox = root.querySelector(".glpirag-answer");
    const answerText = root.querySelector(".glpirag-answer-text");
    const sourcesEl = root.querySelector(".glpirag-sources");
    const feedbackBtns = root.querySelectorAll(".glpirag-fb-btn");
    const fbThanks = root.querySelector(".glpirag-fb-thanks");

    let currentGenerationId = null;

    async function askQuestion() {
      const question = questionInput.value.trim();
      if (question.length < 3) {
        return;
      }

      askBtn.disabled = true;
      statusEl.hidden = false;
      statusEl.textContent = "Recherche en cours (peut prendre jusqu'à 1-2 minutes)...";
      answerBox.hidden = true;
      fbThanks.hidden = true;
      feedbackBtns.forEach((btn) => (btn.disabled = false));

      try {
        const response = await fetch(`${GLPIRAG_API_BASE}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question: question,
            user_id: window.CFG_GLPI && window.CFG_GLPI.glpi_currentuser ? String(window.CFG_GLPI.glpi_currentuser) : null,
            session_id: "glpi-ticket-form-" + Date.now(),
          }),
        });

        if (!response.ok) {
          throw new Error("HTTP " + response.status);
        }

        const data = await response.json();
        currentGenerationId = data.generation_id;

        answerText.textContent = data.answer;

        sourcesEl.innerHTML = "";
        if (data.sources && data.sources.length > 0) {
          const title = document.createElement("div");
          title.className = "glpirag-sources-title";
          title.textContent = "Tickets sources :";
          sourcesEl.appendChild(title);

          const list = document.createElement("ul");
          data.sources.forEach((src) => {
            const li = document.createElement("li");
            li.textContent = `#${src.ticket_id} — ${src.titre} (pertinence ${src.score})`;
            list.appendChild(li);
          });
          sourcesEl.appendChild(list);
        }

        statusEl.hidden = true;
        answerBox.hidden = false;
      } catch (err) {
        statusEl.hidden = false;
        statusEl.textContent = "Le service d'assistant est indisponible pour le moment.";
        console.error("glpirag: erreur /api/chat", err);
      } finally {
        askBtn.disabled = false;
      }
    }

    async function sendFeedback(score) {
      if (!currentGenerationId) {
        return;
      }
      feedbackBtns.forEach((btn) => (btn.disabled = true));
      try {
        await fetch(`${GLPIRAG_API_BASE}/api/feedback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            generation_id: currentGenerationId,
            score: score,
          }),
        });
        fbThanks.hidden = false;
      } catch (err) {
        console.error("glpirag: erreur /api/feedback", err);
      }
    }

    askBtn.addEventListener("click", askQuestion);
    questionInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        askQuestion();
      }
    });
    feedbackBtns.forEach((btn) => {
      btn.addEventListener("click", () => sendFeedback(parseInt(btn.dataset.score, 10)));
    });
  }

  function boot() {
    const root = document.getElementById("glpirag-widget-root");
    if (root) {
      initWidget(root);
      return true;
    }
    return false;
  }

  // Le formulaire de ticket GLPI (et #glpirag-widget-root avec lui) est rendu
  // de façon asynchrone après le chargement initial du DOM — ni l'exécution
  // directe du script, ni DOMContentLoaded ne garantissent que le conteneur
  // existe déjà. On utilise un MutationObserver pour détecter son apparition
  // à coup sûr, quel que soit le moment où GLPI l'injecte, puis on se
  // déconnecte pour ne pas laisser tourner l'observateur inutilement.
  if (!boot()) {
    const observer = new MutationObserver(() => {
      if (boot()) {
        observer.disconnect();
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }
})();
