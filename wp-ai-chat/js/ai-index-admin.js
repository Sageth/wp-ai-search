document.addEventListener('DOMContentLoaded', () => {
  const button = document.getElementById('ai-index-trigger');
  const log = document.getElementById('ai-index-log');

  button.addEventListener('click', async () => {
    button.disabled = true;
    button.textContent = "Reindexing...";
    log.textContent = "⏳ Starting indexing...\n";

    try {
      const response = await fetch(AIIndexAjax.ajax_url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          action: 'ai_index_trigger',
          nonce: AIIndexAjax.nonce
        })
      });

      const data = await response.json();
      if (data.success) {
        const output = JSON.parse(data.data.response);
        log.textContent += "✅ Indexing complete.\n\n";
        log.textContent += output.stdout || "(no stdout)";
        if (output.stderr) {
          log.textContent += "\\n⚠️ Errors:\\n" + output.stderr;
        }
      } else {
        log.textContent += "❌ Error: " + data.data.error;
      }
    } catch (err) {
      log.textContent += "❌ Request failed: " + err.message;
    }

    button.disabled = false;
    button.textContent = "Reindex Now";
  });
});
