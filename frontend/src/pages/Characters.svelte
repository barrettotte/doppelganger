<script lang="ts">
  import { onMount } from 'svelte';
  import { get, del, getAudio } from '../lib/api';
  import { toasts } from '../lib/toast';
  import { formatDate } from '../lib/format';
  import AudioPlayer from '../components/AudioPlayer.svelte';
  import EmptyState from '../components/EmptyState.svelte';
  import Modal from '../components/Modal.svelte';
  import Spinner from '../components/Spinner.svelte';

  let characters: any[] = $state([]);
  let loading = $state(true);
  let testingVoice: string | null = $state(null);
  let audioUrl: string | null = $state(null);

  // Add form
  let newName = $state('');
  let newFile: File | null = $state(null);
  let uploading = $state(false);

  // Delete modal
  let modalOpen = $state(false);
  let deleteTarget: any = $state(null);

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

  // Generate a sample TTS clip for the character and create a playable blob URL.
  async function testVoice(character: any): Promise<void> {
    testingVoice = character.name;
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      audioUrl = null;
    }
    try {
      const blob = await getAudio('/api/tts/generate', {
        character: character.name,
        text: 'Hello, this is a test of the voice cloning system.',
      });
      audioUrl = URL.createObjectURL(blob);
    } catch (e) {
      toasts.error(e instanceof Error ? e.message : String(e));
      audioUrl = null;
    } finally {
      testingVoice = null;
    }
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
            <button class="btn-card btn-card-success" onclick={() => testVoice(char)} disabled={testingVoice === char.name}>
              {testingVoice === char.name ? 'Generating...' : 'Test Voice'}
            </button>
            <button class="btn-card btn-danger" onclick={() => confirmDelete(char)}>Delete</button>
          </div>
        </div>
      {/each}
    </div>

    {#if audioUrl}
      <div class="audio-section">
        <h3>Voice Preview</h3>
        <AudioPlayer src={audioUrl} />
      </div>
    {/if}
  {/if}
</div>

<Modal open={modalOpen} title="Delete Character" message={`Delete character "${deleteTarget?.name}"? This cannot be undone.`}
  onconfirm={doDelete} oncancel={() => { modalOpen = false; deleteTarget = null; }}
/>

<style lang="scss">
  .characters-page {
    max-width: 900px;
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

  .audio-section {
    margin-top: 24px;

    h3 {
      font-size: 0.95em;
      margin-bottom: 8px;
    }
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
