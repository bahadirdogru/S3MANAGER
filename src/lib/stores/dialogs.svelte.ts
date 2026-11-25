// Promise-based prompt/confirm, rendered by <DialogHost />.

export interface PromptOptions {
	title: string;
	label?: string;
	description?: string;
	value?: string;
	placeholder?: string;
	confirmText?: string;
	validate?: (v: string) => string | null;
}

export interface ConfirmOptions {
	title: string;
	description?: string;
	confirmText?: string;
	destructive?: boolean;
}

type Pending =
	| { kind: 'prompt'; opts: PromptOptions; resolve: (v: string | null) => void }
	| { kind: 'confirm'; opts: ConfirmOptions; resolve: (v: boolean) => void };

class Dialogs {
	current = $state<Pending | null>(null);

	prompt(opts: PromptOptions): Promise<string | null> {
		this.#dismiss();
		return new Promise((resolve) => (this.current = { kind: 'prompt', opts, resolve }));
	}

	confirm(opts: ConfirmOptions): Promise<boolean> {
		this.#dismiss();
		return new Promise((resolve) => (this.current = { kind: 'confirm', opts, resolve }));
	}

	settle(value: string | boolean | null) {
		const c = this.current;
		this.current = null;
		if (!c) return;
		if (c.kind === 'prompt') c.resolve(typeof value === 'string' ? value : null);
		else c.resolve(value === true);
	}

	#dismiss() {
		if (this.current) this.settle(null);
	}
}

export const dialogs = new Dialogs();

export const nameValidator = (v: string) => {
	const t = v.trim();
	if (!t) return 'Ad boş olamaz';
	if (/[/\\]/.test(t)) return 'Ad içinde / veya \\ kullanılamaz';
	if (t === '.' || t === '..') return 'Geçersiz ad';
	return null;
};
