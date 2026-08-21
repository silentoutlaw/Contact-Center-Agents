/* Page glue shared by the training and agent pages. Reads config from the
 * #call container's data-* attributes and drives a VoiceSession. */
(function () {
  "use strict";

  async function postJSON(url, body) {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    return r.json();
  }

  function el(id) { return document.getElementById(id); }

  function line(role, text) {
    const div = document.createElement("div");
    div.className = "msg " + role;
    div.textContent = (role === "user" ? "You" : "AI") + ": " + text;
    return div;
  }

  document.addEventListener("DOMContentLoaded", function () {
    const root = el("call");
    if (!root) return;
    const sessionUrl = root.dataset.sessionUrl;
    const gradeUrl = root.dataset.gradeUrl || "";

    const startBtn = el("start"), endBtn = el("end"), gradeBtn = el("grade");
    const statusEl = el("status"), transcriptEl = el("transcript");
    const difficultyEl = el("difficulty"), customerEl = el("customer");
    const resultsEl = el("results");

    let vs = null;
    let lastTranscript = "";

    startBtn.onclick = async function () {
      startBtn.disabled = true;
      statusEl.textContent = "Connecting…";
      transcriptEl.innerHTML = "";
      if (resultsEl) resultsEl.innerHTML = "";
      const difficulty = difficultyEl ? difficultyEl.value : "easy";
      const cfg = await postJSON(sessionUrl, { difficulty });
      if (cfg.error) { statusEl.textContent = cfg.error; startBtn.disabled = false; return; }
      if (customerEl && cfg.customer) {
        customerEl.style.display = "";
        customerEl.textContent =
          "Caller: " + cfg.customer.name + " · Acct " + cfg.customer.account +
          " · " + cfg.customer.address;
      }
      vs = new VoiceSession(cfg, {
        onStatus: function (t) { statusEl.textContent = t; },
        onTranscript: function (role, text) {
          transcriptEl.appendChild(line(role, text));
          transcriptEl.scrollTop = transcriptEl.scrollHeight;
        },
      });
      try {
        await vs.start();
        endBtn.disabled = false;
      } catch (e) {
        statusEl.textContent = "Mic/connection error: " + e.message;
        startBtn.disabled = false;
      }
    };

    endBtn.onclick = function () {
      if (vs) { lastTranscript = vs.transcriptText(); vs.stop(); }
      startBtn.disabled = false;
      endBtn.disabled = true;
      if (gradeBtn && lastTranscript) gradeBtn.disabled = false;
    };

    if (gradeBtn) {
      gradeBtn.onclick = async function () {
        gradeBtn.disabled = true;
        resultsEl.textContent = "Grading…";
        const res = await postJSON(gradeUrl, { transcript: lastTranscript });
        if (res.error) { resultsEl.textContent = res.error; return; }
        resultsEl.innerHTML =
          "<h3>Score: " + res.score + "/100</h3>" +
          "<p>" + (res.overall_assessment || "") + "</p>" +
          "<pre>" + JSON.stringify(res, null, 2) + "</pre>";
      };
    }
  });
})();
