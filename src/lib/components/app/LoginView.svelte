<script lang="ts">
	import { toast } from 'svelte-sonner';
	import CloudIcon from '@lucide/svelte/icons/cloud';
	import Loader2Icon from '@lucide/svelte/icons/loader-2';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Card from '#lib/components/ui/card/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Label } from '#lib/components/ui/label/index.js';
	import * as Select from '#lib/components/ui/select/index.js';
	import { Switch } from '#lib/components/ui/switch/index.js';
	import { Checkbox } from '#lib/components/ui/checkbox/index.js';
	import { errorText } from '#lib/api.js';
	import { DO_REGIONS } from '#lib/format.js';
	import { session } from '#lib/stores/session.svelte.js';
	import ThemeToggle from './ThemeToggle.svelte';

	const saved = session.credentials;
	const isDo = (endpoint: string) => /\.digitaloceanspaces\.com\/?$/.test(endpoint);

	let provider = $state<'do' | 'custom'>(saved && !isDo(saved.endpoint) ? 'custom' : 'do');
	let key = $state(saved?.key ?? '');
	let secret = $state(saved?.secret ?? '');
	let region = $state(saved?.region ?? 'nyc3');
	let endpoint = $state(saved?.endpoint ?? '');
	let bucket = $state(saved?.bucket ?? '');
	let pathStyle = $state(saved?.pathStyle ?? false);
	let remember = $state(true);
	let busy = $state(false);
	let error = $state<string | null>(session.bootError);

	const effectiveEndpoint = $derived(
		provider === 'do' ? `https://${region}.digitaloceanspaces.com` : endpoint.trim()
	);

	function validate(): string | null {
		if (!key.trim()) return 'Access key boş olamaz';
		if (!secret.trim()) return 'Secret key boş olamaz';
		if (!/^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$/.test(bucket.trim()))
			return 'Bucket adı 3-63 karakter; küçük harf, rakam, nokta ve tire içerebilir';
		if (!/^https?:\/\//.test(effectiveEndpoint)) return 'Endpoint http:// veya https:// ile başlamalı';
		if (!region.trim()) return 'Bölge boş olamaz';
		return null;
	}

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		error = validate();
		if (error) return;
		busy = true;
		try {
			await session.connect(
				{
					key: key.trim(),
					secret: secret.trim(),
					region: region.trim(),
					endpoint: effectiveEndpoint,
					bucket: bucket.trim(),
					pathStyle: provider === 'custom' && pathStyle
				},
				remember
			);
			toast.success(`${bucket} bağlandı`);
		} catch (err) {
			error = errorText(err);
		} finally {
			busy = false;
		}
	}
</script>

<div class="relative grid h-full place-items-center overflow-auto p-6">
	<div class="absolute top-4 right-4"><ThemeToggle /></div>
	<Card.Root class="w-full max-w-md">
		<Card.Header>
			<div class="bg-primary/15 text-primary mb-2 grid size-11 place-items-center rounded-xl">
				<CloudIcon class="size-6" />
			</div>
			<Card.Title class="text-xl">S3MANAGER</Card.Title>
			<Card.Description>DigitalOcean Spaces veya S3 uyumlu depoya bağlanın.</Card.Description>
		</Card.Header>
		<Card.Content>
			<form id="login" class="grid gap-4" onsubmit={submit}>
				<div class="grid gap-2">
					<Label>Sağlayıcı</Label>
					<Select.Root type="single" bind:value={provider}>
						<Select.Trigger class="w-full">
							{provider === 'do' ? 'DigitalOcean Spaces' : 'Diğer S3 uyumlu (AWS, MinIO, R2…)'}
						</Select.Trigger>
						<Select.Content>
							<Select.Item value="do" label="DigitalOcean Spaces" />
							<Select.Item value="custom" label="Diğer S3 uyumlu (AWS, MinIO, R2…)" />
						</Select.Content>
					</Select.Root>
				</div>

				{#if provider === 'do'}
					<div class="grid gap-2">
						<Label>Bölge</Label>
						<Select.Root type="single" bind:value={region}>
							<Select.Trigger class="w-full">{region}</Select.Trigger>
							<Select.Content>
								{#each DO_REGIONS as r (r)}
									<Select.Item value={r} label={r} />
								{/each}
							</Select.Content>
						</Select.Root>
						<p class="text-muted-foreground text-xs">{effectiveEndpoint}</p>
					</div>
				{:else}
					<div class="grid grid-cols-[1fr_8rem] gap-2">
						<div class="grid gap-2">
							<Label for="endpoint">Endpoint</Label>
							<Input id="endpoint" bind:value={endpoint} placeholder="https://s3.eu-central-1.amazonaws.com" />
						</div>
						<div class="grid gap-2">
							<Label for="region">Bölge</Label>
							<Input id="region" bind:value={region} placeholder="us-east-1" />
						</div>
					</div>
					<label class="flex items-center justify-between gap-3 text-sm">
						<span>Path-style adresleme <span class="text-muted-foreground">(MinIO vb.)</span></span>
						<Switch bind:checked={pathStyle} />
					</label>
				{/if}

				<div class="grid gap-2">
					<Label for="bucket">Bucket</Label>
					<Input id="bucket" bind:value={bucket} autocomplete="off" spellcheck={false} />
				</div>
				<div class="grid gap-2">
					<Label for="key">Access key</Label>
					<Input id="key" bind:value={key} autocomplete="off" spellcheck={false} />
				</div>
				<div class="grid gap-2">
					<Label for="secret">Secret key</Label>
					<Input id="secret" type="password" bind:value={secret} autocomplete="off" />
				</div>

				<label class="flex items-center gap-2 text-sm">
					<Checkbox bind:checked={remember} />
					Bilgileri kaydet <span class="text-muted-foreground">(~/.s3manager/config.ini)</span>
				</label>

				{#if error}
					<p class="text-destructive text-sm" data-selectable>{error}</p>
				{/if}
			</form>
		</Card.Content>
		<Card.Footer>
			<Button type="submit" form="login" class="w-full" disabled={busy}>
				{#if busy}<Loader2Icon class="animate-spin" />{/if}
				Bağlan
			</Button>
		</Card.Footer>
	</Card.Root>
</div>
