import { LitElement, html, css } from "lit";

const DOMAIN = "yt_subs_recipe";

class YtSubsRecipeCard extends LitElement {
  static get properties() {
    return {
      hass: {},
      _config: {},
      _url: { type: String },
      _jobId: { type: String },
      _markdown: { type: String },
      _model: { type: String },
      _loading: { type: String },
      _error: { type: String },
    };
  }

  constructor() {
    super();
    this._url = "";
    this._jobId = "";
    this._markdown = "";
    this._model = "";
    this._loading = "";
    this._error = "";
  }

  setConfig(config) {
    if (!config) {
      throw new Error("Invalid configuration");
    }
    this._config = {
      title: config.title || "YT Subs → Recipe",
      ...config,
    };
  }

  getCardSize() {
    return 8;
  }

  static getStubConfig() {
    return { title: "YT Subs → Recipe" };
  }

  async _callService(service, data) {
    return this.hass.callService(DOMAIN, service, data, undefined, false, true);
  }

  async _downloadSubs() {
    if (!this._url) {
      this._error = "Введите ссылку";
      return;
    }
    this._loading = "subs";
    this._error = "";
    try {
      const result = await this._callService("download_subs", { url: this._url });
      const resp = result.response;
      this._jobId = resp.job_id;
      this._markdown = "";
      this._model = "";
    } catch (e) {
      this._error = "Ошибка скачивания: " + (e.message || e);
    } finally {
      this._loading = "";
    }
  }

  async _generateRecipe() {
    if (!this._jobId) {
      this._error = "Сначала скачайте субтитры";
      return;
    }
    this._loading = "recipe";
    this._error = "";
    try {
      const result = await this._callService("generate_recipe", {
        job_id: this._jobId,
      });
      const resp = result.response;
      this._markdown = resp.markdown;
      this._model = resp.model;
    } catch (e) {
      this._error = "Ошибка генерации: " + (e.message || e);
    } finally {
      this._loading = "";
    }
  }

  async _downloadAndGenerate() {
    if (!this._url) {
      this._error = "Введите ссылку";
      return;
    }
    this._loading = "all";
    this._error = "";
    this._markdown = "";
    this._model = "";
    try {
      const result = await this._callService("download_and_generate", {
        url: this._url,
      });
      const resp = result.response;
      this._jobId = resp.job_id;
      this._markdown = resp.markdown;
      this._model = resp.model;
    } catch (e) {
      this._error = "Ошибка: " + (e.message || e);
    } finally {
      this._loading = "";
    }
  }

  _copyMd() {
    navigator.clipboard.writeText(this._markdown).then(
      () => {
        this._error = "";
      },
      (e) => {
        this._error = "Не удалось скопировать: " + e;
      }
    );
  }

