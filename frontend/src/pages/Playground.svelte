<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { get, getAudio } from '../lib/api';
  import { toasts } from '../lib/toast';
  import AudioPlayer from '../components/AudioPlayer.svelte';
  import EmptyState from '../components/EmptyState.svelte';
  import Spinner from '../components/Spinner.svelte';

  const MAX_LENGTH = 500;

  let characters: any[] = $state([]);
  let loading = $state(true);
  let selectedCharacter = $state('');
  let inputText = $state('');
  let generating = $state(false);
  let audioUrl: string | null = $state(null);

  // Fetch the list of characters from the API.
  async function loadCharacters(): Promise<void> {
    try {
      const data = await get('/api/characters');
      characters = data.characters;
    } catch (e) {
      toasts.error(e instanceof Error ? e.message : String(e));
    } finally {
      loading = false;
    }
  }

  // Generate TTS audio for the selected character and text.
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
    a.download = `${selectedCharacter}_playground.wav`;
    a.click();
  }

  onMount(loadCharacters);

  onDestroy(() => {
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
    }
  });

</script>

<div class="playground-page">
  <h2>Playground</h2>

  {#if loading}
    <div class="center"><Spinner /></div>
  {:else if characters.length === 0}
    <EmptyState message="No characters available - add one on the Characters page" />
  {:else}
    <div class="form-card">
      <div class="field">
        <label for="pg-character">Character</label>
        <select id="pg-character" bind:value={selectedCharacter}>
          <option value="">Select a character</option>
          {#each characters as char}
            <option value={char.name}>{char.name} ({char.engine})</option>
          {/each}
        </select>
      </div>

      <div class="field">
        <label for="pg-text">
          Text
          <span class="char-count">{MAX_LENGTH - inputText.length} remaining</span>
        </label>
        <textarea id="pg-text" bind:value={inputText} maxlength={MAX_LENGTH}
          rows="4" placeholder="Enter text to speak..."
        ></textarea>
      </div>

      <div class="form-actions">
        <button class="btn-primary" onclick={handleGenerate}
          disabled={generating || !selectedCharacter || !inputText.trim()}
        >
          {generating ? 'Generating...' : 'Generate'}
        </button>
      </div>
    </div>

    {#if generating}
      <div class="center"><Spinner /></div>
    {/if}

    {#if audioUrl}
      <div class="audio-section">
        <h3>Result</h3>
        <AudioPlayer src={audioUrl} />
        <button class="btn-download" onclick={handleDownload}>Download WAV</button>
      </div>
    {/if}
  {/if}
</div>

<style lang="scss">
  .playground-page {
    max-width: 600px;
  }

  .form-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
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
    min-height: 80px;
  }

  .form-actions {
    display: flex;
  }

  .audio-section {
    margin-top: 24px;

    h3 {
      font-size: 0.95em;
      margin-bottom: 8px;
    }
  }

  .btn-download {
    margin-top: 8px;
    padding: 6px 16px;
    font-size: 0.8em;
    border-radius: var(--radius);
    border: 1px solid rgba(122, 162, 247, 0.25);
    background: rgba(122, 162, 247, 0.06);
    color: var(--text-primary);
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;

    &:hover {
      background: rgba(122, 162, 247, 0.15);
      border-color: rgba(122, 162, 247, 0.5);
    }
  }

  .center {
    padding: 24px;
  }
</style>
