import type { ApiRecord } from '../types/api';

export function text(value: unknown, fallback = '—'): string {
  if (typeof value === 'string' || typeof value === 'number') return String(value);
  if (value && typeof value === 'object') {
    const record = value as ApiRecord;
    return text(
      record.display_value ??
        record.normalized_value ??
        record.value ??
        record.name ??
        record.title ??
        record.id,
      fallback,
    );
  }
  return fallback;
}

export function dateTime(value: unknown): string {
  if (typeof value !== 'string') return '—';
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString();
}

export function percent(value: unknown): string {
  if (typeof value !== 'number') return '—';
  const normalized = value <= 1 ? value * 100 : value;
  return `${Math.round(normalized)}%`;
}

export function recordId(record: ApiRecord): string | undefined {
  return typeof record.id === 'string' ? record.id : undefined;
}