  _downloadMd() {
    const blob = new Blob([this._markdown], {
      type: "text/markdown;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `recipe-${this._jobId || "unknown"}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  _reset() {
    this._jobId = "";
    this._markdown = "";
    this._model = "";
    this._error = "";
  }

  render() {
    if (!this.hass || !this._config) return html``;

    const busy = !!this._loading;

    return html`
      <ha-card .header=${this._config.title}>
        <div class="content">
          <div class="field">
            <label>Ссылка на YouTube Shorts</label>
            <input
              type="url"
              placeholder="https://youtube.com/shorts/..."
              .value=${this._url}
              ?disabled=${busy}
              @input=${(e) => (this._url = e.target.value)}
              @keydown=${(e) => {
                if (e.key === "Enter") this._downloadAndGenerate();
              }}
            />
          </div>

          <div class="btn-row primary">
            <button
              class="primary"
              ?disabled=${busy}
              @click=${this._downloadAndGenerate}
            >
              ${this._loading === "all"
                ? html`<span class="spinner"></span> Генерируем…`
                : "Скачать и сгенерировать"}
            </button>
          </div>

          <div class="btn-row">
            <button ?disabled=${busy} @click=${this._downloadSubs}>
              ${this._loading === "subs" ? "…" : "Только субтитры"}
            </button>
            <button
              ?disabled=${busy || !this._jobId}
              @click=${this._generateRecipe}
            >
              ${this._loading === "recipe" ? "…" : "Только рецепт"}
            </button>
          </div>

          ${this._error ? html`<div class="error">${this._error}</div>` : ""}

          ${this._jobId
            ? html`
                <div class="info">
                  <span class="chip">job: <code>${this._jobId}</code></span>
                  ${this._model
                    ? html`<span class="chip"
                        >model: <code>${this._model}</code></span
                      >`
                    : ""}
                </div>
              `
            : ""}

          ${this._markdown
            ? html`
                <div class="btn-row">
                  <button @click=${this._copyMd}>Скопировать</button>
                  <button @click=${this._downloadMd}>Скачать .md</button>
                  <button class="ghost" @click=${this._reset}>Сбросить</button>
                </div>
                <pre class="md">${this._markdown}</pre>
              `
            : ""}
        </div>
      </ha-card>
    `;
  }

  static get styles() {
    return css`
      :host {
        display: block;
      }
      .content {
        padding: 16px;
      }
      .field {
        display: flex;
        flex-direction: column;
        margin-bottom: 12px;
      }
      .field label {
        font-size: 12px;
        color: var(--secondary-text-color);
        margin-bottom: 4px;
      }
      input {
        padding: 10px 12px;
        font-size: 14px;
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        background: var(--card-background-color);
        color: var(--primary-text-color);
        outline: none;
        transition: border-color 0.15s;
      }
      input:focus {
        border-color: var(--primary-color);
      }
      input:disabled {
        opacity: 0.6;
      }
      .btn-row {
        display: flex;
        gap: 8px;
        margin-bottom: 8px;
      }
      .btn-row.primary {
        margin-bottom: 12px;
      }
      button {
        flex: 1;
        padding: 10px 12px;
        font-size: 14px;
        font-weight: 500;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        background: var(--secondary-background-color);
        color: var(--primary-text-color);
        transition: opacity 0.15s, background 0.15s;
      }
      button.primary {
        background: var(--primary-color);
        color: var(--text-primary-color, #fff);
      }
      button.ghost {
        flex: 0 0 auto;
        background: transparent;
        color: var(--secondary-text-color);
      }
      button:hover:not(:disabled) {
        opacity: 0.88;
      }
      button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      .error {
        margin: 8px 0;
        padding: 8px 12px;
        border-radius: 8px;
        font-size: 13px;
        color: var(--error-color);
        background: rgba(244, 67, 54, 0.08);
        border-left: 3px solid var(--error-color);
      }
      .info {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin: 8px 0;
        font-size: 12px;
      }
      .chip {
        padding: 3px 8px;
        border-radius: 999px;
        background: var(--secondary-background-color);
        color: var(--secondary-text-color);
      }
      code {
        font-family: var(--code-font-family, monospace);
        color: var(--primary-text-color);
      }
      pre.md {
        margin-top: 8px;
        max-height: 420px;
        overflow: auto;
        padding: 12px;
        border-radius: 8px;
        background: var(--secondary-background-color);
        font-size: 12px;
        line-height: 1.5;
        white-space: pre-wrap;
        word-break: break-word;
        font-family: var(--code-font-family, monospace);
      }
      .spinner {
        display: inline-block;
        width: 12px;
        height: 12px;
        border: 2px solid currentColor;
        border-top-color: transparent;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
        vertical-align: -2px;
        margin-right: 4px;
      }
      @keyframes spin {
        to {
          transform: rotate(360deg);
        }
      }
    `;
  }
}

customElements.define("yt-subs-recipe-card", YtSubsRecipeCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "yt-subs-recipe-card",
  name: "YT Subs → Recipe",
  description: "Скачивает субтитры YouTube Shorts и генерирует рецепт в Markdown",
  preview: false,
  documentationURL: "https://github.com/ebloved/ha-yt-subs-recipe",
});