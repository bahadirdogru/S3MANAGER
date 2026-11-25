import { setMode } from 'mode-watcher';
import { openUrl } from '@tauri-apps/plugin-opener';
import { toast } from 'svelte-sonner';
import { api, errorText, type Credentials } from '#lib/api.js';
import { explorer } from './explorer.svelte.js';

/** Connection + app-wide state. */
class Session {
	ready = $state(false);
	connected = $state(false);
	online = $state(true);
	credentials = $state<Credentials | null>(null);
	version = $state('');
	configDir = $state('');
	theme = $state<'dark' | 'light'>('dark');
	/** Why the automatic connect with saved credentials failed, shown on the login screen. */
	bootError = $state<string | null>(null);
	#pingTimer: ReturnType<typeof setInterval> | null = null;

	async boot() {
		const s = await api.startup();
		this.credentials = s.credentials;
		this.version = s.version;
		this.configDir = s.configDir;
		this.theme = s.theme;
		setMode(s.theme);
		// Saved credentials connect straight away.
		if (s.credentials) {
			try {
				await this.connect(s.credentials, false);
			} catch (e) {
				this.bootError = errorText(e);
			}
		}
		this.ready = true;
		void this.#checkUpdate();
	}

	/** Startup update check; quiet on failure, respects "skip this version". */
	async #checkUpdate() {
		try {
			const u = await api.checkUpdate();
			if (!u.newer || u.dismissed) return;
			toast.info(`Yeni sürüm mevcut: v${u.latest}`, {
				description: `Kullandığınız sürüm: v${u.current}`,
				duration: 15_000,
				action: { label: 'İndir', onClick: () => void openUrl(u.url) },
				cancel: { label: 'Atla', onClick: () => void api.dismissUpdate(u.latest) }
			});
		} catch {
			// offline or rate-limited: try again next launch
		}
	}

	async connect(creds: Credentials, remember: boolean) {
		await api.connect(creds, remember);
		this.credentials = creds;
		this.connected = true;
		this.online = true;
		explorer.reset();
		void explorer.open('', { history: false });
		this.#startPing();
	}

	async disconnect() {
		await api.disconnect();
		this.connected = false;
		explorer.reset();
		if (this.#pingTimer) clearInterval(this.#pingTimer);
	}

	/** Connection indicator: cheap HeadBucket every 60 s. */
	#startPing() {
		if (this.#pingTimer) clearInterval(this.#pingTimer);
		this.#pingTimer = setInterval(async () => {
			try {
				await api.ping();
				this.online = true;
			} catch {
				this.online = false;
			}
		}, 60_000);
	}

	async setTheme(theme: 'dark' | 'light') {
		this.theme = theme;
		setMode(theme);
		await api.saveTheme(theme).catch(() => {});
	}
}

export const session = new Session();
