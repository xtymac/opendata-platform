(function () {
  const mountPoint = document.getElementById('ckan-assistant-root');
  if (!mountPoint || window.CKAN_ASSISTANT_INITIALISED) {
    return;
  }

  window.CKAN_ASSISTANT_INITIALISED = true;

  const endpoint = mountPoint.dataset.assistantEndpoint || '/assistant/chat';

  const style = document.createElement('style');
  style.textContent = `
    #ckan-assistant-toggle {
      position: fixed;
      right: 24px;
      bottom: 24px;
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: #1f6feb;
      color: #fff;
      border: none;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
      cursor: pointer;
      font-size: 28px;
      z-index: 1050;
    }

    #ckan-assistant-panel {
      position: fixed;
      right: 24px;
      bottom: 96px;
      width: 360px;
      max-width: calc(100vw - 48px);
      height: 480px;
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 16px 40px rgba(31, 51, 73, 0.32);
      display: none;
      flex-direction: column;
      overflow: hidden;
      z-index: 1050;
    }

    #ckan-assistant-panel.open {
      display: flex;
    }

    #ckan-assistant-header {
      background: #1f6feb;
      color: #fff;
      padding: 12px 16px;
      font-weight: 600;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    #ckan-assistant-messages {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      background: #f7f9fc;
    }

    #ckan-assistant-input {
      display: flex;
      gap: 8px;
      padding: 12px;
      border-top: 1px solid #d0d7de;
      background: #fff;
    }

    #ckan-assistant-input textarea {
      flex: 1;
      resize: none;
      border-radius: 8px;
      border: 1px solid #d0d7de;
      padding: 8px;
      min-height: 60px;
      font-size: 14px;
    }

    #ckan-assistant-input button {
      background: #1f6feb;
      border: none;
      color: #fff;
      padding: 0 16px;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
    }

    .assistant-message {
      margin-bottom: 12px;
      white-space: pre-wrap;
    }

    .assistant-message.system {
      color: #57606a;
      font-size: 13px;
    }

    .assistant-message.user {
      color: #1f2328;
    }

    .assistant-message.assistant {
      background: #fff;
      border-radius: 10px;
      padding: 10px 12px;
      border: 1px solid #d0d7de;
    }

    .assistant-sources {
      margin-top: 8px;
      font-size: 12px;
      color: #57606a;
    }
  `;
  document.head.appendChild(style);

  const toggleBtn = document.createElement('button');
  toggleBtn.id = 'ckan-assistant-toggle';
  toggleBtn.type = 'button';
  toggleBtn.setAttribute('aria-label', '打开 CKAN 助手');
  toggleBtn.textContent = '💬';

  const panel = document.createElement('div');
  panel.id = 'ckan-assistant-panel';
  panel.innerHTML = `
    <div id="ckan-assistant-header">
      <span>CKAN AI 助手</span>
      <button type="button" id="ckan-assistant-close" aria-label="关闭">x</button>
    </div>
    <div id="ckan-assistant-messages"></div>
    <form id="ckan-assistant-input">
      <textarea name="message" placeholder="请输入问题…" required></textarea>
      <button type="submit">发送</button>
    </form>
  `;

  mountPoint.append(toggleBtn, panel);

  const closeBtn = panel.querySelector('#ckan-assistant-close');
  const messagesContainer = panel.querySelector('#ckan-assistant-messages');
  const form = panel.querySelector('#ckan-assistant-input');
  const textarea = form.querySelector('textarea');

  const history = [];
  let isSending = false;

  function togglePanel(forceOpen) {
    const shouldOpen = typeof forceOpen === 'boolean' ? forceOpen : !panel.classList.contains('open');
    panel.classList.toggle('open', shouldOpen);
    if (shouldOpen) {
      textarea.focus();
    }
  }

  function appendMessage(role, content, sources) {
    const item = document.createElement('div');
    item.className = `assistant-message ${role}`;

    if (role === 'assistant' && sources && sources.length) {
      const list = sources.map((url) => `<a href="${url}" target="_blank" rel="noopener">${url}</a>`).join('<br>');
      item.innerHTML = `<div>${content}</div><div class="assistant-sources">数据源:<br>${list}</div>`;
    } else {
      item.textContent = content;
    }

    messagesContainer.appendChild(item);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  async function sendMessage(text) {
    if (!text || isSending) {
      return;
    }

    appendMessage('user', text);
    history.push({ role: 'user', content: text });
    isSending = true;
    textarea.value = '';
    textarea.disabled = true;

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
          message: text,
          history: history,
        })
      });

      if (!response.ok) {
        throw new Error(`Assistant error ${response.status}`);
      }

      const payload = await response.json();
      const reply = payload.reply || '（助手没有返回答案。）';
      appendMessage('assistant', reply, payload.sources || []);
      history.push({ role: 'assistant', content: reply });
    } catch (error) {
      console.error(error);
      appendMessage('system', '助手暂时不可用，请稍后再试。');
    } finally {
      isSending = false;
      textarea.disabled = false;
      textarea.focus();
    }
  }

  toggleBtn.addEventListener('click', function () {
    togglePanel();
  });

  closeBtn.addEventListener('click', function () {
    togglePanel(false);
  });

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    const text = textarea.value.trim();
    sendMessage(text);
  });
})();
