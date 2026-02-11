<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { get, del, put, getAudio } from '../lib/api';
  import { toasts } from '../lib/toast';
  import { formatDate } from '../lib/format';
  import AudioPlayer from '../components/AudioPlayer.svelte';
  import EmptyState from '../components/EmptyState.svelte';
  import Modal from '../components/Modal.svelte';
  import Spinner from '../components/Spinner.svelte';

  interface Tuning {
    exaggeration: number | null;
    cfg_weight: number | null;
    temperature: number | null;
    repetition_penalty: number | null;
    top_p: number | null;
    frequency_penalty: number | null;
  }

  const MAX_LENGTH = 255;
  const TEST_SENTENCES = [
    'Which one of you fellas are going to get me a damn beer? I\'m dying of thirst over here.',
    'Yeah can I get a 20-piece nugget, double quarter pounder, large fries, and a large coke. Give me two sweet and sour sauces. Ah screw it give me a big mac too. Put the fries in the bag!',
    'Breaking news from the downtown zoo where officials confirmed two red pandas escaped their enclosure this morning through a gap in the fencing damaged during last night\'s windstorm.',
  ];

  let characters: any[] = $state([]);
  let loading = $state(true);

  // Test Character
  let selectedCharacter = $state('');
  let inputText = $state('');
  let generating = $state(false);
  let audioUrl: string | null = $state(null);

  // Add form
  let newName = $state('');
  let newFile: File | null = $state(null);
  let uploading = $state(false);

  // Delete modal
  let modalOpen = $state(false);
  let deleteTarget: any = $state(null);

  // Tuning panel
  let tuningOpenId: number | null = $state(null);
  let tuningDraft: Tuning = $state({ exaggeration: null, cfg_weight: null, temperature: null, repetition_penalty: null, top_p: null, frequency_penalty: null });
  let savingTuning = $state(false);

  // Global defaults per engine (from config.py)
  const CHATTERBOX_DEFAULTS = { exaggeration: 0.1, cfg_weight: 3.0, temperature: 0.5 };
  const ORPHEUS_DEFAULTS = { temperature: 0.6, top_p: 0.95, repetition_penalty: 1.1, frequency_penalty: 0.0 };

  // Return a display string for a tuning value, showing the default on null.
  function tuningDisplay(value: number | null, defaultVal: number): string {
    if (value !== null) {
      return String(value);
    }
    return `default (${defaultVal})`;
  }

  // Fetch the list of characters from the API.
  async function loadCharacters() {
    try {
      const data = await get('/api/characters');
      characters = data.characters;
    } catch (e) {
      toasts.error(e instanceof Error ? e.message : String(e));
    } finally {
      loading = false;
    }
  }

  onMount(loadCharacters);

  onDestroy(() => {
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
    }
  });

  // Generate TTS audio using the test form.
  async function handleGenerate(): Promise<void> {
    if (!selectedCharacter || !inputText.trim()) {
      return;
    }
    generating = true;

    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      audioUrl = null;
    }

    try {
      const blob = await getAudio('/api/tts/generate', {
        character: selectedCharacter,
        text: inputText.trim(),
      });
      audioUrl = URL.createObjectURL(blob);
    } catch (e) {
      toasts.error(e instanceof Error ? e.message : String(e));
      audioUrl = null;
    } finally {
      generating = false;
    }
  }

  // Download the generated audio as a WAV file.
  function handleDownload(): void {
    if (!audioUrl) {
      return;
    }
    const a = document.createElement('a');
    a.href = audioUrl;
    a.download = `${selectedCharacter}_output.wav`;
    a.click();
  }

  // Open a confirmation modal for deleting a character.
  function confirmDelete(character: any): void {
    deleteTarget = character;
    modalOpen = true;
  }

  // Delete the targeted character and refresh the list.
  async function doDelete() {
    if (!deleteTarget) {
      return;
    }
    try {
      const name = deleteTarget.name;
      await del(`/api/characters/${deleteTarget.id}`);
      modalOpen = false;
      deleteTarget = null;
      toasts.success(`Deleted character "${name}"`);
      await loadCharacters();
    } catch (e) {
      toasts.error(e instanceof Error ? e.message : String(e));
    }
  }

  // Store the selected WAV file from the file input for upload.
  function handleFileChange(e: Event): void {
    const files = (e.target as HTMLInputElement).files;
    if (files && files.length > 0) {
      newFile = files[0];
    }
  }

  // Toggle the tuning panel for a character, loading current values into the draft.
  function toggleTuning(char: any): void {
    if (tuningOpenId === char.id) {
      tuningOpenId = null;
      return;
    }
    tuningOpenId = char.id;
    const t = char.tuning || {};
    tuningDraft = {
      exaggeration: t.exaggeration ?? null,
      cfg_weight: t.cfg_weight ?? null,
      temperature: t.temperature ?? null,
      repetition_penalty: t.repetition_penalty ?? null,
      top_p: t.top_p ?? null,
      frequency_penalty: t.frequency_penalty ?? null,
    };
  }

  // Save the tuning draft for the currently open character.
  async function saveTuning(): Promise<void> {
    if (tuningOpenId === null) {
      return;
    }
    savingTuning = true;
    try {
      await put(`/api/characters/${tuningOpenId}/tuning`, tuningDraft);
      toasts.success('Tuning saved');
      await loadCharacters();
    } catch (e) {
      toasts.error(e instanceof Error ? e.message : String(e));
    } finally {
      savingTuning = false;
    }
  }

  // Reset all tuning values to null (use global defaults).
  async function resetTuning(): Promise<void> {
    if (tuningOpenId === null) {
      return;
    }
    tuningDraft = { exaggeration: null, cfg_weight: null, temperature: null, repetition_penalty: null, top_p: null, frequency_penalty: null };
    savingTuning = true;
    try {
      await put(`/api/characters/${tuningOpenId}/tuning`, tuningDraft);
      toasts.success('Tuning reset to defaults');
      await loadCharacters();
    } catch (e) {
      toasts.error(e instanceof Error ? e.message : String(e));
    } finally {
      savingTuning = false;
    }
  }

  // Parse a slider value, returning null for empty strings.
  function parseSlider(value: string): number | null {
    if (value === '') {
      return null;
    }
    return parseFloat(value);
  }

  // Upload a new character with the given name and WAV file via FormData.
  async function handleUpload() {
    if (!newName || !newFile) {
      return;
    }
    uploading = true;

    try {
      const formData = new FormData();
      formData.append('audio', newFile);

      const params = new URLSearchParams({ name: newName });
      const res = await fetch(`/api/characters?${params}`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text);
      }

      toasts.success(`Added character "${newName}"`);
      newName = '';
      newFile = null;
      await loadCharacters();

    } catch (e) {
      toasts.error(e instanceof Error ? e.message : String(e));
    } finally {
      uploading = false;
    }
  }
