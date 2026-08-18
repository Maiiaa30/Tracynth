export type IconName =
  | 'alert'
  | 'close'
  | 'dashboard'
  | 'evidence'
  | 'file'
  | 'graph'
  | 'identity'
  | 'incident'
  | 'logout'
  | 'menu'
  | 'monitoring'
  | 'report'
  | 'scan'
  | 'settings';

const paths: Record<IconName, string> = {
  alert: 'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4',
  close: 'M6 6l12 12M18 6 6 18',
  dashboard: 'M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z',
  evidence: 'M9 5h6M9 9h6M9 13h4M6 3h12a2 2 0 0 1 2 2v16H4V5a2 2 0 0 1 2-2z',
  file: 'M6 2h8l4 4v16H6zM14 2v6h6M9 13h6M9 17h4',
  graph: 'M7 7l5 4 5-4M12 11v6M5 5a2 2 0 1 0 0 .01M19 5a2 2 0 1 0 0 .01M12 19a2 2 0 1 0 0 .01',
  identity:
    'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM18 8h4M20 6v4',
  incident: 'M12 3 4 6v5c0 5 3.4 8.7 8 10 4.6-1.3 8-5 8-10V6zM12 8v5M12 17h.01',
  logout: 'M10 17l5-5-5-5M15 12H3M14 4h5a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-5',
  menu: 'M4 7h16M4 12h16M4 17h16',
  monitoring: 'M20 12a8 8 0 1 1-2.34-5.66L20 8M20 3v5h-5M12 7v5l3 2',
  report: 'M5 3h14v18H5zM9 16v-4M12 16V8M15 16v-6',
  scan: 'M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3M8 12h8',
  settings: 'M4 7h10M18 7h2M4 17h2M10 17h10M14 4v6M6 14v6',
};

export function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return (
    <svg
      aria-hidden="true"
      className="icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={paths[name]} />
    </svg>
  );
}
