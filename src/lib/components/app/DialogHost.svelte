<script lang="ts">
	import * as AlertDialog from '#lib/components/ui/alert-dialog/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { Button, buttonVariants } from '#lib/components/ui/button/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Label } from '#lib/components/ui/label/index.js';
	import { dialogs } from '#lib/stores/dialogs.svelte.js';

	let value = $state('');
	let error = $state<string | null>(null);
	let input = $state<HTMLInputElement | null>(null);

	const prompt = $derived(dialogs.current?.kind === 'prompt' ? dialogs.current.opts : null);
	const confirm = $derived(dialogs.current?.kind === 'confirm' ? dialogs.current.opts : null);

	$effect(() => {
		if (prompt) {
			value = prompt.value ?? '';
			error = null;
			// Select the name part (before the extension) like a file manager does.
			queueMicrotask(() => {
				if (!input) return;
				input.focus();
				const dot = value.lastIndexOf('.');
				input.setSelectionRange(0, dot > 0 ? dot : value.length);
			});
		}
	});

	function submit(e: SubmitEvent) {
		e.preventDefault();
		error = prompt?.validate?.(value) ?? null;
		if (!error) dialogs.settle(value.trim());
	}
</script>

<Dialog.Root open={!!prompt} onOpenChange={(o) => !o && dialogs.settle(null)}>
	<Dialog.Content class="sm:max-w-md">
		{#if prompt}
			<form class="grid gap-4" onsubmit={submit}>
				<Dialog.Header>
					<Dialog.Title>{prompt.title}</Dialog.Title>
					{#if prompt.description}<Dialog.Description>{prompt.description}</Dialog.Description>{/if}
				</Dialog.Header>
				<div class="grid gap-2">
					{#if prompt.label}<Label for="prompt-input">{prompt.label}</Label>{/if}
					<Input
						id="prompt-input"
						bind:ref={input}
						bind:value
						placeholder={prompt.placeholder}
						spellcheck={false}
						autocomplete="off"
						aria-invalid={!!error}
					/>
					{#if error}<p class="text-destructive text-sm">{error}</p>{/if}
				</div>
				<Dialog.Footer>
					<Button variant="outline" onclick={() => dialogs.settle(null)}>Vazgeç</Button>
					<Button type="submit">{prompt.confirmText ?? 'Tamam'}</Button>
				</Dialog.Footer>
			</form>
		{/if}
	</Dialog.Content>
</Dialog.Root>

<AlertDialog.Root open={!!confirm} onOpenChange={(o) => !o && dialogs.settle(false)}>
	<AlertDialog.Content>
		{#if confirm}
			<AlertDialog.Header>
				<AlertDialog.Title>{confirm.title}</AlertDialog.Title>
				{#if confirm.description}
					<AlertDialog.Description class="whitespace-pre-line">{confirm.description}</AlertDialog.Description>
				{/if}
			</AlertDialog.Header>
			<AlertDialog.Footer>
				<AlertDialog.Cancel onclick={() => dialogs.settle(false)}>Vazgeç</AlertDialog.Cancel>
				<AlertDialog.Action
					class={confirm.destructive ? buttonVariants({ variant: 'destructive' }) : undefined}
					onclick={() => dialogs.settle(true)}
				>
					{confirm.confirmText ?? 'Onayla'}
				</AlertDialog.Action>
			</AlertDialog.Footer>
		{/if}
	</AlertDialog.Content>
</AlertDialog.Root>