</script>

<div class="characters-page">
  <h2>Characters</h2>

  {#if !loading && characters.length > 0}
    <div class="test-character-card">
      <h3>Test Character</h3>
      <div class="pg-top-row">
        <div class="field pg-character-field">
          <label for="pg-character">Character</label>
          <select id="pg-character" bind:value={selectedCharacter}>
            <option value="">Select a character</option>
            {#each characters as char}
              <option value={char.name}>{char.name} ({char.engine})</option>
            {/each}
          </select>
        </div>
        <div class="pg-presets">
          {#each TEST_SENTENCES as sentence, i}
            <button class="btn-preset" onclick={() => { inputText = sentence; }}>
              Test {i + 1}
            </button>
          {/each}
        </div>
      </div>
      <div class="field">
        <label for="pg-text">
          Text
          <span class="char-count">{MAX_LENGTH - inputText.length} remaining</span>
        </label>
        <textarea id="pg-text" bind:value={inputText} maxlength={MAX_LENGTH}
          rows="3" placeholder="Enter text to speak..."
        ></textarea>
      </div>
      <div class="pg-actions">
        <button class="btn-primary" onclick={handleGenerate}
          disabled={generating || !selectedCharacter || !inputText.trim()}
        >
          {generating ? 'Generating...' : 'Generate'}
        </button>
      </div>
      {#if generating}
        <div class="center"><Spinner /></div>
      {/if}
      {#if audioUrl}
        <div class="pg-result">
          <AudioPlayer src={audioUrl} />
          <button class="btn-download" onclick={handleDownload}>Download WAV</button>
        </div>
      {/if}
    </div>
  {/if}

  <div class="add-form">
    <h3>Add Character</h3>
    <div class="form-fields">
      <div class="field">
        <label for="char-name">Name</label>
        <input id="char-name" type="text" placeholder="lowercase-with-hyphens" bind:value={newName} pattern="^[a-z0-9-]+$" />
      </div>
      <div class="field">
        <label for="char-audio">Voice Sample</label>
        <label class="file-pick" class:has-file={newFile}>
          <input id="char-audio" type="file" accept=".wav,audio/wav" onchange={handleFileChange} />
          <span class="file-label">{newFile ? newFile.name : 'Choose a .wav file'}</span>
        </label>
      </div>
    </div>
    <div class="form-actions">
      <button class="btn-primary" onclick={handleUpload} disabled={uploading || !newName || !newFile}>
        {uploading ? 'Uploading...' : 'Add Character'}
      </button>
    </div>
  </div>

  {#if loading}
    <div class="center"><Spinner /></div>
  {:else if characters.length === 0}
    <EmptyState message="No characters configured" />
  {:else}
    <div class="grid">
      {#each characters as char}
        <div class="char-card">
          <div class="char-header">
            <div class="char-top">
              <div class="char-name">{char.name}</div>
              <span class="engine-badge">{char.engine}</span>
            </div>
            <div class="char-date">Added {formatDate(char.created_at)}</div>
          </div>
          <div class="char-actions">
            <button class="btn-card" onclick={() => toggleTuning(char)}>
              {tuningOpenId === char.id ? 'Close' : 'Tune'}
            </button>
            <button class="btn-card btn-danger" onclick={() => confirmDelete(char)}>Delete</button>
          </div>
          {#if tuningOpenId === char.id}
            {@const tempDefault = char.engine === 'orpheus' ? ORPHEUS_DEFAULTS.temperature : CHATTERBOX_DEFAULTS.temperature}
            <div class="tuning-panel">
              <div class="tuning-slider">
                <label for="tune-exag-{char.id}" title="Vocal expressiveness - 0 is flat/monotone, 1 is dramatic/animated">Exaggeration <span class="tuning-val">{tuningDisplay(tuningDraft.exaggeration, CHATTERBOX_DEFAULTS.exaggeration)}</span></label>
                <input id="tune-exag-{char.id}" type="range" min="0" max="1" step="0.05"
                  value={tuningDraft.exaggeration ?? ''}
                  oninput={(e: Event) => { tuningDraft.exaggeration = parseSlider((e.target as HTMLInputElement).value); }} />
              </div>
              <div class="tuning-slider">
                <label for="tune-cfg-{char.id}" title="Voice cloning guidance strength - higher values stay closer to the reference voice">CFG Weight <span class="tuning-val">{tuningDisplay(tuningDraft.cfg_weight, CHATTERBOX_DEFAULTS.cfg_weight)}</span></label>
                <input id="tune-cfg-{char.id}" type="range" min="0" max="10" step="0.1"
                  value={tuningDraft.cfg_weight ?? ''}
                  oninput={(e: Event) => { tuningDraft.cfg_weight = parseSlider((e.target as HTMLInputElement).value); }} />
              </div>
              <div class="tuning-slider">
                <label for="tune-temp-{char.id}" title="Sampling randomness - lower is more consistent, higher adds more variation">Temperature <span class="tuning-val">{tuningDisplay(tuningDraft.temperature, tempDefault)}</span></label>
                <input id="tune-temp-{char.id}" type="range" min="0" max="1.5" step="0.05"
                  value={tuningDraft.temperature ?? ''}
                  oninput={(e: Event) => { tuningDraft.temperature = parseSlider((e.target as HTMLInputElement).value); }} />
              </div>
              {#if char.engine === 'orpheus'}
                <div class="tuning-slider">
                  <label for="tune-rep-{char.id}" title="Penalizes repeated tokens to reduce audio looping - higher values discourage repetition more">Repetition Penalty <span class="tuning-val">{tuningDisplay(tuningDraft.repetition_penalty, ORPHEUS_DEFAULTS.repetition_penalty)}</span></label>
                  <input id="tune-rep-{char.id}" type="range" min="1" max="2" step="0.05"
                    value={tuningDraft.repetition_penalty ?? ''}
                    oninput={(e: Event) => { tuningDraft.repetition_penalty = parseSlider((e.target as HTMLInputElement).value); }} />
                </div>
                <div class="tuning-slider">
                  <label for="tune-topp-{char.id}" title="Nucleus sampling threshold - limits token choices to the most likely candidates summing to this probability">Top P <span class="tuning-val">{tuningDisplay(tuningDraft.top_p, ORPHEUS_DEFAULTS.top_p)}</span></label>
                  <input id="tune-topp-{char.id}" type="range" min="0" max="1" step="0.05"
                    value={tuningDraft.top_p ?? ''}
                    oninput={(e: Event) => { tuningDraft.top_p = parseSlider((e.target as HTMLInputElement).value); }} />
                </div>
                <div class="tuning-slider">
                  <label for="tune-freq-{char.id}" title="Penalizes tokens proportional to how often they have appeared - reduces repetitive audio patterns">Frequency Penalty <span class="tuning-val">{tuningDisplay(tuningDraft.frequency_penalty, ORPHEUS_DEFAULTS.frequency_penalty)}</span></label>
                  <input id="tune-freq-{char.id}" type="range" min="0" max="2" step="0.05"
                    value={tuningDraft.frequency_penalty ?? ''}
                    oninput={(e: Event) => { tuningDraft.frequency_penalty = parseSlider((e.target as HTMLInputElement).value); }} />
                </div>
              {/if}
              <div class="tuning-actions">
                <button class="btn-card btn-card-success" onclick={saveTuning} disabled={savingTuning}>
                  {savingTuning ? 'Saving...' : 'Save'}
                </button>
                <button class="btn-card" onclick={resetTuning} disabled={savingTuning}>Reset to Defaults</button>
              </div>
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<Modal open={modalOpen} title="Delete Character" message={`Delete character "${deleteTarget?.name}"? This cannot be undone.`}
  onconfirm={doDelete} oncancel={() => { modalOpen = false; deleteTarget = null; }}
/>

<style lang="scss">
  .characters-page {
    max-width: 900px;
  }

  .test-character-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    margin-bottom: 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;

    h3 {
      font-size: 0.95em;
      margin: 0;
    }
  }

  .pg-top-row {
    display: flex;
    align-items: flex-end;
    gap: 12px;
  }

  .pg-character-field {
    width: 240px;
    flex-shrink: 0;
  }

  .pg-presets {
    display: flex;
    gap: 6px;
    padding-bottom: 1px;
  }

  .btn-preset {
    padding: 8px 12px;
    font-size: 0.85em;
    border-radius: var(--radius);
    border: 1px solid var(--border);
    background: var(--bg-tertiary);
    color: var(--text-secondary);
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s, color 0.15s;

    &:hover {
      background: var(--bg-hover);
      border-color: var(--accent);
      color: var(--text-primary);
    }
  }

  .pg-actions {
    display: flex;
  }

  .pg-result {
    display: flex;
    align-items: center;
    gap: 12px;

    :global(.player) {
      flex: 1;
      min-width: 0;
    }
  }

  .char-count {
    font-size: 0.9em;
    text-transform: none;
    letter-spacing: normal;
  }

  select,
  textarea {
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    color: var(--text-primary);
    padding: 8px 12px;
    border-radius: var(--radius);
    width: 100%;
    box-sizing: border-box;
    font-family: inherit;
    font-size: 0.9em;

    &::placeholder {
      color: var(--text-muted);
    }
  }

  textarea {
    resize: vertical;
    min-height: 50px;
  }

  .btn-download {
    padding: 6px 16px;
    font-size: 0.8em;
    border-radius: var(--radius);
    border: 1px solid rgba(122, 162, 247, 0.25);
    background: rgba(122, 162, 247, 0.06);
    color: var(--text-primary);
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.15s, border-color 0.15s;

    &:hover {
      background: rgba(122, 162, 247, 0.15);
      border-color: rgba(122, 162, 247, 0.5);
    }
  }

  .add-form {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    margin-bottom: 24px;

    h3 {
      font-size: 0.95em;
      margin-bottom: 16px;
    }
  }

  .form-fields {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 16px;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 6px;

    label {
      font-size: 0.8em;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      display: flex;
      justify-content: space-between;
      align-items: baseline;
    }
  }

  input[type="text"] {
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    color: var(--text-primary);
    padding: 8px 12px;
    border-radius: var(--radius);
    width: 100%;
    box-sizing: border-box;

    &::placeholder {
      color: var(--text-muted);
    }
  }

  .file-pick {
    display: flex;
    align-items: center;
    background: var(--bg-tertiary);
    border: 1px dashed var(--border);
    border-radius: var(--radius);
    padding: 8px 12px;
    cursor: pointer;
    transition: border-color 0.15s;

    &:hover {
      border-color: var(--accent);
    }

    &.has-file {
      border-style: solid;
      border-color: var(--accent);
    }

    input[type="file"] {
      display: none;
    }
  }

  .file-label {
    font-size: 0.9em;
    color: var(--text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .form-actions {
    display: flex;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 14px;
  }

  .char-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 18px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    transition: border-color 0.15s, box-shadow 0.15s;

    &:hover {
      border-color: var(--accent);
      box-shadow: 0 0 0 1px var(--accent), var(--shadow);
    }
  }

  .char-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .char-name {
    font-weight: 600;
    font-size: 0.95em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .engine-badge {
    font-size: 0.65em;
    padding: 2px 7px;
    border-radius: 9999px;
    color: var(--text-secondary);
    border: 1px solid rgba(154, 165, 206, 0.3);
    background: rgba(154, 165, 206, 0.08);
    white-space: nowrap;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .char-date {
    font-size: 0.75em;
    color: var(--text-muted);
  }

  .char-actions {
    display: flex;
    gap: 8px;
  }

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
    border: 1px solid rgba(122, 162, 247, 0.25);
    background: rgba(122, 162, 247, 0.06);
    color: var(--text-primary);
    transition: background 0.15s, color 0.15s, border-color 0.15s;

    &:hover:not(:disabled) {
      background: rgba(122, 162, 247, 0.15);
      border-color: rgba(122, 162, 247, 0.5);
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    &-success {
      color: var(--success);
      border-color: var(--success);
      background: rgba(158, 206, 106, 0.06);

      &:hover:not(:disabled) {
        background: rgba(158, 206, 106, 0.2);
        border-color: var(--success);
        color: var(--success);
      }
    }

    &.btn-danger {
      color: var(--error);
      border-color: var(--error);
      background: rgba(247, 118, 142, 0.06);

      &:hover:not(:disabled) {
        background: rgba(247, 118, 142, 0.2);
        border-color: var(--error);
        color: var(--error);
      }
    }
  }
</style>
