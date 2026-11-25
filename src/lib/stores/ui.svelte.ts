import type { Item, UploadRequest } from '#lib/api.js';

/** Which feature dialogs are open, and their payloads. */
class Ui {
	upload = $state<UploadRequest[] | null>(null);
	share = $state<{ item: Item; days: 3 | 7 } | null>(null);
	properties = $state<Item | null>(null);
	settings = $state(false);
	settingsTab = $state('connection');
	previewOpen = $state(true);
	/** A copy/move/delete batch is running; blocks overlapping batches. */
	busy = $state<string | null>(null);

	openSettings(tab = 'connection') {
		this.settingsTab = tab;
		this.settings = true;
	}
}

export const ui = new Ui();
