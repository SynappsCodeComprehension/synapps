<script>
  import { untrack } from 'svelte';
  import { apiCall } from '../api.js';
  import { tools } from './toolConfig.js';

  const {
    toolId,
    initialValues = null,
    savedFormValues = {},
    onResult,
    onError,
    onLoading,
    onRefresh,
    onClearInitialValues,
    onSaveFormValues,
  } = $props();
  const config = $derived(tools[toolId]);

  let formValues = $state({});
  let submitting = $state(false);

  // Per-param autocomplete state: { [paramName]: { suggestions, activeIndex, open } }
  let autocompleteState = $state({});
  let debounceTimers = {};

  // Reset form values when tool changes; prefer saved state over defaults, initialValues takes highest priority.
  // Read savedFormValues inside untrack to avoid a loop: Effect sets formValues → save callback
  // updates savedFormValues prop → re-triggers this effect → infinite cycle.
  $effect(() => {
    if (config) {
      const saved = untrack(() => savedFormValues?.[toolId]);
      const vals = {};
      for (const p of config.params) {
        if (saved && p.name in saved) {
          vals[p.name] = saved[p.name];
        } else {
          vals[p.name] = p.default !== undefined ? p.default : (p.type === 'checkbox' ? false : '');
        }
      }
      if (initialValues) {
        for (const [k, v] of Object.entries(initialValues)) {
          if (k in vals) vals[k] = v;
        }
      }
      formValues = vals;
      autocompleteState = {};
      if (initialValues) {
        untrack(() => { submit(); });
        onClearInitialValues?.();
      }
    }
  });

  // Persist form values to parent on every change.
  // Use untrack for the callback to avoid triggering upstream reactive cascades.
  $effect(() => {
    if (toolId && config && Object.keys(formValues).length > 0) {
      const id = toolId;
      const vals = { ...formValues };
      untrack(() => onSaveFormValues?.(id, vals));
    }
  });

  async function fetchSuggestions(paramName, value) {
    if (!value || value.length < 2) {
      autocompleteState = { ...autocompleteState, [paramName]: { suggestions: [], activeIndex: -1, open: false } };
      return;
    }
    try {
      const data = await apiCall('search_symbols', { query: value, limit: 10 });
      const items = Array.isArray(data) ? data : (data?.results ?? []);
      const suggestions = items.map(s => s.full_name).filter(Boolean);
      autocompleteState = { ...autocompleteState, [paramName]: { suggestions, activeIndex: -1, open: suggestions.length > 0 } };
    } catch {
      autocompleteState = { ...autocompleteState, [paramName]: { suggestions: [], activeIndex: -1, open: false } };
    }
  }

  function handleAutocompleteInput(paramName, value) {
    clearTimeout(debounceTimers[paramName]);
    debounceTimers[paramName] = setTimeout(() => fetchSuggestions(paramName, value), 300);
  }

  function selectSuggestion(paramName, value) {
    formValues = { ...formValues, [paramName]: value };
    autocompleteState = { ...autocompleteState, [paramName]: { suggestions: [], activeIndex: -1, open: false } };
  }

  function handleAutocompleteKeydown(paramName, event) {
    const state = autocompleteState[paramName];
    if (!state?.open) return;
    const { suggestions, activeIndex } = state;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      autocompleteState = { ...autocompleteState, [paramName]: { ...state, activeIndex: Math.min(activeIndex + 1, suggestions.length - 1) } };
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      autocompleteState = { ...autocompleteState, [paramName]: { ...state, activeIndex: Math.max(activeIndex - 1, -1) } };
    } else if (event.key === 'Enter' && activeIndex >= 0) {
      event.preventDefault();
      selectSuggestion(paramName, suggestions[activeIndex]);
    } else if (event.key === 'Escape') {
      autocompleteState = { ...autocompleteState, [paramName]: { ...state, open: false } };
    }
  }

  function handleAutocompleteBlur(paramName) {
    // Delay so a click on suggestion registers before closing
    setTimeout(() => {
      const state = autocompleteState[paramName];
      if (state?.open) {
        autocompleteState = { ...autocompleteState, [paramName]: { ...state, open: false } };
      }
    }, 150);
  }

  function highlightMatch(text, query) {
    if (!query || query.length < 2) return text;
    const idx = text.toLowerCase().indexOf(query.toLowerCase());
    if (idx === -1) return text;
    return text.slice(0, idx) + '<strong>' + text.slice(idx, idx + query.length) + '</strong>' + text.slice(idx + query.length);
  }

  async function submit() {
    if (submitting) return;

    // Build params, converting empty strings to null for optional params
    const params = {};
    for (const p of config.params) {
      const val = formValues[p.name];
      if (p.type === 'checkbox') {
        params[p.name] = val;
      } else if (p.type === 'number' && val !== '' && val !== undefined) {
        params[p.name] = Number(val);
      } else if (val !== '' && val !== undefined && val !== null) {
        params[p.name] = val;
      }
    }

    submitting = true;
    onLoading?.(true);
    try {
      const result = await apiCall(config.endpoint, params, config.method);
      onResult?.(result, config.resultType, params);
    } catch (err) {
      onError?.(err.message);
    } finally {
      submitting = false;
      onLoading?.(false);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    await submit();
  }
</script>

{#if config}
  {#if config.autoRun}
    <div class="tool-form">
      <h2 class="heading">{config.label}</h2>
      <button type="button" class="submit-btn" data-testid="tool-submit" onclick={() => onRefresh?.(toolId)}>
        {config.cta}
      </button>
    </div>
  {:else}
    <form class="tool-form" onsubmit={handleSubmit}>
      <h2 class="heading">{config.label}</h2>
      <div class="form-fields">
        {#each config.params as param}
          {#if param.hidden}<!-- skip hidden params (e.g. limit/offset on paginated tools — managed by Pagination component) -->{:else}
          <div class="field">
            <label class="label" for={param.name}>{param.label}</label>
            {#if param.type === 'textarea'}
              <textarea
                id={param.name}
                data-testid="param-{param.name}"
                bind:value={formValues[param.name]}
                placeholder={param.placeholder || ''}
                required={param.required}
                rows="4"
              ></textarea>
            {:else if param.type === 'select'}
              <select id={param.name} data-testid="param-{param.name}" bind:value={formValues[param.name]}>
                {#each param.options as opt}
                  <option value={opt}>{opt || param.defaultLabel || '(any)'}</option>
                {/each}
              </select>
            {:else if param.type === 'checkbox'}
              <label class="checkbox-label">
                <input type="checkbox" data-testid="param-{param.name}" bind:checked={formValues[param.name]} />
                {param.label}
              </label>
            {:else if param.autocomplete}
              {@const acState = autocompleteState[param.name] || { suggestions: [], activeIndex: -1, open: false }}
              <div class="autocomplete-field">
                <input
                  id={param.name}
                  type="text"
                  data-testid="param-{param.name}"
                  bind:value={formValues[param.name]}
                  placeholder={param.placeholder || ''}
                  required={param.required}
                  oninput={(e) => handleAutocompleteInput(param.name, e.target.value)}
                  onkeydown={(e) => handleAutocompleteKeydown(param.name, e)}
                  onblur={() => handleAutocompleteBlur(param.name)}
                  autocomplete="off"
                />
                {#if acState.open && acState.suggestions.length > 0}
                  <ul class="autocomplete-dropdown" role="listbox">
                    {#each acState.suggestions as suggestion, i}
                      <li
                        class="autocomplete-item"
                        class:highlighted={i === acState.activeIndex}
                        role="option"
                        aria-selected={i === acState.activeIndex}
                        onmousedown={() => selectSuggestion(param.name, suggestion)}
                      >
                        <!-- eslint-disable-next-line svelte/no-at-html-tags -->
                        {@html highlightMatch(suggestion, formValues[param.name])}
                      </li>
                    {/each}
                  </ul>
                {/if}
              </div>
            {:else}
              <input
                id={param.name}
                type={param.type}
                data-testid="param-{param.name}"
                bind:value={formValues[param.name]}
                placeholder={param.placeholder || ''}
                required={param.required}
              />
            {/if}
          </div>
          {/if}
        {/each}
      </div>
      {#if toolId === 'explore' && Number(formValues.depth) >= 3}
        <p class="depth-warning">Depth 3+ may return a large graph. Consider narrowing your query.</p>
      {/if}
      <button type="submit" class="submit-btn" data-testid="tool-submit" disabled={submitting}>
        {submitting ? 'Loading...' : config.cta}
      </button>
    </form>
  {/if}
{/if}

<style>
  .tool-form {
    margin-bottom: 24px;
  }
  .tool-form .heading {
    margin-bottom: 16px;
  }
  .form-fields {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 16px;
    margin-bottom: 16px;
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .field .label {
    color: var(--color-text-secondary);
  }
  input, select, textarea {
    padding: 8px 12px;
    border: 1px solid var(--color-border);
    border-radius: 4px;
    background: var(--color-dominant);
    color: var(--color-text-primary);
    font-size: 14px;
    font-family: inherit;
  }
  input:focus, select:focus, textarea:focus {
    outline: none;
    border-color: var(--color-accent);
  }
  textarea {
    resize: vertical;
    font-family: monospace;
  }
  .checkbox-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    cursor: pointer;
  }
  .checkbox-label input[type="checkbox"] {
    width: 16px;
    height: 16px;
  }
  .submit-btn {
    padding: 8px 24px;
    background: var(--color-accent);
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  }
  .submit-btn:hover:not(:disabled) {
    opacity: 0.9;
  }
  .submit-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  .depth-warning {
    font-size: 12px;
    font-weight: 400;
    color: var(--color-text-secondary);
    margin-top: 4px;
    margin-bottom: 8px;
  }

  /* Autocomplete */
  .autocomplete-field {
    position: relative;
  }
  .autocomplete-field input {
    width: 100%;
    box-sizing: border-box;
  }
  .autocomplete-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    z-index: 10;
    list-style: none;
    margin: 2px 0 0;
    padding: 4px 0;
    background: var(--color-dominant);
    border: 1px solid var(--color-border);
    border-radius: 4px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    max-height: 240px;
    overflow-y: auto;
  }
  .autocomplete-item {
    padding: 6px 12px;
    font-size: 13px;
    cursor: pointer;
    color: var(--color-text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .autocomplete-item:hover,
  .autocomplete-item.highlighted {
    background: var(--color-accent);
    color: white;
  }
  .autocomplete-item :global(strong) {
    font-weight: 700;
  }
</style>
