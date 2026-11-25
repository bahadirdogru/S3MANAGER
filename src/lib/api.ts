// Typed wrappers around the Rust commands in `src-tauri/src/commands.rs`.
import { invoke } from '@tauri-apps/api/core';
import { listen, type UnlistenFn } from '@tauri-apps/api/event';

export type ItemKind = 'folder' | 'file';
export type Acl = 'private' | 'public-read';

export interface Item {
	name: string;
	path: string;
	kind: ItemKind;
	size: number;
	/** unix seconds */
	modified: number | null;
	etag: string | null;
}

export interface ListPage {
	prefix: string;
	items: Item[];
	nextToken: string | null;
}

export interface Credentials {
	key: string;
	secret: string;
	region: string;
	endpoint: string;
	bucket: string;
	pathStyle: boolean;
}

export interface Startup {
	credentials: Credentials | null;
	theme: 'dark' | 'light';
	version: string;
	configDir: string;
}

export interface ObjectInfo {
	key: string;
	contentType: string;
	cacheControl: string;
	contentDisposition: string;
	contentLength: number;
	lastModified: number | null;
	etag: string;
	metadata: Record<string, string>;
	acl: Acl;
}

export interface MetadataUpdate {
	contentType: string;
	cacheControl: string;
	contentDisposition: string;
	metadata: Record<string, string>;
}

export type Preview =
	| { kind: 'image'; mime: string; dataUrl: string; size: number }
	| { kind: 'text'; mime: string; text: string; truncated: boolean; size: number }
	| { kind: 'unsupported'; mime: string; size: number };

export interface UploadRequest {
	localPath: string;
	remoteKey: string;
	size: number;
}

export type TransferStatus = 'queued' | 'running' | 'done' | 'error' | 'cancelled';

export interface TransferEvent {
	id: string;
	direction: 'upload' | 'download';
	name: string;
	remoteKey: string;
	localPath: string;
	total: number;
	transferred: number;
	status: TransferStatus;
	error: string | null;
	speed: number;
	multipart: boolean;
}

export interface MultipartInfo {
	key: string;
	uploadId: string;
	initiated: number | null;
}

export interface UploadMetadataSettings {
	enabled: boolean;
	cacheControl: string;
	textCharset: string;
	inlineExtensions: string[];
	attachmentExtensions: string[];
}

export interface UpdateInfo {
	current: string;
	latest: string;
	url: string;
	body: string;
	newer: boolean;
	dismissed: boolean;
}

export const api = {
	startup: () => invoke<Startup>('get_startup'),
	defaultEndpoint: (region: string) => invoke<string>('default_endpoint', { region }),
	connect: (credentials: Credentials, remember: boolean) => invoke<void>('connect', { credentials, remember }),
	disconnect: () => invoke<void>('disconnect'),
	ping: () => invoke<void>('ping'),

	listPage: (prefix: string, token: string | null, search = '', maxKeys = 200) =>
		invoke<ListPage>('list_page', { prefix, token, search, maxKeys }),
	getAcls: (keys: string[]) => invoke<Record<string, Acl>>('get_acls', { keys }),
	setAcl: (keys: string[], acl: Acl) => invoke<void>('set_acl', { keys, acl }),
	objectInfo: (key: string) => invoke<ObjectInfo>('object_info', { key }),
	updateMetadata: (key: string, update: MetadataUpdate) => invoke<void>('update_metadata', { key, update }),
	preview: (key: string, size: number) => invoke<Preview>('preview', { key, size }),

	createFolder: (path: string) => invoke<void>('create_folder', { path }),
	deleteItems: (items: Item[]) => invoke<number>('delete_items', { items }),
	copyItem: (item: Item, dest: string) => invoke<void>('copy_item', { item, dest }),
	moveItem: (item: Item, dest: string) => invoke<void>('move_item', { item, dest }),
	renameItem: (item: Item, newName: string) => invoke<string>('rename_item', { item, newName }),
	shareLink: (key: string, days: 3 | 7) => invoke<{ url: string; expiresAt: number }>('share_link', { key, days }),

	expandUpload: (paths: string[], prefix: string) => invoke<UploadRequest[]>('expand_upload', { paths, prefix }),
	startUpload: (requests: UploadRequest[], acl: Acl) => invoke<TransferEvent[]>('start_upload', { requests, acl }),
	startDownload: (items: Item[], destDir: string) => invoke<TransferEvent[]>('start_download', { items, destDir }),
	cancelTransfer: (id: string) => invoke<void>('cancel_transfer', { id }),
	cancelAllTransfers: () => invoke<void>('cancel_all_transfers'),

	listMultipart: (prefix = '') => invoke<MultipartInfo[]>('list_multipart', { prefix }),
	abortMultipart: (key: string, uploadId: string) => invoke<void>('abort_multipart', { key, uploadId }),

	getUploadMetadata: () => invoke<UploadMetadataSettings>('get_upload_metadata'),
	saveUploadMetadata: (settings: UploadMetadataSettings) => invoke<void>('save_upload_metadata', { settings }),
	saveTheme: (theme: 'dark' | 'light') => invoke<void>('save_theme', { theme }),
	checkUpdate: () => invoke<UpdateInfo>('check_update'),
	dismissUpdate: (version: string) => invoke<void>('dismiss_update', { version }),
	readLog: (lines = 500) => invoke<{ path: string; text: string }>('read_log', { lines })
};

export function onTransfer(cb: (e: TransferEvent) => void): Promise<UnlistenFn> {
	return listen<TransferEvent>('transfer', (e) => cb(e.payload));
}

/** Tauri rejects with the serialized AppError string; normalise anything else. */
export function errorText(e: unknown): string {
	if (typeof e === 'string') return e;
	if (e instanceof Error) return e.message;
	return String(e);
}
