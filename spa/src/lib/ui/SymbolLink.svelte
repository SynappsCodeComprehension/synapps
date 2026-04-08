<script>
  const { name, fullName = '', kind = '', filePath = '', line = 0, onNavigate } = $props();

  function handleClick(event) {
    onNavigate?.({ full_name: fullName || name, kind, file_path: filePath, line }, event);
  }
</script>

<button class="symbol-name" onclick={handleClick} title={fullName || name}>
  {name}
</button>

<style>
  .symbol-name {
    display: block;
    width: 100%;
    background: none;
    border: none;
    color: var(--color-accent);
    cursor: pointer;
    font-size: inherit;
    font-family: inherit;
    padding: 0;
    text-align: left;
    text-decoration: none;
  }
  .symbol-name:hover {
    text-decoration: underline;
  }
</style>
