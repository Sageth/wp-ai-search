document.addEventListener('DOMContentLoaded', () => {
  const API_URL = "https://example.com/ai/ask";
  const input = document.getElementById("ai-query");
  const button = document.getElementById("ai-submit");
  const output = document.getElementById("ai-chat-messages");
  const typing = document.getElementById("ai-typing");

  async function sendQuery() {
    const query = input.value.trim();
    if (!query) return;

    const userMsg = document.createElement("div");
    userMsg.className = "chat-message user";
    userMsg.textContent = query;
    output.appendChild(userMsg);

    input.value = "";
    input.disabled = true;
    button.disabled = true;
    typing.style.display = "block";

    let rawHTML = "";
    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query })
      });

      const data = await response.json();
      rawHTML = (data.answer || "Sorry, no response.")
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
        .replace(/\n\n/g, '<br><br>')  // double line breaks for paragraph breaks
        .replace(/\n/g, '<br>');       // single line breaks
    } catch (err) {
      rawHTML = "⚠️ Error contacting AI.";
    }

    typing.style.display = "none";

    const tempEl = document.createElement("div");
    tempEl.innerHTML = rawHTML;
    const plainText = tempEl.textContent || tempEl.innerText || "";

    const aiMsg = document.createElement("div");
    aiMsg.className = "chat-message ai";
    output.appendChild(aiMsg);

    let i = 0;
    const speed = 30;

    function typeChar() {
      if (i < plainText.length) {
        aiMsg.textContent += plainText[i];
        i++;
        setTimeout(typeChar, speed);
        output.scrollTop = output.scrollHeight;
      } else {
        // After typing finishes, swap in full HTML with links
        aiMsg.innerHTML = rawHTML;
        input.disabled = false;
        button.disabled = false;
        input.focus();
      }
    }

    typeChar();
  }

  button.addEventListener("click", sendQuery);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendQuery();
  });
});
