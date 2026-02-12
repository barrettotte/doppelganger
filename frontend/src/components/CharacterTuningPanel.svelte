<script lang="ts">
  interface Tuning {
    exaggeration: number | null;
    cfg_weight: number | null;
    temperature: number | null;
    repetition_penalty: number | null;
    top_p: number | null;
    frequency_penalty: number | null;
  }

  let { character, tuningDraft = $bindable(), onsave, onreset, saving = false }: {
    character: any;
    tuningDraft: Tuning;
    onsave: () => void | Promise<void>;
    onreset: () => void | Promise<void>;
    saving?: boolean;
  } = $props();

  // Global defaults per engine (from config.py).
  const CHATTERBOX_DEFAULTS = { exaggeration: 0.1, cfg_weight: 3.0, temperature: 0.5 };
  const ORPHEUS_DEFAULTS = { temperature: 0.6, top_p: 0.95, repetition_penalty: 1.1, frequency_penalty: 0.0 };

  // Return a display string for a tuning value, showing the default on null.
  function tuningDisplay(value: number | null, defaultVal: number): string {
    if (value !== null) {
      return String(value);
    }
    return `default (${defaultVal})`;
  }

  // Parse a slider value, returning null for empty strings.
  function parseSlider(value: string): number | null {
    if (value === '') {
      return null;
    }
    return parseFloat(value);
  }

  // Resolve the temperature default based on engine type.
  const tempDefault = $derived(character.engine === 'orpheus' ? ORPHEUS_DEFAULTS.temperature : CHATTERBOX_DEFAULTS.temperature);
</script>

<div class="tuning-panel">
  <div class="tuning-slider">
    <label for="tune-exag-{character.id}" title="Vocal expressiveness - 0 is flat/monotone, 1 is dramatic/animated">Exaggeration <span class="tuning-val">{tuningDisplay(tuningDraft.exaggeration, CHATTERBOX_DEFAULTS.exaggeration)}</span></label>
    <input id="tune-exag-{character.id}" type="range" min="0" max="1" step="0.05"
      value={tuningDraft.exaggeration ?? ''}
      oninput={(e: Event) => { tuningDraft.exaggeration = parseSlider((e.target as HTMLInputElement).value); }} />
  </div>
  <div class="tuning-slider">
    <label for="tune-cfg-{character.id}" title="Voice cloning guidance strength - higher values stay closer to the reference voice">CFG Weight <span class="tuning-val">{tuningDisplay(tuningDraft.cfg_weight, CHATTERBOX_DEFAULTS.cfg_weight)}</span></label>
    <input id="tune-cfg-{character.id}" type="range" min="0" max="10" step="0.1"
      value={tuningDraft.cfg_weight ?? ''}
      oninput={(e: Event) => { tuningDraft.cfg_weight = parseSlider((e.target as HTMLInputElement).value); }} />
  </div>
  <div class="tuning-slider">
    <label for="tune-temp-{character.id}" title="Sampling randomness - lower is more consistent, higher adds more variation">Temperature <span class="tuning-val">{tuningDisplay(tuningDraft.temperature, tempDefault)}</span></label>
    <input id="tune-temp-{character.id}" type="range" min="0" max="1.5" step="0.05"
      value={tuningDraft.temperature ?? ''}
      oninput={(e: Event) => { tuningDraft.temperature = parseSlider((e.target as HTMLInputElement).value); }} />
  </div>

  {#if character.engine === 'orpheus'}
    <div class="tuning-slider">
      <label for="tune-rep-{character.id}" title="Penalizes repeated tokens to reduce audio looping - higher values discourage repetition more">Repetition Penalty <span class="tuning-val">{tuningDisplay(tuningDraft.repetition_penalty, ORPHEUS_DEFAULTS.repetition_penalty)}</span></label>
      <input id="tune-rep-{character.id}" type="range" min="1" max="2" step="0.05"
        value={tuningDraft.repetition_penalty ?? ''}
        oninput={(e: Event) => { tuningDraft.repetition_penalty = parseSlider((e.target as HTMLInputElement).value); }} />
    </div>
    <div class="tuning-slider">
      <label for="tune-topp-{character.id}" title="Nucleus sampling threshold - limits token choices to the most likely candidates summing to this probability">Top P <span class="tuning-val">{tuningDisplay(tuningDraft.top_p, ORPHEUS_DEFAULTS.top_p)}</span></label>
      <input id="tune-topp-{character.id}" type="range" min="0" max="1" step="0.05"
        value={tuningDraft.top_p ?? ''}
        oninput={(e: Event) => { tuningDraft.top_p = parseSlider((e.target as HTMLInputElement).value); }} />
    </div>
    <div class="tuning-slider">
      <label for="tune-freq-{character.id}" title="Penalizes tokens proportional to how often they have appeared - reduces repetitive audio patterns">Frequency Penalty <span class="tuning-val">{tuningDisplay(tuningDraft.frequency_penalty, ORPHEUS_DEFAULTS.frequency_penalty)}</span></label>
      <input id="tune-freq-{character.id}" type="range" min="0" max="2" step="0.05"
        value={tuningDraft.frequency_penalty ?? ''}
        oninput={(e: Event) => { tuningDraft.frequency_penalty = parseSlider((e.target as HTMLInputElement).value); }} />
    </div>
  {/if}

  <div class="tuning-actions">
    <button class="btn-card btn-card-success" onclick={onsave} disabled={saving}>
      {saving ? 'Saving...' : 'Save'}
    </button>
    <button class="btn-card" onclick={onreset} disabled={saving}>Reset to Defaults</button>
  </div>
</div>

<style lang="scss">
  .tuning-panel {
    border-top: 1px solid var(--border);
    padding-top: 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .tuning-slider {
    display: flex;
    flex-direction: column;
    gap: 4px;

    label {
      font-size: 0.75em;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      display: flex;
      justify-content: space-between;
    }

    input[type="range"] {
      width: 100%;
      accent-color: var(--accent);
    }
  }

  .tuning-val {
    color: var(--text-secondary);
    font-variant-numeric: tabular-nums;
  }

  .tuning-actions {
    display: flex;
    gap: 8px;
    margin-top: 4px;
  }

  .btn-card {
    flex: 1;
    padding: 6px 0;
    font-size: 0.8em;
    border-radius: var(--radius);
    border: 1px solid rgba(var(--accent-rgb), 0.25);
    background: rgba(var(--accent-rgb), 0.06);
    color: var(--text-primary);
    transition: background 0.15s, color 0.15s, border-color 0.15s;

    &:hover:not(:disabled) {
      background: rgba(var(--accent-rgb), 0.15);
      border-color: rgba(var(--accent-rgb), 0.5);
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    &-success {
      color: var(--success);
      border-color: var(--success);
      background: rgba(var(--success-rgb), 0.06);

      &:hover:not(:disabled) {
        background: rgba(var(--success-rgb), 0.2);
        border-color: var(--success);
        color: var(--success);
      }
    }
  }
</style>
