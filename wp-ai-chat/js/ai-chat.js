document.addEventListener('DOMContentLoaded', () => {
  const API_URL = "https://your-python-api.com/ask"; // Make sure to leave the URI as /ask
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

    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query })
    });

    const data = await response.json();
    typing.style.display = "none";

    const aiMsg = document.createElement("div");
    aiMsg.className = "chat-message ai";
    output.appendChild(aiMsg);

    const text = data.answer || "Sorry, no response.";
    let i = 0;
    const speed = 30; // ms per character

    function typeChar() {
      if (i < text.length) {
        aiMsg.innerHTML += text[i] === "\n" ? "<br>" : text[i];
        i++;
        setTimeout(typeChar, speed);
        output.scrollTop = output.scrollHeight;
      } else {
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
